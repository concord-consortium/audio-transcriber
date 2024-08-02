#!/usr/bin/env python3

# See README for prerequisites and setup instructions.

import os
import sys
import tempfile
from pydub import AudioSegment
from urllib.parse import urlparse
from google.cloud import speech
from google.cloud import storage

bucket_name = "concord_consortium_audio_transcriber"
storage_client = storage.Client()


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

#### Google API methods ####

def convert_to_flac(audio_file_path, temp_flac_file):
    """Converts an audio file to FLAC format."""
    flac_file_path = temp_flac_file.name
    sys.stderr.write(f"Converting audio to FLAC...\n")
    audio = AudioSegment.from_file(audio_file_path)
    audio.export(flac_file_path, format="flac")
    return temp_flac_file


def upload_file_to_bucket(file):
    """Uploads a file to the Google Cloud Storage bucket, returns URL"""
    filename = os.path.basename(file.name)
    print(f"Uploading to {bucket_name}/{filename}...")
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_filename(file.name)
    return f"gs://{bucket_name}/{filename}"


def remove_file_from_bucket(url):
    """Removes a file from the Google Cloud Storage bucket given its URL."""
    parsed_url = urlparse(url)
    bucket_name = parsed_url.netloc
    file_path = parsed_url.path.lstrip('/')
    
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    blob.delete()
    # print(f"File {file_path} deleted from bucket {bucket_name}.")


def transcribe_url(uri) -> speech.RecognizeResponse:
    """Submits the transcription job to the Google Speech-to-Text API."""
    sys.stderr.write(f"Transcribing audio...\n")
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(uri=uri)
    speaker_diarization_config = speech.SpeakerDiarizationConfig(
        enable_speaker_diarization=True,
        min_speaker_count=1,
        max_speaker_count=5,
    )
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        model="latest_long",
        # enable_automatic_punctuation=True,
        language_code="en-US",
        diarization_config=speaker_diarization_config,
    )
    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result()    # could add timeout=90 to wait up to 90 seconds
    return response


def print_transcript(response: speech.RecognizeResponse):
    """Prints the transcript from the Google Speech-to-Text API response."""
    # There are two ways to look through the results:
    # Iterate through response.results, looking at the first (highest confidence) alternative and getting its transcript.
    # Or, look at the first alternative of the last result, and iterate its "words", which should have all the words from the audio.
    # Each of the words has fields "word", "confidence", "speaker_tag" and "speaker_label" (as well as timing info)
    confidences = []
    print("Transcript:")
    for result in response.results:
       confidences.append(result.alternatives[0].confidence)
       print(result.alternatives[0].transcript)

    print("Words with speaker tags:")
    for word in response.results[-1].alternatives[0].words:
        print(f"{word.word}({word.speaker_label})")

    print(f"Confidence range: {min(confidences)} - {max(confidences)}, average: {sum(confidences)/len(confidences)}")


#### Main ####

# Create a temp file for the FLAC audio
with tempfile.NamedTemporaryFile(suffix=".flac", delete=True) as temp_flac_file:

    flac_file = convert_to_flac(audio_file_path, temp_flac_file)
    try:
        cloud_url = upload_file_to_bucket(flac_file)
        response = transcribe_url(cloud_url)
        print_transcript(response)
    finally:
       remove_file_from_bucket(cloud_url)

