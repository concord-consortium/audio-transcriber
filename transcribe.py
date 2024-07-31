#!/usr/bin/env python3

# See README for prerequisites and setup instructions.

# TODO: use asynch API so audio files over 1 minute can be processed:
#      https://cloud.google.com/speech-to-text/docs/async-recognize
# TODO: detect different speakers:
#      https://cloud.google.com/speech-to-text/docs/multiple-voices

import os
import sys
from pydub import AudioSegment
from google.cloud import speech

def usage():
  sys.stderr.write("Usage: " + sys.argv[0] + " <audio_file_path>\n")
  exit(1)

# Read command-line arguments:
if (sys.argv.__len__() != 2):
  usage()

audio_file_path = sys.argv[1]
# Check if file exists and is readable
try:
  with open(audio_file_path, "rb") as f:
    pass
except IOError:
  sys.stderr.write("Error: File " + audio_file_path + " not accessible.\n")
  usage()

import tempfile
from pydub import AudioSegment
from google.cloud import speech

def send_file_to_api(path) -> speech.RecognizeResponse:
  client = speech.SpeechClient()

  # Create a temp file for the FLAC audio
  with tempfile.NamedTemporaryFile(suffix=".flac", delete=True) as temp_flac_file:
    flac_file_path = temp_flac_file.name

    audio = AudioSegment.from_file(path)

    # Just use the part starting at 2:00, which includes multiple speakers.
    # audio_sample = audio[120000:]

    # Convert to FLAC format
    audio.export(flac_file_path, format="flac")

    # Read audio bytes from a local file
    with open(flac_file_path, "rb") as audio_file:
      audio = speech.RecognitionAudio(content=audio_file.read())

    config = speech.RecognitionConfig(
      encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
      language_code="en-US",
    )

    # Detects speech in the audio file
    return client.recognize(config=config, audio=audio)
    # print(response)

def print_transcript(response: speech.RecognizeResponse):
    for result in response.results:
      print(f"Transcript: {result.alternatives[0].transcript}")

response = send_file_to_api(audio_file_path)
print_transcript(response)
