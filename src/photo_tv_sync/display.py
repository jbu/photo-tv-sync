import base64
import io
import os
import sys
from pathlib import Path

from PIL import Image

THUMB_W = 4  # terminal columns per thumbnail
THUMB_H = 3  # terminal rows per thumbnail


def _to_png(path: Path) -> bytes:
    with Image.open(path) as img:
        img = img.convert("RGB")
        img.thumbnail((120, 90), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()


def _kitty_display(png: bytes) -> None:
    data = base64.standard_b64encode(png).decode()
    chunks = [data[i : i + 4096] for i in range(0, len(data), 4096)]
    for i, chunk in enumerate(chunks):
        m = 1 if i < len(chunks) - 1 else 0
        if i == 0:
            sys.stdout.write(
                f"\033_Ga=T,f=100,c={THUMB_W},r={THUMB_H},m={m};{chunk}\033\\"
            )
        else:
            sys.stdout.write(f"\033_Gm={m};{chunk}\033\\")


class ThumbnailProgress:
    """Displays uploaded photos as inline thumbnails using the Kitty graphics protocol."""

    def __init__(self, total: int):
        self.total = total
        self.count = 0
        try:
            cols = os.get_terminal_size().columns
        except OSError:
            cols = 80
        self.thumbs_per_row = max(1, cols // THUMB_W)

    def show(self, path: Path) -> None:
        if not sys.stdout.isatty():
            return

        col_in_row = self.count % self.thumbs_per_row

        if col_in_row == 0:
            # Print THUMB_H blank lines to physically reserve space for this row,
            # move cursor back up into the reserved area, then save that position.
            # We never use cursor-up again after this — all positioning uses
            # save/restore so Kitty's unpredictable post-image cursor placement
            # can't corrupt the layout.
            sys.stdout.write("\n" * THUMB_H)
            sys.stdout.write(f"\033[{THUMB_H}A\033[1G")
            sys.stdout.write("\0337")  # DECSC: save cursor at row start

        _kitty_display(_to_png(path))
        self.count += 1

        is_row_end = self.count % self.thumbs_per_row == 0
        is_last = self.count == self.total

        if not is_row_end and not is_last:
            # Restore to saved position, step right one thumb width, re-save.
            sys.stdout.write(f"\0338\033[{THUMB_W}C\0337")
        else:
            # End of row or all done: restore to the saved row-start position,
            # drop down past the thumbnail row, and reset to column 0.
            sys.stdout.write(f"\0338\033[{THUMB_H}B\r\n")

        sys.stdout.flush()
