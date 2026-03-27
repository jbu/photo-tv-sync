# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                          # install dependencies
uv run photo-tv-sync --help      # run the CLI
uv run photo-tv-sync "Album"     # upload an album (requires SAMSUNG_TV_IP env var)
```

There are no tests or linter configured yet.

## Architecture

Single-purpose CLI tool under `src/photo_tv_sync/`:

- **`cli.py`** — `click` entrypoint. Accepts `ALBUM` argument plus `--tv-ip` / `SAMSUNG_TV_IP` env var, `--token-file`, `--newer DAYS`, and `--reset`. Orchestrates the modules below.
- **`photos.py`** — Opens the default Apple Photos library via `osxphotos`. Queries by album name or favourites (`photo.favorite`), optionally filters by capture date. Uses `PhotoExporter` with `ExportOptions(convert_to_jpeg=True, download_missing=True)` for every photo — this handles RAW (NEF, CR2, ARW…), HEIC, and iCloud proxy downloads uniformly. After export, checks the result dimensions against `photo.width`/`photo.height` from Photos metadata to catch any still-low-res results. Applies `ImageOps.exif_transpose()` before resizing so orientation is baked into the pixels. Resizes to 3840px long edge and saves to a temp directory named by `photo.uuid`.
- **`tv.py`** — Connects to the TV with `samsungtvws.SamsungTVWS` (port 8002). Must call `tv.open()` on the main channel first to fetch/save the auth token before the art channel will accept connections. Retries on `ConnectionFailure` both at connect time and per-upload. Calls `art.upload()` per photo with a 2-second delay between uploads. `delete_my_photos()` deletes user-uploaded content (category `MY-C*`) for `--reset`.
- **`state.py`** — Persists uploaded photo UUIDs to `~/.config/photo-tv-sync/uploaded.json`. Checked before export/upload so already-uploaded photos are skipped. Written after each successful upload so interrupted runs resume correctly.
- **`display.py`** — Renders uploaded photo thumbnails inline using the Kitty graphics protocol. Pre-allocates row space with `\n * THUMB_H` before placing images, then uses DECSC/DECRC (`\0337`/`\0338`) save/restore around each image so Kitty's unpredictable post-image cursor placement can't corrupt the layout. Falls back to plain text when stdout is not a TTY.
- **`discovery.py`** — SSDP auto-discovery of the TV's IP. Tries multiple Samsung service types in sequence; used when `--tv-ip` is not provided.

## Key constraints

- Requires Python 3.12 (pinned in `.python-version`) — pyobjc 9.x wheels don't exist for Python 3.13.
- `pillow-heif` is registered at import time in `photos.py` so Pillow can open HEIC files.
- `tv.open()` must be called before any art channel operations — the art WebSocket returns `ms.channel.timeOut` without a token established on the main channel first. Token saved to `~/.config/photo-tv-sync/token.txt`.
- urllib3's `InsecureRequestWarning` is suppressed in `tv.py` — the TV uses a self-signed cert.
- Retry/status messages in `tv.py` go to stderr so they don't corrupt the Kitty thumbnail row on stdout.
- User-uploaded art on this TV lives in categories prefixed `MY-C` (not `MY_F` which is the content_id prefix).
