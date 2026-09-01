import os
import struct
import datetime
import mimetypes
import cv2


class VideoAnalyzer:
    """
    Analyzes video files to extract container properties, video stream attributes,
    embedded audio stream attributes, and associated subtitle files.
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def _find_subtitles(self):
        base_prefix = os.path.basename(os.path.splitext(self.file_path)[0])
        parent_dir = os.path.dirname(self.file_path) or "."
        sub_exts = [".srt", ".vtt", ".sub", ".ass", ".sbv", ".lrc"]
        subtitles = []

        if os.path.exists(parent_dir):
            for item in os.listdir(parent_dir):
                name, ext = os.path.splitext(item)
                if ext.lower() in sub_exts and name.startswith(base_prefix):
                    subtitles.append(item)
        return subtitles

    def _parse_mp4_atoms(self):
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
            with open(self.file_path, "rb") as f:
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

            ftyp = search_atom("ftyp")
            if ftyp:
                brand = data[ftyp[0] + 8 : ftyp[0] + 12].decode("latin1", errors="ignore").strip()
                info["container"] = f"MP4 (Brand: {brand})" if brand else "MP4"

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

    def analyze(self):
        """
        Performs analysis and returns a structured dictionary of video metadata.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Video file not found at '{self.file_path}'")

        file_name = os.path.basename(self.file_path)
        size_bytes = os.path.getsize(self.file_path)

        # 1. OpenCV extraction
        v_width, v_height, v_fps, v_frames, cv_codec = 0, 0, 0.0, 0, ""
        cv_duration_sec = 0.0

        cap = cv2.VideoCapture(self.file_path)
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

        # 2. Container and MP4 atom inspection
        ext = os.path.splitext(self.file_path)[1].lower()
        mp4_info = self._parse_mp4_atoms() if ext in [".mp4", ".m4v", ".mov"] else {}

        container = mp4_info.get("container")
        if not container:
            mime, _ = mimetypes.guess_type(self.file_path)
            container = mime if mime else (ext.upper().lstrip(".") or "Unknown")

        duration_sec = mp4_info.get("duration_sec") or cv_duration_sec
        mins = int(duration_sec // 60)
        secs = duration_sec % 60
        duration_str = f"{duration_sec:.2f} s ({mins:02d}:{secs:05.2f})" if duration_sec > 0 else "N/A"

        width = mp4_info.get("video_width") or v_width
        height = mp4_info.get("video_height") or v_height
        video_codec = mp4_info.get("video_codec") or (cv_codec if cv_codec else "None / No video stream detected")
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

        # Audio section
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

        creation_time = mp4_info.get("creation_time")
        if not creation_time:
            file_mtime = os.path.getmtime(self.file_path)
            creation_time = datetime.datetime.fromtimestamp(file_mtime).strftime("%Y-%m-%d %H:%M:%S")

        total_frames_str = f"{v_frames} frames" if v_frames > 0 else "N/A"
        overall_bitrate = (size_bytes * 8 / duration_sec / 1000) if duration_sec > 0 else 0
        overall_bitrate_str = f"{overall_bitrate:.2f} kbps" if overall_bitrate > 0 else "N/A"

        subtitles = self._find_subtitles()
        subtitles_str = ", ".join(subtitles) if subtitles else "None found"

        return {
            "media_type": "VIDEO",
            "file_name": file_name,
            "file_path": os.path.abspath(self.file_path),
            "file_size_bytes": size_bytes,
            "container": container,
            "duration": duration_str,
            "duration_seconds": duration_sec,
            "video": {
                "resolution": resolution_str,
                "width": width,
                "height": height,
                "frame_rate": frame_rate_str,
                "fps": v_fps,
                "bit_rate": video_bitrate_str,
                "bitrate_kbps": video_bitrate,
                "codec": video_codec,
            },
            "audio": {
                "has_audio": has_audio,
                "codec": audio_codec,
                "channels": channels_str,
                "sampling_rate": sampling_rate_str,
                "bit_rate": audio_bitrate_str,
            },
            "metadata": {
                "creation_time": creation_time,
                "total_frames": total_frames_str,
                "overall_bitrate": overall_bitrate_str,
                "subtitles": subtitles_str,
                "subtitle_list": subtitles,
            },
        }


def analyze_video(file_path):
    """Utility function for quick video analysis."""
    return VideoAnalyzer(file_path).analyze()


if __name__ == "__main__":
    import sys
    sample_path = sys.argv[1] if len(sys.argv) > 1 else "../datasets/statue_of_unity.mp4"
    analyzer = VideoAnalyzer(sample_path)
    res = analyzer.analyze()
    print("Container       :", res["container"])
    print("Video Codec     :", res["video"]["codec"])
    print("Audio Codec     :", res["audio"]["codec"])
