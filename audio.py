## this is just a quick and dirty script to make an mp4 file into audio (m4a)
## python audio.py
## first install moviepy
## ``` pip3 install moviepy ````
## to run python3 audio.py

from moviepy.editor import AudioFileClip
from pydub import AudioSegment
import os

def convert_mp4_to_m4a(input_file, output_file):
    # Step 1: Extract audio as a temporary WAV file using moviepy
    temp_wav = "temp_audio.wav"
    video = AudioFileClip(input_file)
    video.write_audiofile(temp_wav, codec='pcm_s16le')
    video.close()
    
    # Step 2: Convert the WAV file to mono and save as MP4 using pydub
    audio = AudioSegment.from_wav(temp_wav)
    mono_audio = audio.set_channels(1)
    output_file_mp4 = output_file.replace('.m4a', '.mp4')
    mono_audio.export(output_file_mp4, format="mp4", codec="aac")

    # Step 3: Cleanup the temporary WAV file
    os.remove(temp_wav)

# Replace 'input.mp4' and 'output.m4a' with your file paths
input_file = "GMT20240214-201300_Recording_1792x1096.mp4"
output_file = "GMT20240214-201300_Recording_1792x1096.m4a"

convert_mp4_to_m4a(input_file, output_file)

print(f"Conversion completed! Saved as {output_file.replace('.m4a', '.mp4')}")