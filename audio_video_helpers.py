import logging
import os
from moviepy.editor import VideoFileClip, AudioFileClip
from pydub import AudioSegment
from pytube import YouTube

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_file_duration(file_path):
    """
    Gets the duration of the given audio or video file.

    :param file_path: Path to the audio or video file.
    :return: Duration of the file in seconds.
    """
    try:
        # Check the file extension to determine if it's audio or video
        if any(file_path.endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.flac']):
            # Handle audio file
            audio_clip = AudioFileClip(file_path)
            duration = audio_clip.duration
            audio_clip.close()
        elif any(file_path.endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv']):
            # Handle video file
            video_clip = VideoFileClip(file_path)
            duration = video_clip.duration
            video_clip.close()
        else:
            raise ValueError("Unsupported file format")

        return duration
    except Exception as e:
        # Handle errors: log them or re-raise them
        logging.error(f"Error getting duration of file {file_path}: {e}")
        raise
    
#Get file metadata to determine size and duration
def get_file_metadata(file_path):
    logging.info(f"Getting metadata for file: {file_path}")
    file_size = os.path.getsize(file_path)
    duration = None
    if file_path.endswith('.mp3') or file_path.endswith('.wav'):
        audio = AudioFileClip(file_path)
        duration = audio.duration
    elif file_path.endswith('.mp4'):
        video = VideoFileClip(file_path)
        duration = video.duration

    return {
        'size': file_size,  # size in bytes
        'duration': duration  # duration in seconds
    }

def download_youtube_video(url, output_path='uploads/youtube_videos'):
    try:
        # Ensure the output directory exists
        os.makedirs(output_path, exist_ok=True)
        
        # Create a YouTube object with the URL
        yt = YouTube(url)
        
        # Get the highest resolution stream available
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if video_stream:
            # Construct the output file path
            output_file_path = os.path.join(output_path, video_stream.default_filename)
            
            # Download the video
            video_stream.download(output_path=output_path)
            print(f"Downloaded '{video_stream.default_filename}' to '{output_path}'")
            
            return output_file_path
        else:
            print("No suitable video stream found.")
            return None
    except Exception as e:
        print(f"An error occurred while downloading the video: {e}")
        return None
    

# Extract audio from video files 
def extract_audio_from_video(video_file_path, output_audio_path):
    logging.info(f"Extracting audio from video file: {video_file_path}")
    try:
        video = VideoFileClip(video_file_path)
        video.audio.write_audiofile(output_audio_path)
        logging.info(f"Audio extracted to {output_audio_path}")
        return output_audio_path
    except Exception as e:
        logging.error(f"Error occurred while extracting audio: {e}")
        return None

# Process audio/video files
def process_audio_video_file(file_path, filename):
    logging.info(f"Processing file: {filename}")
    
    # Get file metadata to determine size and duration
    metadata = get_file_metadata(file_path)
    file_size = metadata['size']

    # Initialize a variable to store the path of the file to be transcribed
    file_to_transcribe = file_path

    # Convert video files to audio before further processing
    if filename.endswith('.mp4'):
        logging.info(f"Converting video file to audio: {filename}")
        audio_path = extract_audio_from_video(file_path, f"{file_path}_audio.mp3")
        file_to_transcribe = audio_path

    # Split the file if it's larger than 25 MB
    if file_size > 26214400 :
        logging.info(f"File size exceeds limit. Splitting file: {filename}")
        split_file_paths = split_large_avfile(file_to_transcribe)
        logging.info(f"File split into {len(split_file_paths)} parts")
        return split_file_paths

    # If file size is within the limit, return the single file path
    return [file_to_transcribe]

# Split large audio-vido files into smaller parts 
def split_large_avfile(file_path, max_size=24.5*1024*1024):  # max_size in bytes
    file_size = os.path.getsize(file_path)
    if file_size <= max_size:
        logging.info(f"No need to split file: {file_path}")
        return [file_path]  # No need to split

    logging.info(f"Splitting file: {file_path}")
    parts = []
    audio = AudioSegment.from_file(file_path)
    duration = len(audio)
    part_duration = duration * (max_size / file_size)
    
    start = 0
    part_num = 1
    while start < duration:
        end = min(start + part_duration, duration)
        part = audio[start:end]
        part_file_path = f"{file_path}_part{part_num}.mp3"
        part.export(part_file_path, format="mp3")
        parts.append(part_file_path)
        start = end
        part_num += 1
        logging.info(f"Created part {part_num} for file: {file_path}")

    return parts

