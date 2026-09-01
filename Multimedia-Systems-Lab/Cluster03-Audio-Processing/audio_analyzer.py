import os
import sys
import wave
import struct


def format_file_size(size_bytes):
    """Formats file size into human-readable Bytes, KB, or MB."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
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


def analyze_audio(file_path):
    """
    Inspects an audio file and displays a clean, structured audio metadata report.
    """
    if not os.path.exists(file_path):
        print(f"Error: Audio file not found at '{file_path}'.")
        return

    file_name = os.path.basename(file_path)
    file_size_bytes = os.path.getsize(file_path)
    file_size_str = format_file_size(file_size_bytes)
    ext = os.path.splitext(file_path)[1].lower()

    # Defaults
    codec = "Unknown Audio Codec"
    container = ext.upper().lstrip(".")
    channel_str = "N/A"
    sample_rate_str = "N/A"
    bit_depth_str = "N/A"
    duration_str = "N/A"
    bitrate_str = "N/A"
    total_frames_str = "N/A"

    if ext == ".wav":
        try:
            with wave.open(file_path, "rb") as w:
                channels = w.getnchannels()
                sampwidth = w.getsampwidth()
                sample_rate = w.getframerate()
                total_frames = w.getnframes()
                duration_sec = total_frames / float(sample_rate) if sample_rate > 0 else 0
                bitrate_kbps = (sample_rate * channels * sampwidth * 8) / 1000

                codec = "PCM (Pulse Code Modulation)"
                container = "WAV (Waveform Audio File Format)"
                channel_str = "1 (Mono)" if channels == 1 else ("2 (Stereo)" if channels == 2 else f"{channels} Channels")
                sample_rate_str = f"{sample_rate} Hz ({sample_rate / 1000:.1f} kHz)"
                bit_depth_str = f"{sampwidth * 8}-bit"
                duration_str = format_duration(duration_sec)
                bitrate_str = f"{bitrate_kbps:.2f} kbps"
                total_frames_str = f"{total_frames:,} frames"
        except Exception:
            pass
    elif ext in [".m4a", ".aac", ".mp4"]:
        container = "MPEG-4 Audio (M4A / AAC)"
        codec = "AAC (Advanced Audio Coding)"
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            idx = data.find(b"mp4a")
            if idx != -1:
                entry_off = idx - 4
                channels = int.from_bytes(data[entry_off + 24 : entry_off + 26], "big")
                sample_size = int.from_bytes(data[entry_off + 26 : entry_off + 28], "big")
                sample_rate = int.from_bytes(data[entry_off + 32 : entry_off + 36], "big") >> 16
                channel_str = "1 (Mono)" if channels == 1 else ("2 (Stereo)" if channels == 2 else f"{channels} Channels")
                sample_rate_str = f"{sample_rate} Hz ({sample_rate / 1000:.1f} kHz)"
                bit_depth_str = f"{sample_size}-bit" if sample_size > 0 else "16-bit"

            mvhd_idx = data.find(b"mvhd")
            if mvhd_idx != -1:
                v_off = mvhd_idx + 4
                ver = data[v_off]
                if ver == 1:
                    _, _, timescale, duration = struct.unpack(">QQII", data[v_off + 4 : v_off + 28])
                else:
                    _, _, timescale, duration = struct.unpack(">IIII", data[v_off + 4 : v_off + 20])
                if timescale > 0:
                    dur_sec = duration / timescale
                    duration_str = format_duration(dur_sec)
                    bitrate_str = f"{(file_size_bytes * 8 / dur_sec / 1000):.2f} kbps"
        except Exception:
            pass

    print("================================")
    print("AUDIO METADATA REPORT")
    print("================================")
    print()
    print(f"{'File Name':<16}: {file_name}")
    print(f"{'File Size':<16}: {file_size_str}")
    print(f"{'Container':<16}: {container}")
    print(f"{'Duration':<16}: {duration_str}")
    print()
    print("AUDIO")
    print("--------------------------------")
    print(f"{'Codec':<16}: {codec}")
    print(f"{'Channels':<16}: {channel_str}")
    print(f"{'Sampling Rate':<16}: {sample_rate_str}")
    print(f"{'Bit Depth':<16}: {bit_depth_str}")
    print(f"{'Bit Rate':<16}: {bitrate_str}")
    print(f"{'Total Frames':<16}: {total_frames_str}")


if __name__ == "__main__":
    possible_samples = [
        os.path.join("..", "multimedia_analyzer", "samples", "song.wav"),
        os.path.join("..", "datasets", "test.mp4"),
        os.path.join("multimedia_analyzer", "samples", "song.wav"),
    ]
    default_path = next((p for p in possible_samples if os.path.exists(p)), "")

    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        user_input = input(f"Enter audio path [Default: {default_path}]: ").strip()
        target_path = user_input if user_input else default_path

    analyze_audio(target_path)
