# Audio Transcriber

This repository contains two Python scripts for transcribing audio:
1. `transcribe.py` - Uses Google Speech API
2. `transcribe_faster_whisper.py` - Uses FasterWhisper (offline transcription)

## Prerequisites

### For Google Speech API (transcribe.py)

This script requires you to have a Google Cloud project with the Speech API enabled (which requires billing to be enabled).

- Set up Google Cloud project and access to that project for users of this script.
- Make sure billing is enabled.
- Activate the Google Cloud Speech-to-Text API for the project.
- Create a storage bucket for temporarily holding audio files; put its name in the script

You must also have the Google Cloud command-line tools set up on the machine you will use to run this script.

- Install the gcloud command line tools following the steps in [the official documentation](https://cloud.google.com/sdk/docs/install)
- Follow the steps all the way through running `gcloud init`.
  - When asked for a default project, use the one just created above.
- Log in to Google Cloud: `gcloud auth application-default login`

### For FasterWhisper (transcribe_faster_whisper.py)

- Python 3.8 or higher
- FFmpeg for audio processing
- Sufficient disk space for the FasterWhisper model (approximately 1GB for the large-v2 model)

## Installation

Install Python and the audio-conversion tool FFMpeg:

```shell
brew install python
brew install ffmpeg
```

Clone this repository and `cd` into its directory.

Create virtual environment for python:

```shell
/opt/homebrew/bin/python3 -m venv venv
source venv/bin/activate
```

And install the required Python packages:

```shell
pip install -r requirements.txt
```

## Usage

### Google Speech API (transcribe.py)

`cd` to the application directory

Make sure the virtual environment has been activated:

```shell
source venv/bin/activate
```

And run the script, passing the path to the audio file you want to transcribe as a command-line argument:

```shell
./transcribe.py ~/Documents/my-audio.m4a
```

### FasterWhisper (transcribe_faster_whisper.py)

`cd` to the application directory

Make sure the virtual environment has been activated:

```shell
source venv/bin/activate
```

Run the script with your audio file:

```shell
python3 transcribe_faster_whisper.py path/to/your/audio/file.mp4
```

The script will:
- Convert the audio to WAV format
- Load the FasterWhisper model
- Transcribe the audio
- Output the transcription to both the console and a CSV file

The CSV file will be saved in the same directory as your input file, with the same name but a `.csv` extension.

#### Limitations of FasterWhisper

- Transcription quality may vary depending on audio quality, accents, and background noise
- The large-v2 model requires approximately 1GB of disk space
- Processing time depends on the length of the audio file and your computer's capabilities
- Speaker diarization is basic and may not be as accurate as specialized diarization models

#### Requirements for FasterWhisper

- Python 3.8 or higher
- FFmpeg installed and accessible in your PATH
- Sufficient disk space for the model
- The following Python packages (installed via requirements.txt):
  - faster-whisper
  - pydub
  - numpy
  - torch
  - scipy (for speaker diarization)

#### Speaker Diarization

The FasterWhisper script now includes basic speaker diarization capabilities:
- Uses spectrogram-based feature extraction and k-means clustering
- Identifies different speakers in the audio
- Outputs speaker labels (Speaker 1, Speaker 2, etc.) in the CSV file
- Default number of speakers is 6, but can be adjusted in the code
- No external models required for diarization

## License

This project is (c) [The Concord Consortium](https://concord.org) and licensed under the [MIT License](LICENSE).
