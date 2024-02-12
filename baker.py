import streamlit as st
import os
from audio_video_helpers import process_audio_video_file, download_youtube_video, get_file_duration, get_file_metadata
from credit_auth_helpers import check_and_deduct_credits, credits_db
from file_helpers import list_files, get_file_details, read_file_content, delete_file, list_css_files, read_text_file
import logging
from config_const import PROCESSED_DIRECTORY, UPLOAD_DIRECTORY
from werkzeug.utils import secure_filename
from file_helpers import ensure_directory_exists, ensure_file_exists
from file_hash_helpers import calculate_file_hash, write_hash_to_csv, read_hashes_from_csv, delete_hash_from_csv
import shutil
from api_helpers import call_whisper_api, reformat_transcript_with_gpt4
from werkzeug.utils import secure_filename
from html_creator_helper import convert_txt_to_html, clean_title
import streamlit.components.v1 as components 
import re

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define directories for uploads and processed files
UPLOAD_DIRECTORY = "uploaded_files"
PROCESSED_DIRECTORY = "processed_files"
TRANSCRIPT_DIRECTORY= "pr"
download_folder = os.path.join(UPLOAD_DIRECTORY, "youtube_videos")
ensure_directory_exists(UPLOAD_DIRECTORY)
ensure_directory_exists(PROCESSED_DIRECTORY)
ensure_file_exists("file_hashes.csv")
ensure_directory_exists(download_folder)

def clean_vtt_content(vtt_content):
    # Split the content into lines
    lines = vtt_content.splitlines()
    # Patterns to detect timestamps and potentially unwanted lines
    timestamp_pattern = re.compile(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}')
    non_textual_pattern = re.compile(r'^\d+$|^WEBVTT|^NOTE|^STYLE|^X-|^\s*$')
    
    cleaned_lines = []
    for line in lines:
        # Skip lines matching the patterns for timestamps, "WEBVTT", empty lines, and other non-textual content
        if timestamp_pattern.match(line) or non_textual_pattern.match(line):
            continue
        # Add non-empty lines to the cleaned_lines list
        if line.strip():
            cleaned_lines.append(line.strip())

    return '\n'.join(cleaned_lines)


# Function to extract text from .vtt file and save as .txt
def extract_text_from_vtt(vtt_file_path, output_text_file_path):
    with open(vtt_file_path, 'r', encoding='utf-8') as vtt_file:
        vtt_content = vtt_file.read()  # Read the entire content at once

    cleaned_content = clean_vtt_content(vtt_content)  # Clean the content using the previously defined function

    with open(output_text_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(cleaned_content)  # Write the cleaned content to the output file


#If the file to process is just a .txt file and needs to be converted to .html
def format_text_file(file_path, format_with_gpt, openai_api_key, css_file_path, name, key):
    # Construct the path for the processed folder based on name and key
    user_processed_folder = os.path.join(PROCESSED_DIRECTORY, f"{name}_{key}", "html")
    ensure_directory_exists(user_processed_folder)

    # Extract the base file name and construct the paths for formatted text and HTML files
    base_file_name = os.path.splitext(os.path.basename(file_path))[0]
    formatted_file_path = os.path.join(user_processed_folder, base_file_name + "_formatted.txt")
    html_file_path = os.path.join(user_processed_folder, base_file_name + ".html")
    
    # Check if the file is a .vtt file
    if file_path.endswith('.vtt'):
        # Extract text from .vtt to a temporary .txt file
        temp_text_file_path = os.path.join(user_processed_folder, base_file_name + ".txt")
        extract_text_from_vtt(file_path, temp_text_file_path)
        file_path = temp_text_file_path  # Update file_path to the extracted text file

    # Process the file
    if format_with_gpt:
        st.toast("Formatting with GPT-4", icon="⏳")
        formatted_text = reformat_transcript_with_gpt4(read_text_file(file_path), openai_api_key)
        with open(formatted_file_path, "w") as text_file:
            text_file.write(formatted_text)
        convert_txt_to_html(formatted_file_path, html_file_path, base_file_name, css_file_path)
    else:
        convert_txt_to_html(file_path, html_file_path, base_file_name, css_file_path)
        
    return html_file_path

# Transcribe and format audio/video files with Whisper AI and GPT-4 does not convert to .html
def transcribe_and_save(file_paths, openai_api_key):
    logging.debug(f"Transcribing file: {file_paths}")
    combined_transcription = ''
    for part_path in file_paths:
        print(f"Transcribing file: {part_path}")
        transcription = call_whisper_api(part_path, openai_api_key)
        print(f"Transcription: {transcription}")
        if transcription:
            combined_transcription += transcription + "\n"  # Add a new line between parts
        else:
            logging.error(f"Failed to transcribe file part: {part_path}")
            return None  # Or handle the error as appropriate
    combined_transcription_filename = os.path.splitext(file_paths[0])[0] + "_combined.txt"  # Assuming file_paths[0] is the base name
    with open(combined_transcription_filename, "w") as text_file:
        text_file.write(combined_transcription)
        
    if combined_transcription:
        formatted_transcription = reformat_transcript_with_gpt4(combined_transcription, openai_api_key)
        output_filename = os.path.splitext(file_paths[0])[0] + "_formatted.txt"
            
        with open(output_filename, "w") as text_file:
            text_file.write(formatted_transcription)
                
        return output_filename
            
    return None

# Process Audio/Video Files in streamlit component
def process_audio_video_files(file_path, name, key, css_file_path, openai_api_key):
    logging.info(f"Processing file: {os.path.basename(file_path)}")
    # Extract the filename from the path
    filename = os.path.basename(file_path)
    # Process the file - convert video to audio, split if necessary
    file_paths_to_process = process_audio_video_file(file_path, filename)
    
    # Transcribe and format the audio files
    transcription_filename = transcribe_and_save(file_paths_to_process, openai_api_key)
    
    if transcription_filename:
        # Save the formatted transcription in the user-specific processed folder
        user_processed_folder = os.path.join(PROCESSED_DIRECTORY, f"{name}_{key}", 'transcripts')
        ensure_directory_exists(user_processed_folder)

        # Construct the full path for the processed file
        processed_file_path = os.path.join(user_processed_folder, os.path.basename(transcription_filename))
        
        # Move or copy the file to the user-specific processed folder
        shutil.move(transcription_filename, processed_file_path)

        logging.info(f"Processed file saved: {processed_file_path}")
        # Convert the transcript to HTML and save in the same folder
        title = os.path.splitext(filename)[0]
        html_file_path = os.path.join(user_processed_folder, title + ".html")
        convert_txt_to_html(processed_file_path, html_file_path, title, css_file_path)
        logging.info(f"HTML file created: {html_file_path}")

        return html_file_path
    else:
        logging.error(f"Failed to process file: {os.path.basename(file_path)}")
        return None


# Modify the handle_file_upload function to organize files into directories
def handle_file_upload(uploaded_file, name="jhondoe_asu", key="jhondoekey_asu"):
    # Secure the filename and construct the full path
    filename = secure_filename(uploaded_file.name)
    # Check for duplicates and save the file
    temp_file = uploaded_file.read()
    file_hash = calculate_file_hash(temp_file)
    
    # Create user-specific folder based on name and key
    user_folder_name = f"{name}_{key}"
    user_upload_folder = os.path.join(UPLOAD_DIRECTORY, user_folder_name)
    
    # Create subfolder for file type
    file_extension = uploaded_file.name.rsplit('.', 1)[-1].lower()
    file_type_folder = os.path.join(user_upload_folder, file_extension)
    ensure_directory_exists(file_type_folder)
    
    if file_hash in read_hashes_from_csv():
        logging.info(f"Duplicate file detected, skipped: {filename}")
        st.toast(f"Duplicate file detected, skipped: {filename}", icon="❌")
        return None  # Return None to indicate no further action is needed
    else:
        file_path = os.path.join(file_type_folder, filename)
        with open(file_path, 'wb') as f:
            f.write(temp_file)
        write_hash_to_csv(file_hash, filename)
        return file_path


# Process Text Files
def process_text_file(file_path, format_with_gpt, css_file_path, name, key, openai_api_key):
    """
    Process the text file.

    :param file_path: Path to the text file to be processed.
    :param format_with_gpt: Boolean indicating whether to format with GPT-4.
    :return: Path to the processed HTML file.
    """
    # Call the format_text_file function to process and convert the text file
    processed_html_file_path = format_text_file(
        file_path=file_path,
        format_with_gpt=format_with_gpt,
        openai_api_key=openai_api_key,
        css_file_path=css_file_path,
        name=name,
        key=key)

    return processed_html_file_path

def process_youtube_video(youtube_url, name, key, css_file_path, openai_api_key):
    file_path = download_youtube_video(youtube_url, download_folder)
    filename = os.path.basename(file_path)
    # Download the youtube video
    # Extract audio from the video
    file_paths_to_process = process_audio_video_file(file_path, filename)
    
    # Transcribe and format the audio files
    transcription_filename = transcribe_and_save(file_paths_to_process, openai_api_key)
    
    if transcription_filename:
        # Save the formatted transcription in the user-specific processed folder
        user_processed_folder = os.path.join(PROCESSED_DIRECTORY, f"{name}_{key}", 'html')
        ensure_directory_exists(user_processed_folder)

        # Construct the full path for the processed file
        processed_file_path = os.path.join(user_processed_folder, os.path.basename(transcription_filename))
        
        # Move or copy the file to the user-specific processed folder
        shutil.move(transcription_filename, processed_file_path)
        
        logging.info(f"Processed file saved: {processed_file_path}")
        # Convert the transcript to HTML and save in the same folder
        title = os.path.splitext(filename)[0]
        html_file_path = os.path.join(user_processed_folder, title + ".html")
        convert_txt_to_html(processed_file_path, html_file_path, title, css_file_path)
        logging.info(f"HTML file created: {html_file_path}")

        return html_file_path
    else:
        logging.error(f"Failed to process file: {os.path.basename(file_path)}")
        return None
    
    return None


def transcription_functionality(name, key, credit_on, openai_api_key):
    css_file_path = None
    selected_css_option = None
    # File Upload Section with improved spacing and layout
    with st.container():
            with st.expander("Step 2: File Upload", expanded=True):
                col1, col2= st.columns([1, 1])
                
                with col1:
                    st.write("Upload text, audio, or video files to process.")
                    uploaded_files = st.file_uploader("Drag and drop files here", accept_multiple_files=True, type=['txt', 'mp3', 'mp4', 'vtt'], help="Limit 200MB per file")
                    format_with_gpt = st.checkbox("Format with GPT-4", value=False, help="Format the transcript with GPT-4 to improve readability.")
                with col2:
                    st.write("Process a youtube video.")
                    youtube_url = st.text_input("Enter the youtube url")
                    if st.button("Process Youtube Video", key="process_youtube_video"):
                        css_file_path = "https://assets.ea.asu.edu/ulc/css/stylesheet.css"
                        process_youtube_video(youtube_url, name, key, css_file_path, openai_api_key)
                        st.toast(f"Finished processing youtube video: {youtube_url}", icon="🎉")
                    else:
                        st.error("No youtube url entered.")

            with st.expander("Upload CSS File", expanded=False):
                st.write("Select a CSS file to apply to the transcript.")
                uploaded_css_file = st.file_uploader("Drag and drop CSS file here", accept_multiple_files=False, type=['css'], help="Limit 200MB per file")
                css_files = list_css_files(name, key)
                css_options = ["None"] + css_files
                selected_css_option = st.selectbox("Select a CSS file", css_options, index=0, help="Select a CSS file to apply to the transcript.")  
    
    if st.button("Process Files", key="process_files"):
        with st.status("Processing files..."):
            # Handle CSS file upload and path retrieval
            if uploaded_css_file:
                css_file_path = handle_file_upload(uploaded_css_file, name, key)
                print(css_file_path)
                st.toast(f"CSS file uploaded: {css_file_path}")
            elif selected_css_option != "None":
                css_file_path = os.path.join(UPLOAD_DIRECTORY, f"{name}_{key}", "css", selected_css_option)
                print(css_file_path)
            elif css_file_path is not None and os.path.exists(css_file_path):
                css_file_path = os.path.join(UPLOAD_DIRECTORY, f"{name}_{key}", "css", "default.css")
                print(css_file_path)
            else:
                css_file_path = "https://assets.ea.asu.edu/ulc/css/stylesheet.css"
                
            if not uploaded_files:
                st.error("No files selected.")
            else:
                for uploaded_file in uploaded_files:
                    if credit_on:
                        file_duration = get_file_duration(file_path)
                        # Check and potentially deduct credits
                        credits_ok, message = check_and_deduct_credits(name, key, file_duration)
                        if credits_ok:
                            # If credits check out, process the file
                            st.success("Credits processed successfully")
                        else:
                            # If there is an issue with credits, display an error
                            st.error(message)
                    print(uploaded_file.name)
                    st.write(f"Uploading file: {uploaded_file.name}")
                    file_path = handle_file_upload(uploaded_file, name=name, key=key)
                    print(file_path)
                    
                    audio_video_extensions = ['.mp3', '.mp4', '.wav', '.avi', '.mov', '.flac']
                    extension = os.path.splitext(file_path)[1]
                
                    if extension == ".txt" and file_path is not None:
                        st.write(f"Processing text file: {file_path}")
                        process_text_file(file_path, format_with_gpt, css_file_path=css_file_path, name=name, key=key, openai_api_key=openai_api_key)
                    elif extension == ".vtt" and file_path is not None:
                        st.write(f"Processing vtt file: {file_path}")
                        process_text_file(file_path, format_with_gpt, css_file_path=css_file_path, name=name, key=key, openai_api_key=openai_api_key)
                        st.write(f"Finished processing text file: {file_path}")
                    elif extension in audio_video_extensions and file_path is not None:
                        st.write(f"Processing audio/video file: {file_path}")
                        process_audio_video_files(file_path, name=name, key=key, css_file_path=css_file_path, openai_api_key=openai_api_key)
                        st.write(f"Finished processing audio/video file: {file_path}")
                        
def file_management(page, name, key):
    # File Management Section with search and sort, without using a table
    if page == "Current Functionality":
        with st.container():
            user_processed_folder = os.path.join(PROCESSED_DIRECTORY, f"{name}_{key}", 'html')
            print(user_processed_folder)
            user_uploaded_folder = os.path.join(UPLOAD_DIRECTORY, f"{name}_{key}")
            files = get_file_details(list_files(user_processed_folder))
            uploaded_files = get_file_details(list_files(user_uploaded_folder))
            col1, col2, col3 = st.columns([3, 4, 3])
            with col1:
                st.header("File Management")
            with col2:
                # Enhanced real-time search functionality
                search_query = st.text_input("Search files")
                if search_query:
                    files = [file for file in files if search_query.lower() in file['name'].lower()]
            with col3:
                # Sort options
                sort_option = st.selectbox("Sort by", ["Name", "Date Modified", "Size"], index=0)

            # Sort files based on the selected option
            if sort_option == "Name":
                files.sort(key=lambda x: x['name'].lower())
            elif sort_option == "Date Modified":
                files.sort(key=lambda x: x['mtime'], reverse=True)
            elif sort_option == "Size":
                files.sort(key=lambda x: x['size'], reverse=True)

            # Create table headers with some styling
            header1, header2, header3, header4 = st.columns([3, 3, 1, 1])
            header1.markdown("**Name of the File**", unsafe_allow_html=True)
            header2.markdown("**Title**", unsafe_allow_html=True)
            header3.markdown("**Download**", unsafe_allow_html=True)
            header4.markdown("**Delete**", unsafe_allow_html=True)

            # Alternate row color for better readability
            bg_color = "#f0f2f6"
            
            for file in uploaded_files:
                file_name = file['name']
                file_title = clean_title(file_name)

                # Apply alternate row color
                bg_color = "#e0e2f6" if bg_color == "#f0f2f6" else "#f0f2f6"
                with st.container():
                    st.markdown(f'<div style="background-color: {bg_color}; padding: 5px;">', unsafe_allow_html=True)
                    col1, col2, col3, col4 = st.columns([3, 3, 1, 1])

                    with col1:
                        st.text(file_name)
                    with col2:
                        st.text(file_title)

                    with col3:
                        # Download button
                        with open(file['path'], 'rb') as f:
                            st.download_button("⬇️", f.read(), file_name=file_name, mime="text/plain", key=f"download_{file_name}")

                    with col4:
                        # Delete button
                        if st.button("❌", key=f"delete_{file_name}"):
                            delete_file(file['path'])
                            delete_hash_from_csv()
                            st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)

            for file in files:
                file_name = file['name']
                file_title = clean_title(os.path.splitext(file_name)[0])

                # Apply alternate row color
                bg_color = "#e0e2f6" if bg_color == "#f0f2f6" else "#f0f2f6"
                with st.container():
                    st.markdown(f'<div style="background-color: {bg_color}; padding: 5px;">', unsafe_allow_html=True)
                    col1, col2, col3, col4 = st.columns([3, 3, 1, 1])

                    with col1:
                        st.text(file_name)
                    with col2:
                        st.text(file_title)

                    with col3:
                        # Download button
                        with open(file['path'], 'rb') as f:
                            st.download_button("⬇️", f.read(), file_name=file_name, mime="text/plain", key=f"download_{file_name}")

                    with col4:
                        # Delete button
                        if st.button("❌", key=f"delete_{file_name}"):
                            delete_file(file['path'])
                            delete_hash_from_csv()
                            st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)
                    
    elif page == "File Preview":
        with st.container():
            user_processed_folder = os.path.join(PROCESSED_DIRECTORY, f"{name}_{key}", 'html')
            files = get_file_details(list_files(user_processed_folder))
            col1, col2 = st.columns([3, 4])
            with col1:
                # Enhanced real-time search functionality
                search_query = st.text_input("Search files")
                if search_query:
                    files = [file for file in files if search_query.lower() in file['name'].lower()]
            with col2:
                # Sort options
                sort_option = st.selectbox("Sort by", ["Name", "Date Modified", "Size"], index=0)

            # Sort files based on the selected option
            if sort_option == "Name":
                files.sort(key=lambda x: x['name'].lower())
            elif sort_option == "Date Modified":
                files.sort(key=lambda x: x['mtime'], reverse=True)
            elif sort_option == "Size":
                files.sort(key=lambda x: x['size'], reverse=True)

            
            if 'previewed_file' not in st.session_state:
                st.session_state.previewed_file = None
            if 'file_content_to_preview' not in st.session_state:
                st.session_state.file_content_to_preview = None

            # Display the table with clickable file names
        for i, file in enumerate(files):
            file_name = file['name']
            file_title = clean_title(os.path.splitext(file_name)[0])
            # Each file name is a button that updates the session state for preview
            if st.button(file_title, key=f"preview_{i}"):
                st.session_state['previewed_file'] = file_name
                st.session_state['file_content_to_preview'] = read_file_content(file['path'])
        
         # Show the preview if a file name has been clicked
        if st.session_state['previewed_file']:
            st.markdown(f"## Preview of {st.session_state['previewed_file']}")
            components.html(st.session_state['file_content_to_preview'] , height=800, scrolling=True)
        
        
