#!/usr/bin/env python3

# See README for prerequisites and setup instructions.

# TODO: try API v2 or other models; see which has the best results.

import os
import sys
import tempfile
import hashlib
from pathlib import Path
from pydub import AudioSegment
from urllib.parse import urlparse
from google.cloud import speech
from google.cloud import storage

# Security constants
MAX_FILE_SIZE_MB = 500  # Maximum file size in MB
ALLOWED_AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac', '.flac'}
MAX_AUDIO_DURATION_HOURS = 24  # Maximum audio duration in hours
TEMP_DIR = None  # Will be set to a secure temporary directory

bucket_name = "concord_consortium_audio_transcriber"
storage_client = storage.Client()


def usage():
  sys.stderr.write("Usage: " + sys.argv[0] + " <audio_file_path>\n")
  exit(1)

def setup_secure_environment():
    """Set up a secure environment for processing files."""
    global TEMP_DIR
    
    # Create a secure temporary directory with restricted permissions
    TEMP_DIR = tempfile.mkdtemp(prefix="audio_transcriber_")
    os.chmod(TEMP_DIR, 0o700)  # Only owner can read/write/execute
    
    # Set secure umask for file creation
    os.umask(0o077)  # Only owner can read/write
    
    return TEMP_DIR

def validate_file_path(file_path):
    """Validates the input file path for security."""
    try:
        # Resolve the path to prevent path traversal attacks
        path = Path(file_path).resolve()
        
        # Check if the path exists and is a file
        if not path.exists():
            raise ValueError(f"File does not exist: {file_path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        # Check file extension
        if path.suffix.lower() not in ALLOWED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported file format. Allowed formats: {', '.join(ALLOWED_AUDIO_FORMATS)}")
        
        # Check file size
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE_MB}MB")
        
        # Generate a secure filename to prevent path traversal
        secure_filename = hashlib.sha256(str(path).encode()).hexdigest()[:16] + path.suffix
        secure_path = Path(TEMP_DIR) / secure_filename
        
        # Copy the file to the secure location
        with open(path, 'rb') as src, open(secure_path, 'wb') as dst:
            dst.write(src.read())
        
        # Set secure permissions on the copied file
        os.chmod(secure_path, 0o600)  # Only owner can read/write
        
        return str(secure_path)
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        usage()

# Read command-line arguments:
if (sys.argv.__len__() != 2):
  usage()

audio_file_path = sys.argv[1]

#### Google API methods ####

def convert_to_flac(audio_file_path, temp_flac_file):
    """Converts an audio file to FLAC format with security checks."""
    flac_file_path = temp_flac_file.name
    sys.stderr.write(f"Converting audio to FLAC...\n")
    
    try:
        audio = AudioSegment.from_file(audio_file_path)
        
        # Check audio duration
        duration_hours = len(audio) / (1000 * 60 * 60)  # Convert milliseconds to hours
        if duration_hours > MAX_AUDIO_DURATION_HOURS:
            raise ValueError(f"Audio duration too long. Maximum duration is {MAX_AUDIO_DURATION_HOURS} hours")
        
        # Set secure permissions on temporary file
        temp_flac_file.chmod(0o600)
        audio.export(flac_file_path, format="flac")
        return temp_flac_file
    except Exception as e:
        sys.stderr.write(f"Error converting audio: {str(e)}\n")
        raise


def upload_file_to_bucket(file) -> str:
    """Uploads a file to the Google Cloud Storage bucket, returns URL"""
    filename = os.path.basename(file.name)
    print(f"Uploading to Google Cloud...")
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
        enable_automatic_punctuation=True,
        language_code="en-US",
        diarization_config=speaker_diarization_config,
    )
    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=1800)  # Allow up to 30 minutes
    return response


def format_duration(seconds):
    """Formats a duration in seconds into HH:MM:SS format."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{seconds:06.3f}"


def print_transcript_line(time, speaker, text):
    """Prints a line of the transcript with the time, speaker, and text."""
    if text != "":
        print(f"{format_duration(time)};{speaker};{text}")

def print_transcript(response: speech.RecognizeResponse):
    """Prints the transcript from the Google Speech-to-Text API response."""
    # To just get the text from a RecognizeResponse, you can iterate through
    # response.results, looking at the first (highest confidence) alternative
    # and getting its transcript. 
    # 
    # However, the speaker identification is only shown in the final response,
    # so we have to look at the first alternative of the last result, and
    # iterate its "words", which should have all the words from the audio. 
    # 
    # Each of the words has fields "word", "speaker_tag" and "speaker_label"
    # (which are essentially the same), "start_time" and "end_time".

    # Header row
    print("Time;Speaker;Text")

    current_time = None
    current_speaker = None
    current_text = ""
    for word in response.results[-1].alternatives[0].words:
        if word.speaker_label != current_speaker:
            # New speaker identified; start a new line of output
            print_transcript_line(current_time, current_speaker, current_text)
            current_text = ""
            current_time = word.start_time.seconds
            current_speaker = word.speaker_label
        current_text += word.word + " "
    # print the last line
    print_transcript_line(current_time, current_speaker, current_text)


#### Main ####

try:
    # Set up secure environment
    setup_secure_environment()
    
    # Validate and sanitize input path
    safe_path = validate_file_path(audio_file_path)
    
    # Create a temp file for the FLAC audio
    with tempfile.NamedTemporaryFile(suffix=".flac", delete=True, dir=TEMP_DIR) as temp_flac_file:
        flac_file = convert_to_flac(safe_path, temp_flac_file)
        try:
            cloud_url = upload_file_to_bucket(flac_file)
            response = transcribe_url(cloud_url)
            print_transcript(response)
        finally:
           remove_file_from_bucket(cloud_url)
except Exception as e:
    sys.stderr.write(f"Error processing file: {str(e)}\n")
    sys.exit(1)
finally:
    # Clean up temporary files
    if TEMP_DIR and os.path.exists(TEMP_DIR):
        for file in os.listdir(TEMP_DIR):
            try:
                os.remove(os.path.join(TEMP_DIR, file))
            except:
                pass
        try:
            os.rmdir(TEMP_DIR)
        except:
            pass

