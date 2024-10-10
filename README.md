# Audio Transcriber

This is a Python script to transcribe audio using the Google Speech API.

## Prerequisites

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

`cd` to the application directory

Make sure the virtual environment has been activated:

```shell
source venv/bin/activate
```

And run the script, passing the path to the audio file you want to transcribe as a command-line argument:

```shell
./transcribe.py ~/Documents/my-audio.m4a
```

## License

This project is (c) [The Concord Consortium](https://concord.org) and licensed under the [MIT License](LICENSE).
