# Prompt: Verify Model Armor Inspect-Mode Integration

I need an independent review of a Google Cloud Model Armor integration
before it goes live for an event. Please read the companion file
`modelarmour_fix_details.md` (in this same directory) — it contains the full
source of the integration, the relevant call sites, the config files, and a
set of findings from two prior automated review passes that need
independent verification.

## Ground rules

- Model Armor here runs in **inspect-only mode**: it must never block or
  alter what gets sent to the underlying Gemini model, only observe and log.
  Do not propose anything that would make it blocking.
- Verify every claim in `modelarmour_fix_details.md` against **current**
  official Google Cloud Model Armor documentation — not general/training
  knowledge, which may be stale for this API. Cite the specific doc URL for
  each claim you confirm or refute, and note the page's publish/update date
  if visible.
- Two prior review passes **directly disagreed with each other** on one
  point (Finding A in the details file — the regional API endpoint format).
  Resolve this one definitively with your own doc lookup; don't defer to
  either prior pass.
- For every other finding (B through G in the details file), independently
  confirm, refute, or refine it — don't just restate it as true.
- Deployment target: a GCE VM in Google Cloud project "A", with Model Armor
  also running in that same project "A". Assume same-project deployment
  when evaluating IAM/auth questions.

## Deliverable

1. A verdict on each finding (A–G): CONFIRMED / REFUTED / PARTIALLY CORRECT,
   with the doc citation and a one-line explanation.
2. A single, prioritized, concrete fix list — code changes plus any
   `gcloud`/console setup steps — needed before this integration can be
   trusted to produce real, working telemetry in the app's `prompts.log`
   during a live event.
3. If you find anything wrong with the integration that neither prior pass
   caught, include it too.

Do not modify any files — this is a review only.
