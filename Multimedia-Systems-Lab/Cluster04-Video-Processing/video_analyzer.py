import os
import sys
import struct
import datetime
import mimetypes
import cv2


def format_file_size(size_bytes):
    """Formats file size into human-readable Bytes, KB, or MB."""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB ({size_bytes:,} bytes)"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB ({size_bytes:,} bytes)"


def format_duration(seconds):
    """Formats duration into seconds and MM:SS format."""
    if seconds <= 0:
        return "N/A"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{seconds:.2f} s ({mins:02d}:{secs:05.2f})"


def find_associated_subtitles(file_path):
    """
    Finds available companion/associated subtitle files without generating any.
    Searches for subtitle files matching the media filename (.srt, .vtt, .ass, etc.).
    """
    base_prefix = os.path.basename(os.path.splitext(file_path)[0])
    parent_dir = os.path.dirname(file_path) or "."
    sub_extensions = [".srt", ".vtt", ".sub", ".ass", ".sbv", ".lrc"]
    subtitles = []

    if os.path.exists(parent_dir):
        for item in os.listdir(parent_dir):
            name, ext = os.path.splitext(item)
            if ext.lower() in sub_extensions and name.startswith(base_prefix):
                subtitles.append(item)

    return subtitles


def parse_mp4_container(file_path):
    """
    Parses ISO Base Media (MP4 / MOV) atoms to extract track-level details,
    codecs, audio parameters, bitrates, and creation timestamps in pure Python.
    """
    info = {
        "container": "MP4 / QuickTime",
        "duration_sec": 0.0,
        "creation_time": None,
        "video_codec": None,
        "video_width": None,
        "video_height": None,
        "video_bitrate_kbps": None,
        "has_audio": False,
        "audio_codec": None,
        "audio_channels": None,
        "audio_sample_rate": None,
        "audio_bitrate_kbps": None,
    }

    try:
        with open(file_path, "rb") as f:
            data = f.read()

        def find_atoms(offset=0, limit=None):
            limit = limit if limit is not None else len(data)
            atoms = []
            curr = offset
            while curr + 8 <= limit:
                size, name = struct.unpack(">I4s", data[curr : curr + 8])
                name = name.decode("latin1", errors="ignore")
                if size == 1:
                    if curr + 16 > limit:
                        break
                    size = struct.unpack(">Q", data[curr + 8 : curr + 16])[0]
                    hdr_len = 16
                elif size == 0:
                    size = limit - curr
                    hdr_len = 8
                else:
                    hdr_len = 8

                if size < hdr_len or curr + size > limit:
                    break
                atoms.append((name, curr, size, hdr_len))
                curr += size
            return atoms

        def search_atom(target_name, offset=0, limit=None):
            for aname, aoff, asize, ahdr in find_atoms(offset, limit):
                if aname == target_name:
                    return (aoff, asize, ahdr)
            return None

        # Container brand
        ftyp = search_atom("ftyp")
        if ftyp:
            brand = data[ftyp[0] + 8 : ftyp[0] + 12].decode("latin1", errors="ignore").strip()
            info["container"] = f"MP4 (Brand: {brand})" if brand else "MP4"

        # Movie header (mvhd)
        moov = search_atom("moov")
        if moov:
            moov_off, moov_size, moov_hdr = moov
            mvhd = search_atom("mvhd", moov_off + moov_hdr, moov_off + moov_size)
            if mvhd:
                v_off = mvhd[0] + mvhd[2]
                version = data[v_off]
                if version == 1:
                    ctime, mtime, timescale, duration = struct.unpack(">QQII", data[v_off + 4 : v_off + 28])
                else:
                    ctime, mtime, timescale, duration = struct.unpack(">IIII", data[v_off + 4 : v_off + 20])

                if timescale > 0:
                    info["duration_sec"] = duration / timescale
                if ctime > 0:
                    mac_epoch = datetime.datetime(1904, 1, 1, tzinfo=datetime.timezone.utc)
                    info["creation_time"] = (mac_epoch + datetime.timedelta(seconds=ctime)).strftime("%Y-%m-%d %H:%M:%S UTC")

            # Parse each track (trak)
            for aname, aoff, asize, ahdr in find_atoms(moov_off + moov_hdr, moov_off + moov_size):
                if aname == "trak":
                    mdia = search_atom("mdia", aoff + ahdr, aoff + asize)
                    if mdia:
                        hdlr = search_atom("hdlr", mdia[0] + mdia[2], mdia[0] + mdia[1])
                        htype = ""
                        if hdlr and (hdlr[0] + hdlr[2] + 12 <= len(data)):
                            htype = data[hdlr[0] + hdlr[2] + 8 : hdlr[0] + hdlr[2] + 12].decode("latin1", errors="ignore")

                        minf = search_atom("minf", mdia[0] + mdia[2], mdia[0] + mdia[1])
                        if minf:
                            stbl = search_atom("stbl", minf[0] + minf[2], minf[0] + minf[1])
                            if stbl:
                                # Calculate track payload bytes
                                stsz = search_atom("stsz", stbl[0] + stbl[2], stbl[0] + stbl[1])
                                track_bytes = 0
                                if stsz:
                                    sz_off = stsz[0] + stsz[2]
                                    sample_uniform, count = struct.unpack(">II", data[sz_off + 4 : sz_off + 12])
                                    if sample_uniform != 0:
                                        track_bytes = sample_uniform * count
                                    elif sz_off + 12 + count * 4 <= len(data):
                                        sizes = struct.unpack(f">{count}I", data[sz_off + 12 : sz_off + 12 + count * 4])
                                        track_bytes = sum(sizes)

                                stsd = search_atom("stsd", stbl[0] + stbl[2], stbl[0] + stbl[1])
                                if stsd:
                                    entry_off = stsd[0] + stsd[2] + 8
                                    if entry_off + 8 <= len(data):
                                        entry_size, format_code = struct.unpack(">I4s", data[entry_off : entry_off + 8])
                                        format_str = format_code.decode("latin1", errors="ignore")

                                        # Audio stream
                                        if htype == "soun":
                                            info["has_audio"] = True
                                            codec_map = {"mp4a": "AAC (mp4a)", "ac-3": "AC-3", "samr": "AMR", "alac": "ALAC"}
                                            info["audio_codec"] = codec_map.get(format_str, format_str)

                                            if entry_off + 36 <= len(data):
                                                ch = int.from_bytes(data[entry_off + 24 : entry_off + 26], "big")
                                                sr = int.from_bytes(data[entry_off + 32 : entry_off + 36], "big") >> 16
                                                info["audio_channels"] = ch
                                                info["audio_sample_rate"] = sr

                                            if info["duration_sec"] > 0 and track_bytes > 0:
                                                info["audio_bitrate_kbps"] = (track_bytes * 8) / info["duration_sec"] / 1000

                                        # Video stream
                                        elif htype == "vide":
                                            codec_map = {
                                                "avc1": "H.264 / AVC (avc1)",
                                                "hvc1": "H.265 / HEVC (hvc1)",
                                                "hev1": "H.265 / HEVC (hev1)",
                                                "vp09": "VP9",
                                                "av01": "AV1",
                                            }
                                            info["video_codec"] = codec_map.get(format_str, format_str)

                                            if entry_off + 36 <= len(data):
                                                w, h = struct.unpack(">HH", data[entry_off + 32 : entry_off + 36])
                                                if w > 0 and h > 0:
                                                    info["video_width"] = w
                                                    info["video_height"] = h

                                            if info["duration_sec"] > 0 and track_bytes > 0:
                                                info["video_bitrate_kbps"] = (track_bytes * 8) / info["duration_sec"] / 1000
    except Exception:
        pass

    return info


def analyze_video(video_path):
    """
    Inspects a video file and displays a clean, structured video metadata report.
    """
    if not os.path.exists(video_path):
        print(f"Error: Could not find video file at '{video_path}'.")
        return

    file_name = os.path.basename(video_path)
    file_size_bytes = os.path.getsize(video_path)
    file_size_str = format_file_size(file_size_bytes)

    # 1. OpenCV Frame and Codec extraction
    v_width, v_height, v_fps, v_frames, cv_codec = 0, 0, 0.0, 0, ""
    cv_duration_sec = 0.0

    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        v_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        v_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        v_fps = cap.get(cv2.CAP_PROP_FPS)
        v_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        raw_codec = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
        cv_codec = raw_codec.replace("\x00", "").strip()
        if v_fps > 0 and v_frames > 0:
            cv_duration_sec = v_frames / v_fps
        cap.release()

    # 2. Container and Audio/Video parsing
    ext = os.path.splitext(video_path)[1].lower()
    mp4_info = parse_mp4_container(video_path) if ext in [".mp4", ".m4v", ".mov"] else {}

    # Resolve Container
    container = mp4_info.get("container")
    if not container:
        mime, _ = mimetypes.guess_type(video_path)
        container = mime if mime else (ext.upper().lstrip(".") or "Unknown")

    # Resolve Duration
    duration_sec = mp4_info.get("duration_sec") or cv_duration_sec
    duration_str = format_duration(duration_sec)

    # Resolve Video properties
    width = mp4_info.get("video_width") or v_width
    height = mp4_info.get("video_height") or v_height
    video_codec = mp4_info.get("video_codec") or (cv_codec.strip() if cv_codec.strip() else "None / No video stream detected")
    video_bitrate = mp4_info.get("video_bitrate_kbps")

    if width > 0 and height > 0:
        if width / height == 16 / 9:
            ar = "16:9"
        elif width / height == 4 / 3:
            ar = "4:3"
        elif height / width == 16 / 9:
            ar = "9:16 (Vertical)"
        else:
            ar = f"{width}:{height}"
        resolution_str = f"{width} x {height} ({ar})"
    else:
        resolution_str = "N/A"

    frame_rate_str = f"{v_fps:.2f} FPS" if (v_fps > 0 and width > 0 and height > 0) else "N/A"
    video_bitrate_str = f"{video_bitrate:.2f} kbps" if video_bitrate else "N/A"

    # Resolve Audio properties
    has_audio = mp4_info.get("has_audio", False)
    if has_audio:
        audio_codec = mp4_info.get("audio_codec", "Unknown")
        ch_count = mp4_info.get("audio_channels")
        channels_str = (
            "2 (Stereo)" if ch_count == 2 else ("1 (Mono)" if ch_count == 1 else (f"{ch_count} Channels" if ch_count else "N/A"))
        )
        sample_rate = mp4_info.get("audio_sample_rate")
        sampling_rate_str = f"{sample_rate} Hz ({sample_rate / 1000:.1f} kHz)" if sample_rate else "N/A"
        audio_bitrate = mp4_info.get("audio_bitrate_kbps")
        audio_bitrate_str = f"{audio_bitrate:.2f} kbps" if audio_bitrate else "N/A"
    else:
        audio_codec = "None / No audio stream detected"
        channels_str = "N/A"
        sampling_rate_str = "N/A"
        audio_bitrate_str = "N/A"

    # Resolve Metadata
    creation_time = mp4_info.get("creation_time")
    if not creation_time:
        file_mtime = os.path.getmtime(video_path)
        creation_time = datetime.datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")

    total_frames_str = f"{v_frames} frames" if v_frames > 0 else "N/A"
    overall_bitrate = (file_size_bytes * 8 / duration_sec / 1000) if duration_sec > 0 else 0
    overall_bitrate_str = f"{overall_bitrate:.2f} kbps" if overall_bitrate > 0 else "N/A"

    subtitles = find_associated_subtitles(video_path)
    subtitles_str = ", ".join(subtitles) if subtitles else "None found"

    # Output formatted report
    print("================================")
    print("VIDEO METADATA REPORT")
    print("================================")
    print()
    print(f"{'File Name':<16}: {file_name}")
    print(f"{'File Size':<16}: {file_size_str}")
    print(f"{'Container':<16}: {container}")
    print(f"{'Duration':<16}: {duration_str}")
    print()
    print("VIDEO")
    print("--------------------------------")
    print(f"{'Resolution':<16}: {resolution_str}")
    print(f"{'Frame Rate':<16}: {frame_rate_str}")
    print(f"{'Bit Rate':<16}: {video_bitrate_str}")
    print(f"{'Codec':<16}: {video_codec}")
    print()
    print("AUDIO")
    print("--------------------------------")
    print(f"{'Codec':<16}: {audio_codec}")
    print(f"{'Channels':<16}: {channels_str}")
    print(f"{'Sampling Rate':<16}: {sampling_rate_str}")
    print(f"{'Bit Rate':<16}: {audio_bitrate_str}")
    print()
    print("METADATA")
    print("--------------------------------")
    print(f"{'Creation Time':<16}: {creation_time}")
    print(f"{'Total Frames':<16}: {total_frames_str}")
    print(f"{'Overall Bitrate':<16}: {overall_bitrate_str}")
    print(f"{'Subtitles':<16}: {subtitles_str}")


if __name__ == "__main__":
    # Look for sample file from datasets
    possible_samples = [
        os.path.join("datasets", "statue_of_unity.mp4"),
        os.path.join("..", "datasets", "statue_of_unity.mp4"),
        os.path.join(os.path.dirname(__file__), "..", "datasets", "statue_of_unity.mp4"),
    ]
    default_path = next((p for p in possible_samples if os.path.exists(p)), "datasets/statue_of_unity.mp4")

    # If argument provided, use it; otherwise ask user or use default
    if len(sys.argv) > 1:
        target_path = sys.argv[1]
    else:
        user_input = input(f"Enter video path [Default: {default_path}]: ").strip()
        target_path = user_input if user_input else default_path

    analyze_video(target_path)
