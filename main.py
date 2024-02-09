import streamlit as st
from credit_auth_helpers import  credits_db
from baker import transcription_functionality, file_management

# Update this line if openai_api_key is to be obtained from elsewhere
openai_api_key = st.secrets["openai_api_key"]


# Use Streamlit theme options to select a theme
st.set_page_config(
    page_title="Transcript Creator",
    layout="wide",  # Use the wide layout for more space
    initial_sidebar_state="expanded",  # Start with a collapsed sidebar to give more space to the main content
    menu_items={
        'Get Help': 'https://www.example.com/help',
        'Report a bug': "https://www.example.com/bug",
        'About': "# This is a transcript creator app using Whisper AI and GPT-4."
    }
) 

# Title
st.header("Transcript Creator with Whisper AI and GPT-4", divider="orange")

# Initialize Streamlit session state variables if they don't exist
if 'name' not in st.session_state:
    st.session_state.name = ""
if 'key' not in st.session_state:
    st.session_state.key = ""
    
# Page Navigation
with st.sidebar:
    with st.expander("Step 1: Name and Key", expanded=True):
        name = st.text_input("Enter your name")
        st.session_state.name = name
        key = st.text_input("Enter your key")
        st.session_state.key = key
        credit_on = st.checkbox("Use credits", value=False, help="Use credits to process files.")
        
        if st.session_state.name in credits_db and credits_db[st.session_state.name]['key'] == st.session_state.key:
            st.success("User authenticated!")
            st.write(f"Available credits: {credits_db[st.session_state.name]['credits']}")
        elif st.session_state.name or st.session_state.key:  # Only show an error if fields aren't empty
            st.error("Invalid name or key.")    
    st.title("Navigation")
    page = st.sidebar.radio("Select Page", ["Current Functionality", "File Preview"])
            
if page == "Current Functionality":
    transcription_functionality(name=st.session_state.name, key=st.session_state.key, credit_on=credit_on, openai_api_key=openai_api_key)
    file_management(page)
elif page == "File Preview":
    file_management(page)