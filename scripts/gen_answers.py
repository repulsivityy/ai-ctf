#!/usr/bin/env python3
"""Generate a fresh set of CTF answers (the CIRCLE_* variables) for .env.

    python scripts/gen_answers.py                    # print the block to paste into .env
    python scripts/gen_answers.py --out answers.env  # write it to a new file (mode 0600)
    python scripts/gen_answers.py --avoid .env       # never reuse a word from the old answers

Every run draws from the operating system's secure random source, so the output
is different each time. Nothing is read from or written to your real .env
unless you point --avoid / --out at it.

Run it BY HAND, on the machine you deploy from. Nothing in this repo (deploy.sh,
docker-compose, the app, the tests, CI) calls it, and nothing should: a rotation
is a deliberate act, and an automated one could silently replace live answers.

What it generates, matching the formats answers.py enforces:
  * Exit Passphrases and the Fraus override key: CamelCase, letters only,
    three words of 5-7 letters (e.g. WordWordWord), every word different
    across ALL answers, so one leaked word never helps on another circle.
  * The Avaritia vault key: four hyphen-joined groups of four upper-case
    characters, with no look-alikes (no 0/O, 1/I/L), e.g. K7QM-4XD9-R2TB-9WPE.

Strength: 3 words from a ~330-word list is ~25 bits per answer. That is plenty
for CTF flags (the Ascent Gate allows 8 wrong guesses a minute per session) but
these are not passwords. Swap WORDS for a longer list if you want more.

After generating, the script imports the real answers.py + challenges.py with
the new values in a subprocess, so a value the app would reject (bad format,
duplicate, a prompt that leaks its own answer) is caught here, not at startup.
The answers themselves are only ever printed to stdout / written to --out.
"""

import argparse
import ast
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Easy-to-spell, concrete English words (5-7 letters). No NATO-alphabet words
# (the scanner treats those specially) and nothing from the game's own lore.
WORDS = """
acorn almond anchor apricot arctic arrow aspen aurora autumn avocado badger bagel bamboo
banner barley basil beacon beaver beetle berry biscuit blanket blossom bonfire border
bridge bronze bubble bucket buffalo butter button cabin cactus camel candle canyon
caravan carbon cargo carrot castle cedar cellar cherry chimney cinder citrus clover
cobweb coffee comet copper coral cotton cougar cradle crater crayon crimson crystal
cuckoo curtain cypress dagger daisy dancer desert dolphin donkey dragon drifter
dumpling eagle engine falcon feather fennel ferret fiddle finch flannel flint forest
fossil fountain frosty galaxy garden garlic gazelle ginger glacier goblet gopher
granite gravel grotto guitar hammer hamster harvest hazel helmet hickory horizon
hornet hunter iceberg island ivory jacket jaguar jasmine jersey jungle kettle kernel
kitten ladder lagoon lancer lavender lemon lentil leopard lizard lobster locket lumber
magnet mango maple marble meadow melon mirror monkey mosaic muffin mustard napkin
nectar needle nutmeg oasis ocean olive onion orange orchid osprey otter oyster paddle
pagoda pallet panda panther paprika parrot pebble pelican pepper pickle pigeon pillow
pirate planet plume pocket pollen pomelo poppy potion prairie pretzel puffin pumpkin
puzzle quiver rabbit raccoon radish raisin ranger raven ribbon river rocket rubber
saddle safari salmon sandal sapphire sausage scarf scooter shadow shovel silver sketch
skiff sleigh sparrow spider spiral splash spruce squid squirrel starch statue sticker
stream summit sundial swallow tablet tadpole tangle teacup temple thimble thistle
thunder ticket tiger timber tomato toucan tractor trumpet tulip tunnel turnip turtle
umpire unicorn valley violin walnut walrus wander wagon whistle willow window winter
wizard wombat yogurt zephyr zipper
""".split()

VAULT_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0 O 1 I L
WORDS_PER_ANSWER = 3


def answer_variables():
    """(variable name, is_vault_key) for every field of answers.Answers, in order.
    Read from the source, so a new circle's variable is picked up automatically."""
    tree = ast.parse((ROOT / "answers.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Answers":
            names = [n.target.id for n in node.body if isinstance(n, ast.AnnAssign)]
            return [("CIRCLE_" + n.upper(), "vault_key" in n) for n in names]
    sys.exit("could not find the Answers class in answers.py")


def words_in(path: Path) -> set[str]:
    """Lower-cased words from the CIRCLE_* values of an env-style file."""
    found = set()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return found
    for m in re.finditer(r"(?m)^\s*CIRCLE_[A-Z_]+\s*=\s*(\S+)", text):
        found.update(w.lower() for w in re.findall(r"[A-Z][a-z]*", m.group(1)))
    return found


def generate(avoid: set[str]) -> dict[str, str]:
    pool = sorted({w for w in WORDS if 5 <= len(w) <= 7 and w not in avoid})
    spec = answer_variables()
    need = sum(WORDS_PER_ANSWER for _, vault in spec if not vault)
    if len(pool) < need * 4:
        sys.exit(f"word list too small after exclusions ({len(pool)} words for {need} slots)")
    used, values = set(), {}
    for var, vault in spec:
        if vault:
            groups = ["".join(secrets.choice(VAULT_ALPHABET) for _ in range(4)) for _ in range(4)]
            values[var] = "-".join(groups)
            continue
        picked = []
        while len(picked) < WORDS_PER_ANSWER:
            w = secrets.choice(pool)
            if w not in used:
                used.add(w)
                picked.append(w)
        values[var] = "".join(w.capitalize() for w in picked)
    return values


def validate(values: dict[str, str]) -> None:
    """Import the app's own answers.py and challenges.py with these values."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CIRCLE_")}
    env.update(values)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # cwd=ROOT so imports resolve; load_dotenv never overrides the variables set above
    proc = subprocess.run(
        [sys.executable, "-c", "import answers, challenges"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        err = proc.stderr
        # never echo a value: show only the last line, with any answer masked
        for v in values.values():
            err = err.replace(v, "<answer>")
        last = [ln for ln in err.strip().splitlines() if ln.strip()][-1:] or ["(no message)"]
        sys.exit(f"the app rejected the generated answers: {last[0]}")


def render(values: dict[str, str]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Generated {stamp} by scripts/gen_answers.py",
        "# Replace the CIRCLE_* block in .env with these, restart the app, and update",
        "# prompt_answers.md (the internal answer key) to match.",
    ]
    lines += [f"{var}={val}" for var, val in values.items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a fresh set of CTF answers for .env.")
    ap.add_argument("--out", metavar="FILE", help="write to FILE (new, mode 0600) instead of stdout")
    ap.add_argument("--force", action="store_true", help="allow --out to overwrite an existing file")
    ap.add_argument("--avoid", metavar="FILE", action="append", default=[],
                    help="env-style file whose CIRCLE_* words must not be reused (e.g. your current .env); repeatable")
    ap.add_argument("--no-check", action="store_true", help="skip importing the app to validate the result")
    args = ap.parse_args()

    # The sample values in .env.example never come back. Words from your CURRENT answers are
    # excluded only if you pass --avoid .env: no answer is ever written into this script.
    avoid = words_in(ROOT / ".env.example")
    for f in args.avoid:
        if not Path(f).is_file():
            sys.exit(f"--avoid: no such file: {f}")
        avoid |= words_in(Path(f))

    values = generate(avoid)
    if not args.no_check:
        validate(values)

    text = render(values)
    if args.out:
        flags = os.O_WRONLY | os.O_CREAT | (os.O_TRUNC if args.force else os.O_EXCL)
        try:
            fd = os.open(args.out, flags, 0o600)
        except FileExistsError:
            sys.exit(f"{args.out} already exists (use --force to overwrite it)")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {len(values)} answers to {args.out} (mode 0600)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    status = "validated against answers.py + challenges.py" if not args.no_check else "NOT validated (--no-check)"
    print(f"{len(values)} answers generated, {status}. Remember: update .env, prompt_answers.md, "
          "restart the app, and treat old logs as containing the retired answers.", file=sys.stderr)


if __name__ == "__main__":
    main()
