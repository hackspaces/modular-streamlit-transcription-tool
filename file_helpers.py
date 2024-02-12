from moviepy.editor import AudioFileClip, VideoFileClip
import logging
import os
import csv
import re
from datetime import datetime
from config_const import UPLOAD_DIRECTORY


# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def ensure_file_exists(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["hash", "filename"])

# Read text file    
def read_text_file(file_path):
    # Check if the file is a .txt file
    if not file_path.endswith('.txt'):
        raise ValueError("Unsupported file format. Expected a .txt file.")

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logging.error(f"Error reading text file {file_path}: {e}")
        raise

def clean_filename(filename):
    """
    Clean the filename to make it safe for file systems.

    :param filename: The original filename.
    :return: A cleaned version of the filename safe for use in file systems.
    """
    # Remove invalid file system characters
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    # Optionally, truncate the filename to a maximum length, e.g., 255 characters
    filename = (filename[:255]) if len(filename) > 255 else filename
    return filename

# Helper function to get file details
def get_file_details(files):
    file_details = []
    for file in files:
        try:
            stat = os.stat(file['path'])
            file_details.append({
                'name': file['name'],
                'path': file['path'],
                'size': stat.st_size,
                'mtime': datetime.fromtimestamp(stat.st_mtime)
            })
        except:
            continue  # If the file was deleted, skip it
    return file_details

def delete_file(file_path):
    """
    Deletes a file from the file system.
    """
    # Delete the file
    os.remove(file_path)

# Helper functions for file handling
def save_uploaded_file(uploaded_file):
    file_path = os.path.join(UPLOAD_DIRECTORY, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def list_files(directory):
    files = []
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            if os.path.isfile(path):
                files.append({"name": filename, "path": path})
    return files

def list_css_files(name, key):
    css_folder_path = os.path.join(UPLOAD_DIRECTORY, f"{name}_{key}", 'css')
    if os.path.exists(css_folder_path):
        return [f for f in os.listdir(css_folder_path) if f.endswith('.css')]
    return []

def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logging.error(f"Error reading file: {e}")
        return None