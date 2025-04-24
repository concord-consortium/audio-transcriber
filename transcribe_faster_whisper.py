#!/usr/bin/env python3

# See README for prerequisites and setup instructions.

import os
import sys
import tempfile
import csv
import numpy as np
from pydub import AudioSegment
from faster_whisper import WhisperModel
from scipy.io import wavfile
from scipy.cluster.vq import kmeans, vq
from scipy.signal import spectrogram

def usage():
    sys.stderr.write("Usage: " + sys.argv[0] + " audio_file_path\n")
    exit(1)

def convert_to_wav(audio_file_path, temp_wav_file):
    """Converts an audio file to WAV format."""
    wav_file_path = temp_wav_file.name
    sys.stderr.write(f"Converting audio to WAV...\n")
    audio = AudioSegment.from_file(audio_file_path)
    audio.export(wav_file_path, format="wav")
    return temp_wav_file

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
    
    # Open CSV file for writing
    with open(output_csv_path, 'w', newline='') as csvfile:
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
    """Process a specific audio file"""
    try:
        with open(audio_file_path, "rb") as f:
            pass
    except IOError:
        sys.stderr.write("Error: File " + audio_file_path + " not accessible.\n")
        usage()

    output_csv_path = os.path.splitext(audio_file_path)[0] + '.csv'

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_wav_file:
        wav_file = convert_to_wav(audio_file_path, temp_wav_file)
        transcribe_audio(wav_file.name, output_csv_path)

    sys.stderr.write(f"\nTranscript saved to: {output_csv_path}\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        usage()
    process_file(sys.argv[1])

