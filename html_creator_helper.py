import os
import re
import html
import logging
from werkzeug.utils import secure_filename

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_html_title(title):
    """
    Clean the title for use in HTML pages.

    :param title: The original title.
    :return: A sanitized version of the title safe for use in HTML.
    """
    # Escape HTML special characters to prevent HTML injection
    title = html.escape(title)
    return title

def clean_title(file_name):
    """Generate a clean title by removing special characters except spaces and underscores."""
    # Remove the file extension and any leading directory paths
    title = os.path.basename(file_name)
    # Replace underscores with spaces for readability
    title = title.replace("_", " ").title()
    # Remove any remaining special characters except spaces
    title = re.sub(r"[^a-zA-Z0-9\s]", "", title)
    return title



# convert txt to html 
def convert_txt_to_html(txt_file_path, html_file_path, title, css_file_path):
    try:
        title = clean_title(title)
        print(title)
        # Read the content of the .txt file
        with open(txt_file_path, 'r') as file:
            transcription = file.read()

        # Split into paragraphs and wrap in <p> tags
        paragraphs = transcription.split('\n')
        paragraphs = [f'<p>{p.strip()}</p>' for p in paragraphs if p.strip() != '']
        
        main_header_frame = f'''
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" type="text/css" href={css_file_path}>
            <title>{title}</title>
        </head>'''
        
        main_body_frame = f'''
        <body>
        <main>
        <header>
        <h1>{title}</h1>
        </header>
        <div>
        {''.join(paragraphs)}
        </div>
        </main>'''
        

        # HTML footer content
        footer = '''
        <footer>
        <hr>
            <img src="https://assets.ea.asu.edu/ulc/images/asu_header%20logo%20small%20200%20px.png" alt="ASU logo">
            <br>
            <p>This page was created by Universal Learner Courses. Visit <a href="https://ea.asu.edu/">ASU Universal Learner courses</a> to learn more.</p>
        </footer>'''
        
        

        # Construct the HTML content
        html_content = f'''
        <!DOCTYPE html>
        <html lang="en">
        {main_header_frame}
        {main_body_frame}
        {footer}
        </body>
        </html>'''
        
        # Write the HTML content to a file
        with open(html_file_path, "w") as html_file:
            html_file.write(html_content)

        logging.info(f"HTML file created: {html_file_path}")

    except Exception as e:
        logging.error(f"Error converting TXT to HTML: {e}")