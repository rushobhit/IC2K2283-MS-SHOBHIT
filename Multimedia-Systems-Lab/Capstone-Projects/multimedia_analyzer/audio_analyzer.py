import os
import wave
import struct
import mimetypes


class AudioAnalyzer:
    """
    Analyzes audio files to extract channels, sampling rates, bit depths,
    codecs, durations, and bitrates without requiring external binaries.
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def analyze(self):
        """
        Performs analysis and returns a structured dictionary of audio metadata.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Audio file not found at '{self.file_path}'")

        file_name = os.path.basename(self.file_path)
        size_bytes = os.path.getsize(self.file_path)
        ext = os.path.splitext(self.file_path)[1].lower()

        # Defaults
        codec = "Unknown Audio Codec"
        container = ext.upper().lstrip(".")
        channels = 0
        channel_str = "N/A"
        sample_rate = 0
        sample_rate_str = "N/A"
        bit_depth_str = "N/A"
        total_frames = 0
        duration_sec = 0.0
        bitrate_kbps = 0.0
        tags = {}

        # 1. Handle WAV files
        if ext == ".wav":
            try:
                with wave.open(self.file_path, "rb") as w:
                    channels = w.getnchannels()
                    sampwidth = w.getsampwidth()
                    sample_rate = w.getframerate()
                    total_frames = w.getnframes()
                    if sample_rate > 0:
                        duration_sec = total_frames / float(sample_rate)
                    codec = "PCM (Pulse Code Modulation)"
                    container = "WAV (Waveform Audio File Format)"
                    bit_depth_str = f"{sampwidth * 8}-bit"
                    channel_str = "1 (Mono)" if channels == 1 else ("2 (Stereo)" if channels == 2 else f"{channels} Channels")
                    sample_rate_str = f"{sample_rate} Hz ({sample_rate / 1000:.1f} kHz)"
                    bitrate_kbps = (sample_rate * channels * sampwidth * 8) / 1000
            except Exception:
                pass

        # 2. Handle MP3 files
        elif ext == ".mp3":
            container = "MP3 (MPEG-1 Audio Layer III)"
            codec = "MPEG Audio Layer III (MP3)"
            try:
                with open(self.file_path, "rb") as f:
                    data = f.read()

                # Parse ID3 tags if present
                if data.startswith(b"ID3"):
                    id3_size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
                    audio_data_start = 10 + id3_size
                else:
                    audio_data_start = 0

                # Search for MPEG Sync word (0xFFE or 0xFFF)
                bitrates_v1_l3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
                samplerates_v1 = [44100, 48000, 32000, 0]

                idx = audio_data_start
                while idx < len(data) - 4:
                    if data[idx] == 0xFF and (data[idx + 1] & 0xE0) == 0xE0:
                        b1 = data[idx + 1]
                        b2 = data[idx + 2]
                        b3 = data[idx + 3]

                        version = (b1 >> 3) & 0x03  # 3 = MPEG v1
                        layer = (b1 >> 1) & 0x03    # 1 = Layer 3
                        br_idx = (b2 >> 4) & 0x0F
                        sr_idx = (b2 >> 2) & 0x03
                        ch_mode = (b3 >> 6) & 0x03  # 3 = Single channel (Mono)

                        if version == 3 and layer == 1 and br_idx < 15 and sr_idx < 3:
                            bitrate_kbps = bitrates_v1_l3[br_idx]
                            sample_rate = samplerates_v1[sr_idx]
                            channels = 1 if ch_mode == 3 else 2
                            channel_str = "1 (Mono)" if channels == 1 else "2 (Stereo)"
                            sample_rate_str = f"{sample_rate} Hz ({sample_rate / 1000:.1f} kHz)"
                            bit_depth_str = "16-bit (Equivalent)"

                            audio_bytes = len(data) - audio_data_start
                            if bitrate_kbps > 0:
                                duration_sec = (audio_bytes * 8) / (bitrate_kbps * 1000)
                            break
                    idx += 1
            except Exception:
                pass

        # 3. Handle M4A / AAC container
        elif ext in [".m4a", ".aac", ".mp4"]:
            container = "MPEG-4 Audio (M4A / AAC)"
            codec = "AAC (Advanced Audio Coding)"
            try:
                with open(self.file_path, "rb") as f:
                    data = f.read()

                idx = data.find(b"mp4a")
                if idx != -1:
                    entry_off = idx - 4
                    channels = int.from_bytes(data[entry_off + 24 : entry_off + 26], "big")
                    sample_size = int.from_bytes(data[entry_off + 26 : entry_off + 28], "big")
                    sample_rate = int.from_bytes(data[entry_off + 32 : entry_off + 36], "big") >> 16
                    bit_depth_str = f"{sample_size}-bit" if sample_size > 0 else "16-bit"
                    channel_str = "1 (Mono)" if channels == 1 else ("2 (Stereo)" if channels == 2 else f"{channels} Channels")
                    sample_rate_str = f"{sample_rate} Hz ({sample_rate / 1000:.1f} kHz)"

                # Timescale duration from mvhd
                mvhd_idx = data.find(b"mvhd")
                if mvhd_idx != -1:
                    v_off = mvhd_idx + 4
                    ver = data[v_off]
                    if ver == 1:
                        _, _, timescale, duration = struct.unpack(">QQII", data[v_off + 4 : v_off + 28])
                    else:
                        _, _, timescale, duration = struct.unpack(">IIII", data[v_off + 4 : v_off + 20])
                    if timescale > 0:
                        duration_sec = duration / timescale
                        bitrate_kbps = (size_bytes * 8) / duration_sec / 1000
            except Exception:
                pass

        # Format duration
        mins = int(duration_sec // 60)
        secs = duration_sec % 60
        duration_str = f"{duration_sec:.2f} s ({mins:02d}:{secs:05.2f})" if duration_sec > 0 else "N/A"

        return {
            "media_type": "AUDIO",
            "file_name": file_name,
            "file_path": os.path.abspath(self.file_path),
            "file_size_bytes": size_bytes,
            "container": container,
            "codec": codec,
            "channels": channel_str,
            "channel_count": channels,
            "sample_rate": sample_rate_str,
            "sampling_rate_hz": sample_rate,
            "bit_depth": bit_depth_str,
            "total_frames": f"{total_frames:,}" if total_frames > 0 else "N/A",
            "duration": duration_str,
            "duration_seconds": duration_sec,
            "bitrate": f"{bitrate_kbps:.2f} kbps" if bitrate_kbps > 0 else "N/A",
            "bitrate_kbps": bitrate_kbps,
            "tags": tags,
        }


def analyze_audio(file_path):
    """Utility function for quick audio analysis."""
    return AudioAnalyzer(file_path).analyze()


if __name__ == "__main__":
    import sys
    sample_path = sys.argv[1] if len(sys.argv) > 1 else "../datasets/test.mp4"
    analyzer = AudioAnalyzer(sample_path)
    res = analyzer.analyze()
    print("Audio Codec      :", res["codec"])
    print("Channels         :", res["channels"])
    print("Sampling Rate    :", res["sample_rate"])
    print("Duration         :", res["duration"])
