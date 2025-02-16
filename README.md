# Sermon Slicer

This is a python script that we use to trim video recordings of our sermons.  Immediately after a service, 
our tech volunteers use our DAW to trim a clean audio recording of the sermon.  They export this as a wav 
file.  This wav file is a prerequisite for this tool, because this script trims the video to match the 
bounds of the audio file.  This script:

- Aligns the audio and video files, based on their audio tracks.
- Trims the video to the bounds of the audio
- Adds a 1-second fade-to-black at the end
- Renders an output video (x265) with the audio from the (cleaned) audio input file and the video (but not
  audio) from the video input file.

The script assumes that python and ffmpeg are installed, along with several python packages. The Windows
installer script (which probably needs to be run as an administrator) will automatically install both
python and ffmpeg using winget, and then will use pip to install the python packages. 

## Usage

```bash
.\cut.py input_video_file input_audio_file output_file
```

It is assumed that the input video is H.264 video (.mp4) and the input audio file is .wav because that's 
what we use, but theoretically other formats may work, too.  The output file will be H.265 at the
same video bitrate as the input video file. 
