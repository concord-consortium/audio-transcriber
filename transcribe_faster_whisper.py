#!/usr/bin/env python3

# See README for prerequisites and setup instructions.

# TODO: speaker diarization model to get speaker labels.

import os
import sys
import tempfile
import csv
from pydub import AudioSegment
from faster_whisper import WhisperModel

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

def print_transcript_line(time, text, csv_writer=None):
    """Prints a line of the transcript with the time and text."""
    if text != "":
        line = f"{format_duration(time)};{text}"
        print(line)
        if csv_writer:
            csv_writer.writerow([format_duration(time), text])

def transcribe_audio(audio_path, output_csv_path):
    """Transcribes audio using FasterWhisper."""
    sys.stderr.write(f"Loading FasterWhisper model...\n")
    model = WhisperModel("large-v2", device="cpu", compute_type="int8")
    
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
    print("Time;Text")
    
    # Open CSV file for writing
    with open(output_csv_path, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Time', 'Text'])

        # Process segments
        for segment in segments:
            start_time = segment.start
            
            current_text = ""
            for word in segment.words:
                if current_text:
                    current_text += " "
                current_text += word.word
                
            if current_text.strip():
                print_transcript_line(start_time, current_text.strip(), csv_writer)

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

