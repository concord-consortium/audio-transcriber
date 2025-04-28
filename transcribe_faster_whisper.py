#!/usr/bin/env python3

# See README for prerequisites and setup instructions.

import os
import sys
import tempfile
import csv
import numpy as np
import hashlib
import secrets
from pathlib import Path
from pydub import AudioSegment
from faster_whisper import WhisperModel
from scipy.io import wavfile
from scipy.cluster.vq import kmeans, vq
from scipy.signal import spectrogram

# Security constants
MAX_FILE_SIZE_MB = 500  # Maximum file size in MB
ALLOWED_AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.ogg', '.flac'}
MAX_AUDIO_DURATION_HOURS = 24  # Maximum audio duration in hours
TEMP_DIR = None  # Will be set to a secure temporary directory

def usage():
    sys.stderr.write("Usage: " + sys.argv[0] + " audio_file_path\n")
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

def convert_to_wav(audio_file_path, temp_wav_file):
    """Converts an audio file to WAV format with security checks."""
    wav_file_path = temp_wav_file.name
    sys.stderr.write(f"Converting audio to WAV...\n")
    
    try:
        audio = AudioSegment.from_file(audio_file_path)
        
        # Check audio duration
        duration_hours = len(audio) / (1000 * 60 * 60)  # Convert milliseconds to hours
        if duration_hours > MAX_AUDIO_DURATION_HOURS:
            raise ValueError(f"Audio duration too long. Maximum duration is {MAX_AUDIO_DURATION_HOURS} hours")
        
        # Set secure permissions on temporary file
        os.chmod(temp_wav_file.name, 0o600)
        audio.export(wav_file_path, format="wav")
        return temp_wav_file
    except Exception as e:
        sys.stderr.write(f"Error converting audio: {str(e)}\n")
        raise

def format_duration(seconds):
    """Formats a duration in seconds into HH:MM:SS format."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours):02}:{int(minutes):02}:{seconds:06.3f}"

def extract_audio_features(audio_path, window_size=0.5):
    """Extract audio features for speaker diarization."""
    sys.stderr.write(f"Extracting audio features...\n")
    sample_rate, audio_data = wavfile.read(audio_path)
    
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Calculate spectrogram
    _, _, Sxx = spectrogram(audio_data, fs=sample_rate, nperseg=int(window_size * sample_rate))
    
    # Calculate features (mean and std of frequency bands)
    features = []
    for i in range(Sxx.shape[1]):
        segment_features = [np.mean(Sxx[:, i]), np.std(Sxx[:, i])]
        features.append(segment_features)
    
    return np.array(features)

def perform_diarization(audio_path, num_speakers=6):
    """Performs basic speaker diarization using clustering."""
    try:
        # Extract features
        features = extract_audio_features(audio_path)
        
        # Perform k-means clustering
        centroids, _ = kmeans(features, num_speakers)
        labels, _ = vq(features, centroids)
        
        # Convert to time segments
        window_size = 0.5  # seconds
        speaker_segments = []
        for i, label in enumerate(labels):
            start_time = i * window_size
            end_time = (i + 1) * window_size
            speaker_segments.append((start_time, end_time, f"{label + 1}"))
        
        return speaker_segments
    except Exception as e:
        sys.stderr.write(f"Warning: Speaker diarization failed: {str(e)}\n")
        return []

def print_transcript_line(time, text, speaker=None, csv_writer=None):
    """Prints a line of the transcript with the time, speaker, and text."""
    if text != "":
        speaker_text = f"Speaker {speaker}" if speaker is not None else "Unknown"
        line = f"{format_duration(time)};{speaker_text};{text}"
        print(line)
        if csv_writer:
            csv_writer.writerow([format_duration(time), speaker_text, text])

def transcribe_audio(audio_path, output_csv_path):
    """Transcribes audio using FasterWhisper and adds speaker diarization."""
    sys.stderr.write(f"Loading FasterWhisper model...\n")
    model = WhisperModel("large-v2", device="cpu", compute_type="int8")
    
    # Perform speaker diarization
    speaker_segments = perform_diarization(audio_path)
    
    sys.stderr.write(f"Transcribing audio...\n")
    # Transcribe with word-level timestamps
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500)
    )

    # Print header
    print("Time;Speaker;Text")
    
    # Open CSV file for writing with secure permissions
    with open(output_csv_path, 'w', newline='') as csvfile:
        # Set secure permissions on the CSV file
        os.chmod(output_csv_path, 0o600)  # Only owner can read/write
        
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Time', 'Speaker', 'Text'])

        # Process segments
        for segment in segments:
            start_time = segment.start
            
            # Find the speaker for this segment if diarization is available
            speaker = None
            if speaker_segments:
                for seg_start, seg_end, seg_speaker in speaker_segments:
                    if start_time >= seg_start and start_time < seg_end:
                        speaker = seg_speaker
                        break
            
            current_text = ""
            for word in segment.words:
                if current_text:
                    current_text += " "
                current_text += word.word
                
            if current_text.strip():
                print_transcript_line(start_time, current_text.strip(), speaker, csv_writer)

def process_file(audio_file_path):
    """Process a specific audio file with security measures."""
    try:
        # Set up secure environment
        setup_secure_environment()
        
        # Validate and sanitize input path
        safe_path = validate_file_path(audio_file_path)
        
        # Create output path safely
        output_path = Path(audio_file_path)
        output_csv_path = str(output_path.with_suffix('.csv'))
        
        # Ensure output directory is writable
        output_dir = output_path.parent
        if not os.access(output_dir, os.W_OK):
            raise PermissionError(f"No write permission in directory: {output_dir}")
        
        # Create temporary file with secure permissions
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True, mode='wb', dir=TEMP_DIR) as temp_wav_file:
            wav_file = convert_to_wav(safe_path, temp_wav_file)
            transcribe_audio(wav_file.name, output_csv_path)
        
        sys.stderr.write(f"\nTranscript saved to: {output_csv_path}\n")
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

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
    process_file(sys.argv[1])

