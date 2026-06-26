# CANON.md — moved to the docs/canon/ bible folder

> **The world bible now lives in the [`docs/canon/`](canon/) folder** (Phase D / D1).
> Start at [`docs/canon/README.md`](canon/README.md) — the authoring contract (layout,
> section conventions, the field-bullet convention, the fact-id scheme, the tag affordance).

This single-file stub is **retired**. It used to be the whole world bible; it was split,
losslessly, into cornerstone files:

- `the station` → [`docs/canon/00-station.md`](canon/00-station.md)
- `the time concept` → [`docs/canon/01-time.md`](canon/01-time.md)
- the canon facts → the `## Canon facts` lists in the files above
- `## Cast` (Vell, Wren) → [`docs/canon/90-cast.md`](canon/90-cast.md)
- `## Events` (Lumen Festival) → [`docs/canon/95-events.md`](canon/95-events.md)

## How seeding finds the bible

Seeding (`make seed-canon`) reads the **folder** automatically whenever it holds at least one
cornerstone `*.md` file (which it now does). This file is no longer read for seeding — it is kept
only as a pointer so older references don't dangle. (`settings.canon_path` still points here for
the single-file back-compat path, but the folder takes precedence; see `src/config.py`.)
