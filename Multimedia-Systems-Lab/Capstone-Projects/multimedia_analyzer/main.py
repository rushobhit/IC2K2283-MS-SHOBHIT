import os
import sys

from file_utils import validate_file, identify_file_type
from image_analyzer import ImageAnalyzer
from audio_analyzer import AudioAnalyzer
from video_analyzer import VideoAnalyzer
from report_generator import ReportGenerator


def process_file(file_path, export_json=True):
    """
    Main pipeline to validate, identify, analyze, and report on a media file.
    """
    # 1. File Validation
    is_valid, err_msg = validate_file(file_path)
    if not is_valid:
        print(f"\n[Error]: {err_msg}")
        return None

    # 2. Identify File Type
    media_type = identify_file_type(file_path)
    print(f"\n[Detected File Type]: {media_type}")

    # 3. Dispatch to Analyzer & Extract Metadata
    metadata = None
    if media_type == "IMAGE":
        analyzer = ImageAnalyzer(file_path)
        metadata = analyzer.analyze()
    elif media_type == "AUDIO":
        analyzer = AudioAnalyzer(file_path)
        metadata = analyzer.analyze()
    elif media_type == "VIDEO":
        analyzer = VideoAnalyzer(file_path)
        metadata = analyzer.analyze()
    else:
        print(f"[Error]: Unsupported or unrecognized media file type for '{file_path}'.")
        return None

    # 4. Generate & Display Report
    print()
    ReportGenerator.display_report(metadata)

    # 5. Export JSON Report
    if export_json:
        json_path = ReportGenerator.export_json(metadata)
        print(f"\n[Report Exported]: {json_path}")

    return metadata


def process_all_samples():
    """Processes all media files available in the samples/ directory and exports a consolidated JSON report."""
    base_dir = os.path.dirname(__file__)
    samples_dir = os.path.join(base_dir, "samples")
    if not os.path.exists(samples_dir):
        print(f"Error: Samples directory not found at '{samples_dir}'.")
        return

    sample_files = [
        os.path.join(samples_dir, f)
        for f in os.listdir(samples_dir)
        if os.path.isfile(os.path.join(samples_dir, f))
    ]

    if not sample_files:
        print(f"No sample files found in '{samples_dir}'.")
        return

    consolidated_results = []
    for sample in sample_files:
        meta = process_file(sample, export_json=False)
        if meta:
            consolidated_results.append(meta)
        print("\n" + "=" * 50)

    json_path = ReportGenerator.export_json(consolidated_results)
    print(f"\n[Consolidated JSON Report Exported for {len(consolidated_results)} files]: {json_path}")


def main():
    """Main CLI entrypoint."""
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() in ["--all", "-a", "all"]:
            process_all_samples()
        else:
            process_file(arg)
    else:
        # Interactive mode
        print("=" * 50)
        print("     CONSOLIDATED MULTIMEDIA ANALYZER         ")
        print("   (Supports Images, Audio, and Videos)       ")
        print("=" * 50)

        base_dir = os.path.dirname(__file__)
        default_video = os.path.join(base_dir, "samples", "video.mp4")
        if not os.path.exists(default_video):
            default_video = os.path.join(base_dir, "..", "datasets", "statue_of_unity.mp4")

        print("Options:")
        print("  - Enter path to an image, audio, or video file")
        print("  - Type 'all' to analyze all sample files in samples/")
        print(f"  - Press Enter to analyze default: {os.path.basename(default_video)}")
        print("-" * 50)

        user_input = input("Enter choice or file path: ").strip()

        if user_input.lower() == "all":
            process_all_samples()
        elif user_input:
            process_file(user_input)
        else:
            process_file(default_video)


if __name__ == "__main__":
    main()
