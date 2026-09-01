import os
import mimetypes
import cv2
import wave


def format_file_size(size_bytes):
    """Formats file size into human-readable Bytes, KB, or MB."""
    if size_bytes < 1024:
        return f"{size_bytes} Bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB ({size_bytes:,} bytes)"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB ({size_bytes:,} bytes)"


def format_duration(seconds):
    """Formats duration in seconds and MM:SS format."""
    if seconds <= 0:
        return "N/A"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{seconds:.2f} s ({mins:02d}:{secs:05.2f})"


def find_associated_subtitles(file_path):
    """
    Finds available companion/associated subtitle files without generating any.
    Searches for subtitle files matching the media filename (e.g. .srt, .vtt, .ass).
    """
    base_name, _ = os.path.splitext(file_path)
    parent_dir = os.path.dirname(file_path) or "."
    file_prefix = os.path.basename(base_name)
    sub_extensions = ['.srt', '.vtt', '.sub', '.ass', '.sbv', '.lrc']
    
    subtitles = []
    if os.path.exists(parent_dir):
        for item in os.listdir(parent_dir):
            name, ext = os.path.splitext(item)
            if ext.lower() in sub_extensions and name.startswith(file_prefix):
                full_sub_path = os.path.join(parent_dir, item)
                size_bytes = os.path.getsize(full_sub_path)
                subtitles.append({
                    "filename": item,
                    "format": ext.upper().lstrip('.'),
                    "size": format_file_size(size_bytes)
                })
    return subtitles


def extract_video_metadata(file_path):
    """Extracts video stream metadata using OpenCV."""
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
    
    # Convert fourcc integer to string code
    fourcc = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)]).strip()
    duration_sec = (total_frames / fps) if (fps > 0 and total_frames > 0) else 0

    cap.release()

    # Calculate aspect ratio
    aspect_ratio = "N/A"
    if width > 0 and height > 0:
        aspect_ratio = f"{width}:{height}"
        if width / height == 16 / 9:
            aspect_ratio = "16:9"
        elif width / height == 4 / 3:
            aspect_ratio = "4:3"
        elif height / width == 16 / 9:
            aspect_ratio = "9:16 (Vertical)"

    return {
        "width": width,
        "height": height,
        "resolution": f"{width} x {height} px",
        "aspect_ratio": aspect_ratio,
        "fps": f"{fps:.2f}" if fps > 0 else "N/A",
        "total_frames": total_frames if total_frames > 0 else "N/A",
        "duration": format_duration(duration_sec),
        "codec": fourcc if fourcc else "Unknown"
    }


def extract_audio_metadata(file_path):
    """Extracts audio metadata using the built-in wave module for WAV files."""
    try:
        with wave.open(file_path, 'rb') as audio:
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            framerate = audio.getframerate()
            total_frames = audio.getnframes()
            duration_sec = total_frames / float(framerate) if framerate > 0 else 0
            bitrate_kbps = (framerate * channels * sample_width * 8) / 1000

            channel_str = "Mono (1 Channel)" if channels == 1 else (
                "Stereo (2 Channels)" if channels == 2 else f"{channels} Channels"
            )

            return {
                "channels": channel_str,
                "sample_rate": f"{framerate} Hz ({framerate / 1000:.1f} kHz)",
                "bit_depth": f"{sample_width * 8}-bit",
                "total_frames": f"{total_frames:,}",
                "duration": format_duration(duration_sec),
                "bitrate": f"{bitrate_kbps:.1f} kbps"
            }
    except Exception:
        return None


def extract_metadata(file_path):
    """Main extraction routine combining general, stream-specific, and subtitle metadata."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return

    file_name = os.path.basename(file_path)
    file_size_bytes = os.path.getsize(file_path)
    file_size = format_file_size(file_size_bytes)
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "Unknown MIME type"

    print("=" * 45)
    print("         MULTIMEDIA METADATA REPORT          ")
    print("=" * 45)
    print(f"{'File Name':<18}: {file_name}")
    print(f"{'File Size':<18}: {file_size}")
    print(f"{'MIME Type':<18}: {mime_type}")
    print("-" * 45)

    # Check for video metadata
    if mime_type.startswith("video") or file_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.webm')):
        video_meta = extract_video_metadata(file_path)
        if video_meta:
            print("VIDEO STREAM METADATA:")
            print(f"  {'Resolution':<16}: {video_meta['resolution']}")
            print(f"  {'Aspect Ratio':<16}: {video_meta['aspect_ratio']}")
            print(f"  {'Frame Rate (FPS)':<16}: {video_meta['fps']}")
            print(f"  {'Total Frames':<16}: {video_meta['total_frames']}")
            print(f"  {'Duration':<16}: {video_meta['duration']}")
            print(f"  {'Codec':<16}: {video_meta['codec']}")
            print("-" * 45)

    # Check for audio metadata
    if mime_type.startswith("audio") or file_path.lower().endswith(('.wav', '.mp3', '.aac', '.flac', '.ogg')):
        audio_meta = extract_audio_metadata(file_path)
        if audio_meta:
            print("AUDIO STREAM METADATA:")
            print(f"  {'Channels':<16}: {audio_meta['channels']}")
            print(f"  {'Sample Rate':<16}: {audio_meta['sample_rate']}")
            print(f"  {'Bit Depth':<16}: {audio_meta['bit_depth']}")
            print(f"  {'Total Frames':<16}: {audio_meta['total_frames']}")
            print(f"  {'Duration':<16}: {audio_meta['duration']}")
            print(f"  {'Bitrate':<16}: {audio_meta['bitrate']}")
            print("-" * 45)

    # Check for available subtitles
    subtitles = find_associated_subtitles(file_path)
    print("SUBTITLE METADATA:")
    if subtitles:
        for idx, sub in enumerate(subtitles, 1):
            print(f"  Track/File {idx}      : {sub['filename']} (Format: {sub['format']}, Size: {sub['size']})")
    else:
        print("  Available Subtitles: None found (no subtitle files present)")
    print("=" * 45)


if __name__ == "__main__":
    # Default sample file from datasets folder
    default_path = r"../datasets/statue_of_unity.mp4"

    # Input prompt or default
    user_input = input(f"Enter media file path [Default: {default_path}]: ").strip()
    target_file = user_input if user_input else default_path

    extract_metadata(target_file)
