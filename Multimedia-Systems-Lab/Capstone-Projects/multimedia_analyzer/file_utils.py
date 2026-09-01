import os
import mimetypes

# Known extensions for fallback checking
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.ico'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma', '.aiff', '.opus'}
VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.3gp'}


def validate_file(file_path):
    """
    Validates whether a given file path exists, is a regular file, and is non-empty.
    Returns (is_valid, error_message).
    """
    if not file_path:
        return False, "No file path provided."
    if not os.path.exists(file_path):
        return False, f"File not found at '{file_path}'."
    if not os.path.isfile(file_path):
        return False, f"Path '{file_path}' is a directory, not a regular file."
    if os.path.getsize(file_path) == 0:
        return False, f"File '{file_path}' is empty (0 bytes)."
    return True, ""


def get_file_size(file_path):
    """
    Returns the file size in formatted human-readable string and raw bytes.
    """
    if not os.path.exists(file_path):
        return "0 bytes", 0
    size_bytes = os.path.getsize(file_path)
    if size_bytes < 1024:
        formatted = f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        formatted = f"{size_bytes / 1024:.2f} KB ({size_bytes:,} bytes)"
    else:
        formatted = f"{size_bytes / (1024 * 1024):.2f} MB ({size_bytes:,} bytes)"
    return formatted, size_bytes


def get_file_extension(file_path):
    """
    Returns the lowercased file extension with leading dot (e.g., '.jpg').
    """
    return os.path.splitext(file_path)[1].lower()


def identify_file_type(file_path):
    """
    Identifies if a file is 'IMAGE', 'AUDIO', 'VIDEO', or 'UNKNOWN'
    using MIME type detection, file headers (magic bytes), and extensions.
    """
    ext = get_file_extension(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)

    # 1. Primary check via MIME type
    if mime_type:
        if mime_type.startswith("image/"):
            return "IMAGE"
        elif mime_type.startswith("audio/"):
            return "AUDIO"
        elif mime_type.startswith("video/"):
            return "VIDEO"

    # 2. Check via file extension
    if ext in IMAGE_EXTENSIONS:
        return "IMAGE"
    elif ext in AUDIO_EXTENSIONS:
        return "AUDIO"
    elif ext in VIDEO_EXTENSIONS:
        return "VIDEO"

    # 3. Check via magic bytes
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
            if header.startswith(b"\xff\xd8\xff") or header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"GIF8"):
                return "IMAGE"
            if header.startswith(b"RIFF") and b"WAVE" in header:
                return "AUDIO"
            if header.startswith(b"ID3") or header[:2] == b"\xff\xfb" or header[:2] == b"\xff\xf3":
                return "AUDIO"
            if len(header) >= 8 and (b"ftyp" in header or header.startswith(b"\x1aE\xdf\xa3")):
                return "VIDEO"
    except Exception:
        pass

    return "UNKNOWN"
