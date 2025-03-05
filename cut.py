import subprocess
import shutil
import sys
from pathlib import Path
import librosa
import numpy as np
from scipy.signal import fftconvolve  # Faster correlation using FFT

def check_ffmpeg():
    """Check if FFmpeg is installed and available in PATH."""
    if not shutil.which("ffmpeg"):
        print("Error: FFmpeg is not installed or not in PATH.")
        sys.exit(1)

def extract_audio(input_file, output_wav):
    """Extracts the audio from a video file as a WAV for analysis."""
    command = [
        "ffmpeg", "-y",
        "-i", str(input_file),
        "-ac", "1",  # Convert to mono for easier analysis
        "-ar", "14700",  # Normalize sample rate
        "-vn", "-f", "wav",
        str(output_wav)
    ]
    subprocess.run(command, check=True)

def find_audio_offset(video_audio, external_audio):
    """Finds the best alignment offset (in seconds) using FFT cross-correlation."""
    print("  Load audio...")
    video_y, sr = librosa.load(video_audio, sr=14700)
    wav_y, _ = librosa.load(external_audio, sr=14700)

    # cut wav_y down to 1 minute, which is enough for a match and makes the correlation A LOT faster.
    wav_y = wav_y[:sr*60]

    # Compute FFT-based cross-correlation (faster than a normal correlation)
    print("  Correlate...")
    correlation = fftconvolve(video_y, wav_y[::-1], mode="full")
    best_offset = np.argmax(correlation) - len(wav_y)

    # check that the correlation is good enough
    if np.max(correlation) < 1000:
        print("Error: No good alignment found.  Are you sure the audio and video match?")
        sys.exit(1)

    # Convert sample index to seconds
    offset_seconds = best_offset / sr

    print(f"  Best offset: {offset_seconds:.2f} seconds ({np.max(correlation):.0f} correlation)")

    return max(offset_seconds, 0)  # Ensure it's non-negative

def get_audio_duration(audio_file):
    """Get the duration of the WAV file using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-i", str(audio_file), "-show_entries", "format=duration", 
             "-v", "quiet", "-of", "csv=p=0"],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())
    except subprocess.CalledProcessError:
        print("Error: Could not determine audio duration.")
        sys.exit(1)

def get_video_bitrate(video_file):
    """Extracts the video bitrate using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=bit_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_file
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        bitrate = result.stdout.strip()
        return int(bitrate) if bitrate.isdigit() else None
    except Exception as e:
        print(f"Error getting bitrate: {e}")
        return None

def process_video(input_video, input_audio, output_video):
    """Aligns audio, trims video, and applies fade in a single pass."""
    check_ffmpeg()

    duration = get_audio_duration(input_audio)

    extracted_audio = input_video.parent / "temp_video_audio.wav"
    extract_audio(input_video, extracted_audio)

    print("Finding best alignment...")
    offset_seconds = find_audio_offset(extracted_audio, input_audio)
    print(f"Best offset found: {offset_seconds:.2f} seconds")

    print("Getting video bitrate...")
    bitrate = get_video_bitrate(input_video)

    # FFmpeg command: 
    # - Shift video start time to align with audio
    # - Trim to match the audio length
    # - Apply fade to black
    command = [
        "ffmpeg", "-y",
        "-ss", str(offset_seconds),  # Shift video start time (needs to be before -i to which it applies)
        "-i", str(input_video),  # Input video
        "-i", str(input_audio),  # Input audio
        "-map", "0:v:0",  # Select first video stream from input.mp4
        "-map", "1:a:0",  # Select first audio stream from input.wav
        "-c:v", "libx265",
        "-c:a", "aac",
        "-b:v", str(bitrate),
        "-b:a", "128k",
        "-t", str(duration),  # Trim to match new audio length
        "-vf", f"fade=t=out:st={duration-1}:d=1",  # Apply fade
        str(output_video)
    ]

    print("Processing video with synchronized audio and fade-to-black...")
    print("  " + " ".join(command))
    subprocess.run(command, check=True)
    print(f"Process complete! Output saved as {output_video}")

    # Cleanup temporary files
    extracted_audio.unlink(missing_ok=True)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python process_video.py <input.mp4> <input.wav> <output.mp4>")
        sys.exit(1)

    input_video = Path(sys.argv[1])
    input_audio = Path(sys.argv[2])
    output_video = Path(sys.argv[3])

    if not input_video.exists() or not input_audio.exists():
        print("Error: One or more input files do not exist.")
        sys.exit(1)

    process_video(input_video, input_audio, output_video)