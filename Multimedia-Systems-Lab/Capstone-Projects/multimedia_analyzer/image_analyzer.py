import os
import cv2
from PIL import Image, ExifTags


class ImageAnalyzer:
    """
    Analyzes image files to extract dimensional properties, color modes,
    resolutions, and embedded EXIF metadata.
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def analyze(self):
        """
        Performs extraction and returns a structured dictionary of image metadata.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Image not found at '{self.file_path}'")

        file_name = os.path.basename(self.file_path)
        size_bytes = os.path.getsize(self.file_path)

        # 1. OpenCV extraction for raw matrix dimensions
        img_cv = cv2.imread(self.file_path)
        if img_cv is not None:
            height, width = img_cv.shape[:2]
            channels = img_cv.shape[2] if len(img_cv.shape) > 2 else 1
            dtype = str(img_cv.dtype)
            val_min = int(img_cv.min())
            val_max = int(img_cv.max())
        else:
            height, width, channels, dtype, val_min, val_max = 0, 0, 0, "Unknown", 0, 0

        # 2. Pillow extraction for format, DPI, and EXIF
        file_format = "Unknown"
        color_mode = "Unknown"
        dpi_str = "N/A"
        exif_clean = {}

        try:
            with Image.open(self.file_path) as pil_img:
                file_format = pil_img.format or "Unknown"
                color_mode = pil_img.mode
                dpi = pil_img.info.get("dpi")
                if dpi:
                    dpi_str = f"{round(dpi[0])} x {round(dpi[1])} DPI"

                if height == 0 or width == 0:
                    width, height = pil_img.size

                raw_exif = pil_img.getexif()
                if raw_exif:
                    for tag_id, val in raw_exif.items():
                        tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                        exif_clean[tag] = str(val)
                    for ifd_id in ExifTags.IFD:
                        try:
                            ifd = raw_exif.get_ifd(ifd_id)
                            if ifd:
                                for tag_id, val in ifd.items():
                                    tag = ExifTags.TAGS.get(tag_id, ExifTags.GPSTAGS.get(tag_id, str(tag_id)))
                                    exif_clean[tag] = str(val)
                        except Exception:
                            pass
        except Exception:
            pass

        # Camera & Date parsing
        make = exif_clean.get("Make", "").strip()
        model = exif_clean.get("Model", "").strip()
        if make and model:
            camera = model if model.startswith(make) else f"{make} {model}"
        else:
            camera = make or model or "N/A"

        date_taken = (
            exif_clean.get("DateTimeOriginal")
            or exif_clean.get("DateTimeDigitized")
            or exif_clean.get("DateTime")
            or "N/A"
        )
        orientation = exif_clean.get("Orientation", "N/A")

        return {
            "media_type": "IMAGE",
            "file_name": file_name,
            "file_path": os.path.abspath(self.file_path),
            "file_size_bytes": size_bytes,
            "file_format": file_format,
            "width": width,
            "height": height,
            "resolution": f"{width} x {height} px",
            "channels": channels,
            "color_mode": color_mode,
            "dpi": dpi_str,
            "data_type": dtype,
            "pixel_range": f"{val_min}..{val_max}" if img_cv is not None else "N/A",
            "exif": {
                "camera": camera,
                "date_taken": date_taken,
                "orientation": orientation,
                "raw_tags": exif_clean,
            },
        }


def analyze_image(file_path):
    """Utility function for quick image analysis."""
    return ImageAnalyzer(file_path).analyze()


if __name__ == "__main__":
    import sys
    sample_path = sys.argv[1] if len(sys.argv) > 1 else "../datasets/universe.jpeg"
    analyzer = ImageAnalyzer(sample_path)
    res = analyzer.analyze()
    print("Image Resolution:", res["resolution"])
    print("Color Mode      :", res["color_mode"])
    print("Format          :", res["file_format"])
