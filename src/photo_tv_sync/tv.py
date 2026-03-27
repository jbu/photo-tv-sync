import sys
import time
import urllib3
from collections.abc import Callable
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from samsungtvws import SamsungTVWS
from samsungtvws.exceptions import ConnectionFailure

from .state import UploadedState

UPLOAD_DELAY = 2.0   # seconds between uploads to allow TV processing
CONNECT_RETRIES = 5
CONNECT_DELAY = 3.0  # seconds to wait after a timeout before retrying


def _make_art(tv_ip: str, token_file: Path):
    tv = SamsungTVWS(host=tv_ip, port=8002, token_file=str(token_file), timeout=10)
    # Open the main channel first — this fetches and saves the auth token.
    # The art channel connection will time out without it.
    tv.open()
    tv.close()
    art = tv.art()
    if not art.supported():
        raise RuntimeError("This TV does not support Art Mode")
    return tv, art


def _connect_with_retry(tv_ip: str, token_file: Path):
    """Connect and return (tv, art), retrying on timeout."""
    for attempt in range(CONNECT_RETRIES):
        try:
            return _make_art(tv_ip, token_file)
        except ConnectionFailure:
            if attempt == CONNECT_RETRIES - 1:
                raise RuntimeError(
                    f"Could not connect to TV after {CONNECT_RETRIES} attempts. "
                    "Make sure it is on and on the same network."
                )
            sys.stderr.write(f"  Connection timed out, retrying in {CONNECT_DELAY:.0f}s "
                             f"(attempt {attempt + 1}/{CONNECT_RETRIES})...\n")
            time.sleep(CONNECT_DELAY)


def delete_my_photos(tv_ip: str, token_file: Path) -> int:
    """Delete all user-uploaded photos from the TV. Returns the count deleted."""
    tv, art = _connect_with_retry(tv_ip, token_file)
    try:
        all_content = art.available()
        user_ids = [
            item["content_id"]
            for item in all_content
            if str(item.get("category_id", "")).startswith("MY-C")
        ]
        if user_ids:
            art.delete_list(user_ids)
        return len(user_ids)
    finally:
        tv.close()


def upload_photos(
    tv_ip: str,
    token_file: Path,
    photos: list[Path],
    on_progress: Callable[[Path], None] | None = None,
    state: UploadedState | None = None,
) -> None:
    tv, art = _connect_with_retry(tv_ip, token_file)
    try:
        for i, photo in enumerate(photos):
            if on_progress:
                on_progress(photo)

            for attempt in range(CONNECT_RETRIES):
                try:
                    art.upload(str(photo))
                    break
                except ConnectionFailure:
                    if attempt == CONNECT_RETRIES - 1:
                        raise RuntimeError(
                            f"Lost connection to TV while uploading {photo.name}."
                        )
                    sys.stderr.write(f"  Connection dropped, reconnecting "
                                     f"(attempt {attempt + 1}/{CONNECT_RETRIES})...\n")
                    time.sleep(CONNECT_DELAY)
                    tv.close()
                    tv, art = _connect_with_retry(tv_ip, token_file)

            if state:
                state.mark_uploaded(photo.stem)
            if i < len(photos) - 1:
                time.sleep(UPLOAD_DELAY)
    finally:
        tv.close()
