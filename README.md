# photo-tv-sync

Upload photos from Apple Photos to a Samsung Frame TV's art gallery.

## Requirements

- macOS with Apple Photos
- Samsung Frame TV on the same network
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

## Usage

```bash
# TV is auto-discovered on the local network
uv run photo-tv-sync "Landscapes"

# Or set the IP explicitly
export SAMSUNG_TV_IP=192.168.1.x
uv run photo-tv-sync "Landscapes"

# Upload favourited photos
uv run photo-tv-sync Favourites

# Only photos taken in the last 180 days
uv run photo-tv-sync --newer 180 "Landscapes"

# Delete everything from the TV and re-upload from scratch
uv run photo-tv-sync --reset "Landscapes"
```

On first run your TV will show a connection approval prompt — accept it once and subsequent runs connect automatically.

As photos upload, thumbnails are displayed inline in the terminal (requires a [Kitty-compatible terminal](https://sw.kovidgoyal.net/kitty/graphics-protocol/) such as Ghostty).

## Behaviour

- **Auto-discovery**: the TV's IP is found via SSDP if `--tv-ip` / `SAMSUNG_TV_IP` is not set.
- **Deduplication**: uploaded photo UUIDs are tracked in `~/.config/photo-tv-sync/uploaded.json`. Already-uploaded photos are skipped on subsequent runs. Interrupted runs resume from where they left off.
- **Resolution check**: photos where the local file is less than 50% of the original's resolution are skipped — this catches iCloud low-res proxies. Re-download the originals in Photos.app (select photos → right-click → Download Originals) and retry.
- **Conversion**: photos are converted to JPEG and resized to 3840px on the long edge before upload. HEIC originals are supported.

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--tv-ip` | `$SAMSUNG_TV_IP` or auto-discovered | TV IP address |
| `--newer DAYS` | — | Only upload photos taken within the last N days |
| `--reset` | — | Delete all photos from TV, clear upload history, then re-upload |
| `--token-file` | `~/.config/photo-tv-sync/token.txt` | Where to persist the TV auth token |
