import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import osxphotos
import pillow_heif
from osxphotos import ExportOptions, PhotoExporter
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

LONG_EDGE = 3840
RESOLUTION_THRESHOLD = 0.5  # skip if exported file < 50% of original's long edge

_EXPORT_OPTIONS_BASE = dict(
    convert_to_jpeg=True,
    jpeg_quality=0.95,
    overwrite=True,
    download_missing=True,
)
EXPORT_OPTIONS = ExportOptions(**_EXPORT_OPTIONS_BASE, edited=False)
EXPORT_OPTIONS_EDITED = ExportOptions(**_EXPORT_OPTIONS_BASE, edited=True)


def _resize_to_dest(src: Path, dest: Path) -> None:
    with Image.open(src) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) > LONG_EDGE:
            if w >= h:
                new_size = (LONG_EDGE, int(h * LONG_EDGE / w))
            else:
                new_size = (int(w * LONG_EDGE / h), LONG_EDGE)
            img = img.resize(new_size, Image.LANCZOS)
        img.save(dest, "JPEG", quality=95)


def get_photos(album: str, newer_than_days: int | None = None) -> list[Path]:
    """Return JPEG paths for photos in the named album or Favourites."""
    db = osxphotos.PhotosDB()

    if album.lower() in ("favourites", "favorites"):
        photos = [p for p in db.photos() if p.favorite and p.isphoto]
        label = "Favourites"
    else:
        photos = [p for p in db.photos(albums=[album]) if p.isphoto]
        label = f'album "{album}"'

    if newer_than_days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=newer_than_days)
        photos = [p for p in photos if p.date >= cutoff]

    if not photos:
        raise ValueError(f"No photos found in {label}")

    tmpdir = Path(tempfile.mkdtemp(prefix="photo-tv-sync-"))
    results: list[Path] = []

    for photo in photos:
        dl_dir = Path(tempfile.mkdtemp(prefix="photo-tv-sync-dl-"))
        try:
            options = EXPORT_OPTIONS_EDITED if photo.hasadjustments else EXPORT_OPTIONS
            result = PhotoExporter(photo).export(str(dl_dir), options=options)

            if result.error:
                print(f"  Error exporting {photo.original_filename}: {result.error[0][1]}")
                continue
            if not result.exported:
                print(f"  Skipping {photo.original_filename}: nothing exported")
                continue

            src = Path(result.exported[0])
            original_long_edge = max(photo.width or 0, photo.height or 0)
            if original_long_edge > 0:
                with Image.open(src) as probe:
                    actual_long_edge = max(probe.size)
                if actual_long_edge < original_long_edge * RESOLUTION_THRESHOLD:
                    print(
                        f"  Skipping {photo.original_filename}: "
                        f"exported at {actual_long_edge}px but original is {original_long_edge}px"
                    )
                    continue

            dest = tmpdir / (photo.uuid + ".jpg")
            _resize_to_dest(src, dest)
            results.append(dest)
        finally:
            shutil.rmtree(dl_dir, ignore_errors=True)

    return results
