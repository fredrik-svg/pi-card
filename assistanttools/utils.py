import re
import os
import requests
import json
from datetime import datetime


def check_if_vision_mode(transcription):
    """
    Check if the transcription is a command to enter vision mode.
    """
    return any([x in transcription.lower() for x in ["photo", "picture", "image", "snap", "shoot"]])


def check_if_exit(transcription):
    """
    Check if the transcription is an exit command.
    """
    return any([x in transcription.lower() for x in ["stop", "exit", "quit"]])


def check_if_ignore(transcription):
    """
    Check if the transcription should be ignored. 
    This happens if the whisper prediction is "you" or "." or "", or is some sound effect like wind blowing, usually inside parentheses.
    These are things caused by having the fan so close to the microphone, definitely need to fix.
    """
    if transcription.strip().lower() == "you" or transcription.strip() == "." or transcription.strip() == "":
        return True
    if re.match(r"\(.*\)", transcription):
        return True
    return False


def dictate_ollama_stream(stream, early_stopping=False, max_spoken_tokens=250, GPIO=None):
    response = ""
    streaming_word = ""
    for i, chunk in enumerate(stream):
        if GPIO:
            if GPIO.input(2) == GPIO.LOW:
                return response

        text_chunk = chunk['message']['content']
        streaming_word += text_chunk
        response += text_chunk
        if i > max_spoken_tokens:
            early_stopping = True
            break

        if is_complete_word(text_chunk):
            streaming_word_clean = streaming_word.replace(
                '"', "").replace("\n", " ").replace("'", "").replace("*", "").replace('-', '').replace(':', '').replace('!', '')
            os.system(f"espeak '{streaming_word_clean}'")
            streaming_word = ""
    if not early_stopping:
        streaming_word_clean = streaming_word.replace(
            '"', "").replace("\n", " ").replace("'", "").replace("*", "").replace('-', '').replace(':', '').replace('!', '')

        os.system(f"espeak '{streaming_word_clean}'")

    return response


def is_complete_word(text_chunk):
    """
    Given the subword outputs from streaming, as these chunks are added together, check if they form a coherent word. If so, return the word.
    """

    if ' ' in text_chunk or all([x not in text_chunk for x in ['a', 'e', 'i', 'o', 'u']]):
        return True
    return False


def remove_parentheses(transcription):
    """
    Remove parentheses and their contents from the transcription.
    """
    return re.sub(r"\(.*\)", "", transcription).strip()


def send_to_n8n_webhook(webhook_url, transcription, response, tool_used=None):
    """
    Send conversation data to n8n webhook.
    
    Args:
        webhook_url: The n8n webhook URL
        transcription: The user's transcribed input
        response: The assistant's response
        tool_used: Optional tool that was used (e.g., 'weather', 'news', 'spotify')
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not webhook_url:
        return False
    
    try:
        payload = {
            "timestamp": datetime.now().isoformat(),
            "transcription": transcription,
            "response": response,
            "tool_used": tool_used
        }
        
        result = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if result.status_code == 200:
            print(f"Successfully sent data to n8n webhook")
            return True
        else:
            print(f"Failed to send to n8n webhook: {result.status_code}")
            return False
            
    except Exception as e:
        print(f"Error sending to n8n webhook: {e}")
        return False
