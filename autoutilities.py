from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType
import subprocess

app_list = {'google': 'chrome.exe', 'notepad': 'notepad.exe',
            'spotify': 'C:/Users/kumar/AppData/Roaming/Spotify/Spotify.exe',
            'brave': 'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe'}


# driver = webdriver.Chrome(service=Service(ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()))
def find_application(text):
    for key, value in app_list.items():
        if text.lower() == key:
            return value


def open(command):
    app = find_application(command)
    subprocess.Popen([app, 'http://www.google.com'])


def search(command):
    print(command)
