import subprocess
import sys
import os


def process_video(input_path: str, output_path: str, trim_start: float, trim_end: float, target_size_mb: float):
    duration = trim_end - trim_start
    
    if duration <= 0:
        raise ValueError("trim_end must be greater than trim_start")


    SAFETY_MARGIN = 0.92  # a small buffer to avoid overshooting in MOST cases
    AUDIO_KBPS = 128

    total_kbps = int((target_size_mb * 8 * 1024) / duration)
    video_kbps = int(total_kbps * SAFETY_MARGIN) - AUDIO_KBPS
    video_kbps = max(100, video_kbps) 

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(trim_start),
        "-to", str(trim_end),
        "-i", input_path,
        "-c:v", "libx264",
        "-b:v", f"{video_kbps}k",
        "-c:a", "aac",
        "-b:a", f"{AUDIO_KBPS}k",
        output_path,
    ]

    print(f"\nRUNNING: {' '.join(cmd)}\n")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg exited with code {result.returncode}")

    actual_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nDONE! output size: {actual_size:.2f} MB (target was {target_size_mb} MB)")



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python compress.py <input.mp4>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = input_file.replace(".mp4", "_out.mp4")

    process_video(
        input_path=input_file,
        output_path=output_file,
        trim_start=2.0,
        trim_end=10.0,
        target_size_mb=10.0,
    )