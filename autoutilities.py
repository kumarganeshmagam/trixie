import json
from subprocess import Popen
import requests
from random import choice
from utils import done_texts
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter
import wikipedia
import os
from PIL import Image
import subprocess

url = "http://localhost:11434/api/"
current_directory = os.path.dirname(os.path.abspath(__file__))
upload_image = os.path.join(current_directory, "upload_file.py")
save_image_server = os.path.join(current_directory, "app.py")

def construct_prompt(command):
    if "program" in command:
        return "Generate a simple Python 3 code snippet " + command.split("program ")[1]
    elif "what" in command:
        return command + "please summarize in a single sentence of few words"
    elif "why" in command:
        return command + "please summarize under 25 words"
    elif "explain" in command or "tell" in command:
        return command + (
            "please summarize the explanation in 25-40 words with any types information needed and give a "
            "simple understandable example")
    elif "image" in command:
        return command + "Please summarize it in 40 words"
    else:
        return command


def generate(prompt):
    data = {
        "model": "codellama",
        "prompt": prompt,
        "raw": True,
        "stream": False
    }
    response = requests.post(url + "generate", json=data)
    if response.status_code == 200:
        result = response.json()
        formatted_response = highlight(result["response"], PythonLexer(), TerminalFormatter())
        print(formatted_response)
        return result["response"]
    else:
        print(f"Error: {response.status_code} - {response.text}")
    return choice(done_texts)


def chat(prompt):
    data = {
        "model": "llama2",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False
    }
    response = requests.post(url + "chat", json=data)
    if response.status_code == 200:
        result = response.json()
        return result["message"]["content"]
    else:
        print(f"Error: {response.status_code} - {response.text}")
    return choice(done_texts)


def scan(prompt, images):
    data = {
        "model": "llava:13b",
        "prompt": prompt,
        "images": images,
        "raw": True,
        "stream": False
    }
    response = requests.post(url + "generate", json=data)
    if response.status_code == 200:
        result = response.json()
        formatted_response = highlight(result["response"], PythonLexer(), TerminalFormatter())
        print(formatted_response)
        return result["response"]
    else:
        print(f"Error: {response.status_code} - {response.text}")
    return choice(done_texts)


app_list = {'google': 'chrome.exe', 'notepad': 'notepad.exe',
            'spotify': 'C:/Users/kumar/AppData/Roaming/Spotify/Spotify.exe',
            'brave': 'C:/Users/kumar/AppData/Local/BraveSoftware/Brave-Browser/Application/brave.exe'}


# driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()))
def find_application(text):
    for key, value in app_list.items():
        if text.lower() == key:
            return value.lower()


def get_images_from_folder(folder_path):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']  # Add more if needed
    image_list = []

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        # Check if the file is an image based on its extension
        if any(filename.lower().endswith(ext) for ext in image_extensions):
            try:
                # Attempt to open the file as an image
                with Image.open(file_path):
                    # If successful, add the file path to the image list
                    image_list.append(file_path)
            except (IOError, SyntaxError):
                # Handle cases where the file is not a valid image
                print(f"Skipping non-image file: {file_path}")

    return image_list[-1]


def open_app(command):
    print("initiated openapp ")
    app = find_application(command)
    print("initiating subprocess ")
    proc = Popen([app, 'http://www.google.com'])
    print("Application opened", proc)
    Popen.kill(proc)
    print("Application killed")
    return choice(done_texts)


def search(command):
    result = wikipedia.summary(command, sentences=2)
    return result


def code_llama(command):
    prompt = construct_prompt(command)
    response = generate(prompt)
    return response


def chat_llama(command):
    prompt = construct_prompt(command)
    response = chat(prompt)
    return response.replace('*', '')


def image(command):
    prompt = construct_prompt(command)
    # subprocess.run(["python", save_image_server], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # subprocess.run(["python", upload_image])
    # images = get_images_from_folder(current_directory + "/uploads")
    response = scan(prompt, "C:\/Users\kumar\OneDrive\Pictures\/aesthetics-of-abandonment-5160x2160-v0-sv3ot16jm9jb1")
    return response


def play(command):
    print("initiated play... ")
    app = find_application('spotify')
    print("initiating subprocess ")
    proc = Popen([app])
    print("Application opened", proc)
    Popen.kill(proc)
    print("Application killed")
    return choice(done_texts)
