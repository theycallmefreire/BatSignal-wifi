# Improvement priorities

## P0 — Collection reliability and data preservation

Implemented:
- Worker-to-UI queue, bounded polling, cancellation, and main-thread-only widget updates.
- Bounded netsh execution without a shell, actionable errors, and PT/EN/ES/FR/DE output parsing.
- Explicit interface selection when multiple Wi-Fi interfaces are connected.
- SSID, BSSID, interface name, and full timestamps in new readings.
- JSON schema validation, safe unique filenames, atomic writes, and legacy imports.
- Confirmation before replacing a room, loading over unsaved work, or closing.
- Cancelled, empty, and unexpectedly failed collections preserve previous room data.
- Safe Excel worksheet names, literal user strings, and atomic export.

## P1 — Correct and useful charts

Implemented:
- Full 0–100% scales and reusable colors/markers for more than five rooms.
- Consistent color boundaries and minimum/maximum annotations.
- Before/after comparison of matching rooms, with changes in percentage points.

## P2 — Reproducible development and regression prevention

Implemented:
- Standard requirements.txt, explicit direct dependencies, and removal of unused pandas/seaborn.
- Compatibility alias for the old requeriments.txt filename.
- Automated tests for collection, storage, export, charts, and the Tk event loop.
- Ruff formatting/linting and Windows CI for Python 3.12/3.13.
- Stable resource paths and a configurable local data folder.

## P3 — Distribution and documentation

Implemented:
- Portable Windows build script and CI build artifact.
- Apache-2.0 license, NOTICE, and bundled dependency notices.
- English README, contribution guide, and sample surveys.

Still to validate or decide:
- Real Wi-Fi hardware across Windows versions and all supported output languages.
- Signed releases and an installer: require a signing identity and a release process.
- Floor-plan heatmap: requires coordinates, a scale, and repeated location samples;
  the existing room names alone are insufficient for reliable interpolation.
- Linux/macOS collection backends and full interface translation.
