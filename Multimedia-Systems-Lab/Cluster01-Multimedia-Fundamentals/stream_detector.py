import os
import mimetypes

def detect_stream_type(file_path):
    """
    Checks if a given multimedia file is an Audio Stream or Video Stream.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at '{file_path}'"

    # Guess MIME type based on file extension
    mime_type, _ = mimetypes.guess_type(file_path)

    if mime_type:
        if mime_type.startswith("video"):
            return f"[VIDEO STREAM] MIME Type: {mime_type}"
        elif mime_type.startswith("audio"):
            return f"[AUDIO STREAM] MIME Type: {mime_type}"

    return "[UNKNOWN] Could not determine stream type."


if __name__ == "__main__":
    # Default sample file from datasets folder
    default_path = r"../datasets/statue_of_unity.mp4"

    # Ask for user input or fall back to default
    file_path = input(f"Enter file path [Default: {default_path}]: ").strip()
    if not file_path:
        file_path = default_path

    print("\n" + "=" * 40)
    print(f"Checking File : {os.path.basename(file_path)}")
    print(f"Result        : {detect_stream_type(file_path)}")
    print("=" * 40)
