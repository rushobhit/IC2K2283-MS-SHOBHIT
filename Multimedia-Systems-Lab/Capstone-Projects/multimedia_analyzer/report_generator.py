import os
import json
from file_utils import get_file_size


class ReportGenerator:
    """
    Formats and displays metadata reports for Image, Audio, and Video files,
    and exports consolidated structured reports to JSON.
    """

    @staticmethod
    def print_image_report(data):
        """Prints formatted report for Image media."""
        file_size_str, _ = get_file_size(data["file_path"])
        print("================================")
        print("IMAGE METADATA REPORT")
        print("================================")
        print()
        print(f"{'File Name':<16}: {data['file_name']}")
        print(f"{'File Size':<16}: {file_size_str}")
        print(f"{'File Format':<16}: {data['file_format']}")
        print(f"{'Width':<16}: {data['width']} px")
        print(f"{'Height':<16}: {data['height']} px")
        print(f"{'Resolution':<16}: {data['dpi']}")
        print(f"{'Color Mode':<16}: {data['color_mode']}")
        print()
        print("EXIF Metadata")
        print("--------------------------------")
        exif = data.get("exif", {})
        print(f"{'Camera':<16}: {exif.get('camera', 'N/A')}")
        print(f"{'Date Taken':<16}: {exif.get('date_taken', 'N/A')}")
        print(f"{'Orientation':<16}: {exif.get('orientation', 'N/A')}")

    @staticmethod
    def print_audio_report(data):
        """Prints formatted report for Audio media."""
        file_size_str, _ = get_file_size(data["file_path"])
        print("================================")
        print("AUDIO METADATA REPORT")
        print("================================")
        print()
        print(f"{'File Name':<16}: {data['file_name']}")
        print(f"{'File Size':<16}: {file_size_str}")
        print(f"{'Container':<16}: {data['container']}")
        print(f"{'Duration':<16}: {data['duration']}")
        print()
        print("AUDIO")
        print("--------------------------------")
        print(f"{'Codec':<16}: {data['codec']}")
        print(f"{'Channels':<16}: {data['channels']}")
        print(f"{'Sampling Rate':<16}: {data['sample_rate']}")
        print(f"{'Bit Depth':<16}: {data['bit_depth']}")
        print(f"{'Bit Rate':<16}: {data['bitrate']}")
        print(f"{'Total Frames':<16}: {data['total_frames']}")

    @staticmethod
    def print_video_report(data):
        """Prints formatted report for Video media matching the requested specification."""
        file_size_str, _ = get_file_size(data["file_path"])
        v = data.get("video", {})
        a = data.get("audio", {})
        m = data.get("metadata", {})

        print("================================")
        print("VIDEO METADATA REPORT")
        print("================================")
        print()
        print(f"{'File Name':<16}: {data['file_name']}")
        print(f"{'File Size':<16}: {file_size_str}")
        print(f"{'Container':<16}: {data['container']}")
        print(f"{'Duration':<16}: {data['duration']}")
        print()
        print("VIDEO")
        print("--------------------------------")
        print(f"{'Resolution':<16}: {v.get('resolution', 'N/A')}")
        print(f"{'Frame Rate':<16}: {v.get('frame_rate', 'N/A')}")
        print(f"{'Bit Rate':<16}: {v.get('bit_rate', 'N/A')}")
        print(f"{'Codec':<16}: {v.get('codec', 'N/A')}")
        print()
        print("AUDIO")
        print("--------------------------------")
        print(f"{'Codec':<16}: {a.get('codec', 'N/A')}")
        print(f"{'Channels':<16}: {a.get('channels', 'N/A')}")
        print(f"{'Sampling Rate':<16}: {a.get('sampling_rate', 'N/A')}")
        print(f"{'Bit Rate':<16}: {a.get('bit_rate', 'N/A')}")
        print()
        print("METADATA")
        print("--------------------------------")
        print(f"{'Creation Time':<16}: {m.get('creation_time', 'N/A')}")
        print(f"{'Total Frames':<16}: {m.get('total_frames', 'N/A')}")
        print(f"{'Overall Bitrate':<16}: {m.get('overall_bitrate', 'N/A')}")
        print(f"{'Subtitles':<16}: {m.get('subtitles', 'None found')}")

    @classmethod
    def display_report(cls, metadata):
        """Dispatches metadata to the appropriate report printer based on media_type."""
        m_type = metadata.get("media_type")
        if m_type == "IMAGE":
            cls.print_image_report(metadata)
        elif m_type == "AUDIO":
            cls.print_audio_report(metadata)
        elif m_type == "VIDEO":
            cls.print_video_report(metadata)
        else:
            print("================================")
            print("UNKNOWN MEDIA TYPE")
            print("================================")
            print(json.dumps(metadata, indent=2))

    @staticmethod
    def export_json(report_data, output_path=None):
        """
        Exports metadata dictionary or list of metadata to JSON report file.
        """
        if output_path is None:
            base_dir = os.path.dirname(__file__)
            output_dir = os.path.join(base_dir, "reports")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "report.json")
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        return output_path
