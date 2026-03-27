from pathlib import Path

import click

import sys

from .discovery import discover_tv
from .display import ThumbnailProgress
from .photos import get_photos
from .state import UploadedState
from .tv import delete_my_photos, upload_photos

DEFAULT_TOKEN_FILE = Path.home() / ".config" / "photo-tv-sync" / "token.txt"
DEFAULT_STATE_FILE = Path.home() / ".config" / "photo-tv-sync" / "uploaded.json"


@click.command()
@click.argument("album")
@click.option(
    "--tv-ip",
    envvar="SAMSUNG_TV_IP",
    default=None,
    help="Samsung TV IP address (or set SAMSUNG_TV_IP env var); auto-discovered if omitted",
)
@click.option(
    "--token-file",
    type=click.Path(path_type=Path),
    default=DEFAULT_TOKEN_FILE,
    show_default=True,
    help="Path to persist TV auth token",
)
@click.option(
    "--newer",
    type=int,
    default=None,
    metavar="DAYS",
    help="Only upload photos taken within the last N days",
)
@click.option(
    "--reset",
    is_flag=True,
    default=False,
    help="Delete all photos from TV, clear upload history, then re-upload",
)
def main(album: str, tv_ip: str | None, token_file: Path, newer: int | None, reset: bool) -> None:
    """Upload photos from an Apple Photos album (or Favourites) to a Samsung TV.

    ALBUM is either an album name from Apple Photos, or 'Favourites' to use
    your favourited photos.
    """
    token_file.parent.mkdir(parents=True, exist_ok=True)

    if tv_ip is None:
        click.echo("Discovering TV on local network...")
        tv_ip = discover_tv()
        if tv_ip is None:
            raise click.ClickException(
                "No Samsung TV found. Set --tv-ip or SAMSUNG_TV_IP."
            )
        click.echo(f"Found TV at {tv_ip}")

    click.echo(
        f"Fetching photos from "
        f"{'Favourites' if album.lower() in ('favourites', 'favorites') else f'album \"{album}\"'}..."
    )
    try:
        photos = get_photos(album, newer_than_days=newer)
    except ValueError as e:
        raise click.ClickException(str(e))

    state = UploadedState(DEFAULT_STATE_FILE)

    if reset:
        click.echo("Deleting all photos from TV...")
        try:
            deleted = delete_my_photos(tv_ip, token_file)
        except RuntimeError as e:
            raise click.ClickException(str(e))
        click.echo(f"Deleted {deleted} photo(s). Resetting upload history...")
        state.reset()

    new_photos = [p for p in photos if not state.already_uploaded(p.stem)]

    if not new_photos:
        click.echo(f"Nothing to upload — all {len(photos)} photo(s) already on TV.")
        return
    if len(new_photos) < len(photos):
        click.echo(f"Skipping {len(photos) - len(new_photos)} already-uploaded photo(s).")
    photos = new_photos

    click.echo(f"Uploading {len(photos)} photo(s) to {tv_ip}...")
    click.echo("(Approve the connection request on your TV if prompted.)")

    if sys.stdout.isatty():
        progress = ThumbnailProgress(len(photos))
        on_progress = progress.show
    else:
        on_progress = lambda p: click.echo(f"  {p.name}")

    try:
        upload_photos(tv_ip, token_file, photos, on_progress=on_progress, state=state)
    except RuntimeError as e:
        raise click.ClickException(str(e))

    click.echo(f"Done! {len(photos)} photo(s) uploaded.")
