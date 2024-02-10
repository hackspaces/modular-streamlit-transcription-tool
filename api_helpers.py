import logging
import requests
import json
import tiktoken


# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Calculate the number of tokens used by a list of messages for a specific GPT model    
def num_tokens_from_messages(messages, model="gpt-4-1106-preview"):
    """
    Return the number of tokens used by a list of messages for a specific GPT model.

    :param messages: A list of message dictionaries with 'role' and 'content'.
    :param model: The model name (default: "gpt-3.5-turbo").
    :return: The number of tokens used.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: Model gpt-4-1106-preview. Using default encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")

    # Assumptions for token costs per message for GPT-3.5 Turbo and GPT-4 models
    tokens_per_message = 3 if "turbo" in model else 4
    tokens_per_name = 1 if "turbo" in model else -1

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name

    num_tokens += 3  # Accounting for the assistant's role in the reply
    return num_tokens

# Call the OpenAI Whisper API
def call_whisper_api(file_path, openai_api_key):
    """
    Calls the OpenAI Whisper API with the given audio file and returns the transcribed text.

    :param file_path: Path to the audio file.
    :param openai_api_key: Your OpenAI API key.
    :return: The transcribed text or None if the transcription fails.
    """
    url = "https://api.openai.com/v1/audio/transcriptions"

    headers = {
        "Authorization": f"Bearer {openai_api_key}"
    }

    files = {
        "file": open(file_path, 'rb'),
        "model": (None, "whisper-1")
    }

    try:
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        transcription_response = response.json()
        return transcription_response.get('text', '')
    except requests.RequestException as e:
        print(f"Error calling Whisper API: {e}")
        return None
    
# Call the GPT-4 API for reformating the transcript
def reformat_transcript_with_gpt4(raw_transcription, openai_api_key):
    """
    Calls GPT-4 API to reformat a raw transcript into a more readable format.

    :param raw_transcription: The raw transcript text to be reformatted.
    :param openai_api_key: Your OpenAI API key.
    :return: The reformatted transcript.
    """
    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api_key}"
    }


    data = {
        "model": "gpt-4-1106-preview",  # Update the model to "gpt-4" when available
        "messages": [

            {"role": "system","content": "\"You are the AI text-editor called Jarvy\"\nTASK:\nYour task is to reformat the transcript into a more readable format by breaking it into paragraphs to improve readability. \nINSTRUCTIONS: \n1.You are provided with a raw transcript from a course video. \n2 . Ensure all original content remains intact and do not add any headers or titles. The aim is to enhance the flow and readability while maintaining the integrity of the original content. \n3. Reformat the transcript to make it more reader-friendly without altering the content or adding titles.\n\nDO:\n1. Follow the instructions\n\n"},
            {"role": "user","content": "Here is the transcript: \n\n{raw_transcription}".format(raw_transcription=raw_transcription)},
            {"role": "user","content": "Please do not add any headings, bullet points or any other styling. "},
        ]
    }
    
    input_tokens = num_tokens_from_messages(data["messages"], model="gpt-4-1106-preview")
    logging.info(f"Estimated input tokens: {input_tokens}")
    print(headers)
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        response_data = response.json()
        if 'choices' in response_data: 
            output_content = response_data['choices'][0]['message']['content']
            print(output_content)
            output_tokens = num_tokens_from_messages([{"role": "assistant", "content": output_content}], model="gpt-4-1106-preview")
            logging.info(f"Estimated output tokens: {output_tokens}")
            return output_content
        else:
            return None
    except requests.RequestException as e:
        print(f"Error calling GPT-4 API: {e}")
        return None