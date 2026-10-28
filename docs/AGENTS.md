# AGENTS.md — docs

Read [`README.md`](../README.md), root [`AGENTS.md`](../AGENTS.md), [`data-sources.md`](data-sources.md), and accepted ADRs in [`adr/`](adr/) before editing.

## Agent rules

- Treat README and root `AGENTS.md` as the approved product scope. Do not expand city coverage, HTTP surface, stack, or profiles in documentation unless the human asked.
- Preserve the accepted execution sequence (geocode and `as_of` → parallel Market and Development → typed supervisor follow-ups → writer → verifier → finalize) until implementation evidence requires an ADR.
- Never rewrite history in an accepted ADR; supersede it with a new ADR.
- State whether a capability is planned, partially implemented, or verified.
- Keep job statuses, claim types, follow-up names, `as_of` / `available_at` language, and module ownership consistent with each package's `AGENTS.md`.
- Do not introduce architecture through documentation alone. A new process, module, or import edge needs code in the same change, and usually an ADR.
- Link to source files and tests once they exist instead of duplicating implementation details.
- Update the matching module `AGENTS.md` when responsibilities actually change.
- Record source license, lag, history, and go/no-go in `data-sources.md`. Record architecture and policy choices in `adr/`.
- Keep failure scenarios and verification commands reproducible (pytest paths, module service entrypoints, CI).
- Do not commit raw data, `phases.md`, or editor-only paths.

## ADR naming

Use `NNNN-short-kebab-case-title.md`, sequentially numbered. Include `Status`, `Context`, `Decision`, `Alternatives`, and `Consequences`.
