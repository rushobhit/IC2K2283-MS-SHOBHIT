import os
import cv2
from PIL import Image, ExifTags

import sys

possible_paths = [
    r"datasets/universe.jpeg",
    r"../datasets/universe.jpeg",
    os.path.join(os.path.dirname(__file__), "..", "datasets", "universe.jpeg")
]
default_path = next((p for p in possible_paths if os.path.exists(p)), "datasets/universe.jpeg")
image_path = sys.argv[1] if len(sys.argv) > 1 else default_path

img = cv2.imread(image_path)

if img is None:
    print(f"Error: Could not read image at '{image_path}'. Check if file exists.")
    exit(1)

# Extract dimensions directly from cv2 imread matrix (shape: height, width, channels)
height, width = img.shape[:2]

# File Size & Basic Details
file_name = os.path.basename(image_path)
file_size_bytes = os.path.getsize(image_path)
if file_size_bytes < 1024:
    file_size = f"{file_size_bytes} bytes"
elif file_size_bytes < 1024 * 1024:
    file_size = f"{file_size_bytes / 1024:.2f} KB ({file_size_bytes:,} bytes)"
else:
    file_size = f"{file_size_bytes / (1024 * 1024):.2f} MB ({file_size_bytes:,} bytes)"

# EXIF & Extended Properties via Pillow
with Image.open(image_path) as pil_img:
    file_format = pil_img.format if pil_img.format else "Unknown"
    color_mode = pil_img.mode
    dpi = pil_img.info.get('dpi')
    resolution = f"{round(dpi[0])} x {round(dpi[1])} DPI" if dpi else "N/A"

    exif_data = {}
    exif = pil_img.getexif()
    if exif:
        for tag_id, val in exif.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            exif_data[tag] = val
        for ifd_id in ExifTags.IFD:
            try:
                ifd = exif.get_ifd(ifd_id)
                if ifd:
                    for tag_id, val in ifd.items():
                        tag = ExifTags.TAGS.get(tag_id, ExifTags.GPSTAGS.get(tag_id, tag_id))
                        exif_data[tag] = val
            except Exception:
                pass

print("================================")
print("IMAGE METADATA REPORT")
print("================================")
print()
print(f"{'File Name':<16}: {file_name}")
print(f"{'File Size':<16}: {file_size}")
print(f"{'File Format':<16}: {file_format}")
print(f"{'Width':<16}: {width} px")
print(f"{'Height':<16}: {height} px")
print(f"{'Resolution':<16}: {resolution}")
print(f"{'Color Mode':<16}: {color_mode}")
print()
print("EXIF Metadata")
print("-------------------------------")

if not exif_data:
    print("No EXIF metadata found.")
else:
    make = str(exif_data.get('Make', '')).strip()
    model = str(exif_data.get('Model', '')).strip()
    if make and model:
        camera = model if model.startswith(make) else f"{make} {model}"
    else:
        camera = make or model or "N/A"

    date_taken = (
        exif_data.get('DateTimeOriginal') or
        exif_data.get('DateTimeDigitized') or
        exif_data.get('DateTime') or
        "N/A"
    )

    orientation = exif_data.get('Orientation', 'N/A')

    print(f"{'Camera':<16}: {camera}")
    print(f"{'Date Taken':<16}: {date_taken}")
    print(f"{'Orientation':<16}: {orientation}")