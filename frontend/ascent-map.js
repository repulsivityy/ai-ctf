// Ascent Map — vertical cross-section of the INFERNO containment lattice.
// Ported from the old Streamlit component: same visuals, no component protocol.
// Styles live in styles.css under `#ascent-map`.

const TAG = {
  current: "CURRENT",
  breached: "FRACTURED",
  open: "OPEN",
  sealed: "SEALED",
  void: "NOT BUILT",
};

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
  }[c]));
}

function plateHTML(s) {
  const clickable = !!s.clickable;
  const el = clickable ? "button" : "div";
  const hint = s.status === "sealed"
    ? '<span class="hint hint--muted">Break the seal above first.</span>'
    : `<span class="hint">${esc(s.tell)}</span>`;
  return (
    `<${el} class="plate plate--${s.status}" style="--i:${s.n}"` +
    (clickable ? ` data-n="${s.n}"` : "") + ">" +
    `<span class="gutter"><span class="numeral">${esc(s.numeral)}</span></span>` +
    '<span class="node"></span>' +
    '<span class="frac" aria-hidden="true"><svg viewBox="0 0 22 22">' +
    '<path d="M1 11 L8 9 L6 4 L14 12 L12 15 L21 13"/></svg></span>' +
    '<span class="reticle" aria-hidden="true"></span>' +
    '<span class="meta">' +
    `<span class="latin">${esc(s.latin)}</span>` +
    `<span class="codename">${esc(s.codename)}</span>` +
    hint +
    "</span>" +
    `<span class="tag">${TAG[s.status] || ""}</span>` +
    '<span class="enter" aria-hidden="true">GO ▸</span>' +
    `</${el}>`
  );
}

let resizeBound = false;

export function renderAscentMap(root, { strata = [], cleared = 0, total = 6, exitOpen = false, onSelect } = {}) {
  let seg = "";
  for (let i = 0; i < total; i++) seg += `<i class="${i < cleared ? "on" : ""}"></i>`;

  root.innerHTML =
    '<div class="head">' +
    '<div class="title">Ascent Map</div>' +
    '<div class="sub">Containment lattice</div>' +
    `<div class="prog"><span class="seg">${seg}</span>` +
    `<span class="lbl"><b>${cleared}</b> / ${total} fractured</span></div>` +
    "</div>" +
    '<div class="shaft">' +
    '<div class="rail"><div class="charge"></div><div class="ping"></div></div>' +
    `<div class="cap ${exitOpen ? "exit-open" : "exit-sealed"}">` +
    '<span class="dot"></span><span class="lx">Aegis Surface</span>' +
    `<span class="tg">${exitOpen ? "EXIT OPEN" : "EXIT SEALED"}</span>` +
    "</div>" +
    strata.map(plateHTML).join("") +
    '<div class="foot">▼  egress runs through the core</div>' +
    "</div>";

  root.querySelectorAll("button.plate").forEach((el) => {
    el.addEventListener("click", () => {
      el.style.filter = "brightness(1.6)";
      if (onSelect) onSelect(parseInt(el.getAttribute("data-n"), 10));
    });
  });

  const place = () => {
    const charge = root.querySelector(".charge");
    const ping = root.querySelector(".ping");
    let y = 0;
    root.querySelectorAll(".plate--current, .plate--breached").forEach((el) => {
      y = Math.max(y, el.offsetTop + el.offsetHeight / 2);
    });
    if (charge) charge.style.height = `${y}px`;
    if (ping) ping.style.setProperty("--ping-to", `${y}px`);
    root.classList.add("loaded");
  };

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => requestAnimationFrame(place));
    setTimeout(place, 700);
  } else {
    requestAnimationFrame(place);
  }

  if (!resizeBound) {
    resizeBound = true;
    window.addEventListener("resize", () => {
      const r = document.getElementById("ascent-map");
      if (!r) return;
      const charge = r.querySelector(".charge");
      let y = 0;
      r.querySelectorAll(".plate--current, .plate--breached").forEach((el) => {
        y = Math.max(y, el.offsetTop + el.offsetHeight / 2);
      });
      if (charge) charge.style.height = `${y}px`;
    });
  }
}
