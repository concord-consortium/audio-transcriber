## this is just a quick and dirty script to make an mp4 file into audio (m4a)
## python audio.py
## first install moviepy
## ``` pip3 install moviepy ````
## to run python3 audio.py

import os
import sys
import tempfile
import hashlib
from pathlib import Path
from moviepy.editor import AudioFileClip
from pydub import AudioSegment

# Security constants
MAX_FILE_SIZE_MB = 500  # Maximum file size in MB
ALLOWED_INPUT_FORMATS = {'.mp4', '.avi', '.mov', '.mkv'}
ALLOWED_OUTPUT_FORMATS = {'.m4a', '.mp3', '.wav'}
MAX_AUDIO_DURATION_HOURS = 24  # Maximum audio duration in hours
TEMP_DIR = None  # Will be set to a secure temporary directory

def setup_secure_environment():
    """Set up a secure environment for processing files."""
    global TEMP_DIR
    
    # Create a secure temporary directory with restricted permissions
    TEMP_DIR = tempfile.mkdtemp(prefix="audio_converter_")
    os.chmod(TEMP_DIR, 0o700)  # Only owner can read/write/execute
    
    # Set secure umask for file creation
    os.umask(0o077)  # Only owner can read/write
    
    return TEMP_DIR

def validate_file_path(file_path, is_input=True):
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
        allowed_formats = ALLOWED_INPUT_FORMATS if is_input else ALLOWED_OUTPUT_FORMATS
        if path.suffix.lower() not in allowed_formats:
            raise ValueError(f"Unsupported file format. Allowed formats: {', '.join(allowed_formats)}")
        
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
        sys.exit(1)

def convert_mp4_to_m4a(input_file, output_file):
    """Convert MP4 to M4A with security checks."""
    try:
        # Set up secure environment
        setup_secure_environment()
        
        # Validate input file
        safe_input_path = validate_file_path(input_file, is_input=True)
        
        # Create output path safely
        output_path = Path(output_file)
        output_dir = output_path.parent
        
        # Ensure output directory is writable
        if not os.access(output_dir, os.W_OK):
            raise PermissionError(f"No write permission in directory: {output_dir}")
        
        # Step 1: Extract audio as a temporary WAV file using moviepy
        temp_wav = os.path.join(TEMP_DIR, "temp_audio.wav")
        video = AudioFileClip(safe_input_path)
        
        # Check audio duration
        duration_hours = video.duration / (60 * 60)  # Convert seconds to hours
        if duration_hours > MAX_AUDIO_DURATION_HOURS:
            raise ValueError(f"Audio duration too long. Maximum duration is {MAX_AUDIO_DURATION_HOURS} hours")
        
        video.write_audiofile(temp_wav, codec='pcm_s16le')
        video.close()
        
        # Set secure permissions on temporary WAV file
        os.chmod(temp_wav, 0o600)
        
        # Step 2: Convert the WAV file to mono and save as MP4 using pydub
        audio = AudioSegment.from_wav(temp_wav)
        mono_audio = audio.set_channels(1)
        output_file_mp4 = output_file.replace('.m4a', '.mp4')
        mono_audio.export(output_file_mp4, format="mp4", codec="aac")
        
        # Set secure permissions on output file
        os.chmod(output_file_mp4, 0o600)
        
        print(f"Conversion completed! Saved as {output_file_mp4}")
    except Exception as e:
        sys.stderr.write(f"Error converting file: {str(e)}\n")
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

# Example usage
if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.stderr.write("Usage: python audio.py <input_file> <output_file>\n")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    convert_mp4_to_m4a(input_file, output_file)