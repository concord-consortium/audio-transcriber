## this is just a quick and dirty script to make an mp4 file into audio (m4a)
## python convertaudio.py
## first install pip3 install moviepy
## to run python audio.py

from moviepy.editor import AudioFileClip

def convert_mp4_to_m4a(input_file, output_file):
    # Load the video file
    video = AudioFileClip(input_file)
    
    # Write the audio part to an m4a file
    video.write_audiofile(output_file, codec='aac')
    
    # Close the video file to free up resources
    video.close()

# Replace 'input.mp4' and 'output.m4a' with your file paths
input_file = "input.mp4"
output_file = "output.m4a"

convert_mp4_to_m4a(input_file, output_file)

print(f"Conversion completed! Saved as {output_file}")