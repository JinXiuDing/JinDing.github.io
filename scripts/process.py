#!/usr/bin/env python3
# Requires: pip install Pillow
"""
Photo processing script for JinDing Photography website.
Usage: python3 scripts/process.py

Reads JPG photos from /Users/jinding/Pictures/2025/[theme]/,
generates thumbnails and display images,
and produces data/photos.json and data/themes.json.
"""

import argparse
import json
import os
import sys
from fractions import Fraction
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS

# ---------------------------------------------------------------------------
# Theme directory name → theme_id mapping
# ---------------------------------------------------------------------------
THEME_DIR_MAP = {
    "13楼的晚霞": "13lou-wanxia",
    "2025-01-01": "2025-01-01",
    "2025-03-16": "2025-03-16",
    "2025-04-04": "2025-04-04",
    "2025-08-10": "2025-08-10",
    "2025-08-14": "2025-08-14",
    "2025-08-18": "2025-08-18",
    "2025-08-23": "2025-08-23",
    "2025-11-29": "2025-11-29",
    "3.26": "3-26",
    "7月成都机场": "cdut-airport-july",
    "生活随记": "life-moments",
}

JPG_EXTENSIONS = {".jpg", ".jpeg"}
SKIP_EXTENSIONS = {".nef", ".dng", ".tif", ".tiff", ".png", ".mov", ".mp4"}
DEFAULT_SOURCE = "/Users/jinding/Pictures/2025"
DEFAULT_OUTPUT = os.path.expanduser("~/JinDing.github.io")
THUMB_MAX_SIZE = 400
DISPLAY_MAX_SIZE = 1600
JPEG_QUALITY = 85


# ---------------------------------------------------------------------------
# EXIF helpers
# ---------------------------------------------------------------------------

def get_exif_data(image_path):
    """
    Extract key EXIF fields from an image. Returns a dict.
    Missing / unparseable fields default to empty string or 0.
    """
    result = {
        "date_taken": "",
        "make": "",
        "model": "",
        "focal_length": "",
        "aperture": "",
        "shutter_speed": "",
        "iso": 0,
    }

    try:
        img = Image.open(image_path)
        exif_raw = img.getexif()
        if not exif_raw:
            return result

        # Merge main IFD and ExifIFD (sub-IFD) tags
        exif = {}
        for tag_id, value in exif_raw.items():
            tag_name = TAGS.get(tag_id, tag_id)
            exif[tag_name] = value
        # ExifIFD sub-IFD contains DateTimeOriginal, FNumber, etc.
        ifd = exif_raw.get_ifd(0x8769)
        for tag_id, value in ifd.items():
            tag_name = TAGS.get(tag_id, tag_id)
            exif[tag_name] = value

        # -- DateTimeOriginal --
        dt = exif.get("DateTimeOriginal")
        if dt and isinstance(dt, str):
            result["date_taken"] = parse_date_taken(dt)

        # -- Make / Model --
        make = exif.get("Make", "")
        if isinstance(make, str):
            result["make"] = make.strip()
            result["model"] = (exif.get("Model", "") or "").strip()
            # Remove redundant make prefix from model
            if result["make"] and result["model"].startswith(result["make"]):
                result["model"] = result["model"][len(result["make"]):].strip()
            # Nikon: Make="NIKON CORPORATION", Model="NIKON Z 6" — strip leading "NIKON"
            if result["model"].startswith("NIKON "):
                result["model"] = result["model"][6:].strip()

        # -- FocalLength --
        fl = exif.get("FocalLength")
        if fl is not None:
            try:
                focal_num = float(fl)
                result["focal_length"] = f"{focal_num:.0f}mm"
            except (TypeError, ValueError):
                pass

        # -- FNumber (Aperture) --
        fn = exif.get("FNumber")
        if fn is not None:
            try:
                result["aperture"] = f"f/{float(fn):.1f}"
            except (TypeError, ValueError):
                pass

        # -- ExposureTime (Shutter Speed) --
        et = exif.get("ExposureTime")
        if et is not None:
            try:
                if isinstance(et, tuple):
                    et = float(et[0]) / float(et[1]) if et[1] != 0 else float(et[0])
                else:
                    et = float(et)
                if et >= 1:
                    result["shutter_speed"] = f"{et:.1f}s"
                else:
                    frac = Fraction(et).limit_denominator(10000)
                    result["shutter_speed"] = f"{frac.numerator}/{frac.denominator}"
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        # -- ISOSpeedRatings --
        iso = exif.get("ISOSpeedRatings")
        if iso is not None:
            try:
                result["iso"] = int(iso)
            except (TypeError, ValueError):
                pass

        img.close()
    except Exception as exc:
        print(f"  WARNING: Could not read EXIF from {image_path}: {exc}")

    return result


def parse_date_taken(dt_string):
    """
    Convert EXIF DateTimeOriginal "YYYY:MM:DD HH:MM:SS" → ISO "YYYY-MM-DD HH:MM:SS".
    """
    try:
        # EXIF format: "2025:02:22 18:30:00"
        date_part, time_part = dt_string.split(" ")
        iso_date = date_part.replace(":", "-")
        return f"{iso_date} {time_part}"
    except (ValueError, AttributeError):
        return ""


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------

def process_image(src_path, output_dir, theme_name, quality=85, rebuild=False):
    """
    Generate thumbnail (400px) and display (1600px) versions of an image.
    Returns (thumb_rel_path, display_rel_path, width, height) of the display image.

    Paths returned are relative to output_dir for use in JSON data.
    """
    filename = os.path.basename(src_path)
    thumb_dir = os.path.join(output_dir, "photos", theme_name, "thumb")
    display_dir = os.path.join(output_dir, "photos", theme_name)
    thumb_path = os.path.join(thumb_dir, filename)
    display_path = os.path.join(display_dir, filename)

    os.makedirs(thumb_dir, exist_ok=True)
    os.makedirs(display_dir, exist_ok=True)

    if not rebuild and os.path.exists(thumb_path) and os.path.exists(display_path):
        # Skip re-processing; still need dimensions of existing display image
        with Image.open(display_path) as existing:
            w, h = existing.size
        thumb_rel = os.path.join("photos", theme_name, "thumb", filename)
        display_rel = os.path.join("photos", theme_name, filename)
        return thumb_rel, display_rel, w, h

    img = Image.open(src_path)

    # Use LANCZOS (high-quality downsampling) — renamed to LANCZOS in Pillow 10+
    try:
        resample = Image.LANCZOS
    except AttributeError:
        resample = Image.Resampling.LANCZOS

    # ------------------------------------------------------------------
    # Display image (1600px wide)
    # ------------------------------------------------------------------
    display = img.copy()
    if display.width > DISPLAY_MAX_SIZE:
        ratio = DISPLAY_MAX_SIZE / display.width
        new_h = int(display.height * ratio)
        display = display.resize((DISPLAY_MAX_SIZE, new_h), resample)
    # Convert to RGB if needed (e.g., RGBA images from phones)
    if display.mode not in ("RGB", "L"):
        display = display.convert("RGB")
    display.save(display_path, "JPEG", quality=quality, optimize=True)
    dw, dh = display.size

    # ------------------------------------------------------------------
    # Thumbnail (400px wide)
    # ------------------------------------------------------------------
    thumb = img.copy()
    if thumb.width > THUMB_MAX_SIZE:
        ratio_t = THUMB_MAX_SIZE / thumb.width
        new_h_t = int(thumb.height * ratio_t)
        thumb = thumb.resize((THUMB_MAX_SIZE, new_h_t), resample)
    if thumb.mode not in ("RGB", "L"):
        thumb = thumb.convert("RGB")
    thumb.save(thumb_path, "JPEG", quality=quality, optimize=True)

    img.close()
    display.close()
    thumb.close()

    thumb_rel = os.path.join("photos", theme_name, "thumb", filename)
    display_rel = os.path.join("photos", theme_name, filename)
    return thumb_rel, display_rel, dw, dh


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def generate_photo_id(filename):
    """Derive a photo ID from its filename: lowercase without extension."""
    name, _ = os.path.splitext(filename)
    return name.lower()


def is_jpg(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in JPG_EXTENSIONS


def is_skipped(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in SKIP_EXTENSIONS


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Process photos for JinDing Photography website"
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"Source directory (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=JPEG_QUALITY,
        help=f"JPEG quality 1-100 (default: {JPEG_QUALITY})",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Force rebuild all images even if they already exist",
    )
    parser.add_argument(
        "--theme",
        help="Process only a specific theme directory (e.g., '13楼的晚霞')",
    )
    args = parser.parse_args()

    source_dir = os.path.expanduser(args.source)
    output_dir = os.path.expanduser(args.output)
    quality = args.quality

    print(f"Source:  {source_dir}")
    print(f"Output:  {output_dir}")
    print(f"Quality: {quality}")

    # Load or create themes.json
    themes_path = os.path.join(output_dir, "data", "themes.json")
    if os.path.exists(themes_path):
        with open(themes_path, "r", encoding="utf-8") as f:
            themes = json.load(f)
        print(f"Loaded {len(themes)} themes from themes.json")
    else:
        themes = []
        print("No existing themes.json — will create one.")

    # Build theme lookup: name → theme dict
    theme_by_name = {t["name"]: t for t in themes}

    # ------------------------------------------------------------------
    # Scan source directory for theme directories
    # ------------------------------------------------------------------
    all_photos = []
    total_processed = 0
    total_skipped = 0

    sorted_dirs = sorted(os.listdir(source_dir))
    for dirname in sorted_dirs:
        dirpath = os.path.join(source_dir, dirname)
        if not os.path.isdir(dirpath):
            continue

        # Skip non-theme directories
        if dirname not in THEME_DIR_MAP:
            continue

        # Filter single theme if requested
        if args.theme and dirname != args.theme:
            continue

        # Find JPG files
        files = sorted(
            f
            for f in os.listdir(dirpath)
            if os.path.isfile(os.path.join(dirpath, f))
        )
        jpg_files = [f for f in files if is_jpg(f)]
        non_jpg = [f for f in files if is_skipped(f)]

        if not jpg_files:
            print(f"\n[{dirname}] No JPG files ({len(non_jpg)} non-JPG files skipped)")
            continue

        print(f"\n[{dirname}] Processing {len(jpg_files)} photos"
              f"{f' ({len(non_jpg)} non-JPG skipped)' if non_jpg else ''}...")

        theme_id = THEME_DIR_MAP[dirname]
        theme_photos = []

        for idx, filename in enumerate(jpg_files):
            src_path = os.path.join(dirpath, filename)

            try:
                thumb_rel, display_rel, dw, dh = process_image(
                    src_path, output_dir, theme_id, quality, args.rebuild
                )
                exif = get_exif_data(src_path)

                photo = {
                    "id": generate_photo_id(filename),
                    "filename": filename,
                    "title": "",
                    "theme": dirname,
                    "theme_id": theme_id,
                    "date_taken": exif["date_taken"],
                    "location": "",
                    "camera": exif["model"] if exif["model"] else exif["make"],
                    "lens": "",
                    "focal_length": exif["focal_length"],
                    "aperture": exif["aperture"],
                    "shutter_speed": exif["shutter_speed"],
                    "iso": exif["iso"],
                    "description": "",
                    "width": dw,
                    "height": dh,
                }
                theme_photos.append(photo)
                total_processed += 1

                # Progress indicator every 10 photos or on last
                if (idx + 1) % 10 == 0 or (idx + 1) == len(jpg_files):
                    print(f"  {idx + 1}/{len(jpg_files)} done")

            except Exception as exc:
                print(f"  SKIPPED {filename}: {exc}")
                total_skipped += 1

        # Update theme metadata
        if dirname in theme_by_name:
            t = theme_by_name[dirname]
        else:
            t = {
                "id": theme_id,
                "name": dirname,
                "description": "",
                "cover": "",
                "count": 0,
            }
            themes.append(t)
            theme_by_name[dirname] = t

        t["count"] = len(theme_photos)
        if theme_photos and not t["cover"]:
            first = theme_photos[0]
            t["cover"] = os.path.join(
                "photos", theme_id, "thumb", first["filename"]
            )

        all_photos.extend(theme_photos)

    # ------------------------------------------------------------------
    # Save output
    # ------------------------------------------------------------------
    photos_path = os.path.join(output_dir, "data", "photos.json")

    # Sort themes by the order in THEME_DIR_MAP
    theme_order = list(THEME_DIR_MAP.keys())
    themes.sort(key=lambda t: (
        theme_order.index(t["name"]) if t["name"] in theme_order else 9999
    ))

    with open(themes_path, "w", encoding="utf-8") as f:
        json.dump(themes, f, ensure_ascii=False, indent=2)
    print(f"\nThemes written to {themes_path}")

    with open(photos_path, "w", encoding="utf-8") as f:
        json.dump(all_photos, f, ensure_ascii=False, indent=2)
    print(f"Photos written to {photos_path}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    theme_summaries = ", ".join(
        f"{t['name']} ({t['count']} photos)" for t in themes if t["count"] > 0
    )
    print(f"\n=== Summary ===")
    print(f"  Processed: {total_processed} photos")
    print(f"  Skipped:   {total_skipped} files")
    print(f"  Themes:    {theme_summaries if theme_summaries else '(none)'}")
    print(f"  Output:    {output_dir}")


if __name__ == "__main__":
    main()
