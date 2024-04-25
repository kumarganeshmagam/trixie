from datetime import datetime
import os
import pyttsx3 as p
import speech_recognition as sr
import pyaudio as pyadio
from random import choice
from utils import opening_text
import autoutilities
from decouple import config

USERNAME = config('USER')
PANAME = config('PANAME')

engine = p.init()
rate = engine.getProperty('rate')
engine.setProperty('rate', 190)
engine.setProperty('volume', 1.0)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)
my_commands_list = {'open': autoutilities.open_app, 'search': autoutilities.search}


def speak(value):
    engine.say(value)
    engine.runAndWait()


def greet_user():
    hour = datetime.now().hour
    if (hour >= 6) and (hour < 12):
        speak(f"Good Morning {USERNAME}")
    elif (hour >= 12) and (hour < 16):
        speak(f"Good afternoon {USERNAME}")
    elif (hour >= 16) and (hour < 19):
        speak(f"Good Evening {USERNAME}")
    speak(f"I am {PANAME}. How may I assist you?")


def screen_command(cd, tag):
    index = cd.find(tag)
    cmd = cd[index:]
    cmd = cmd.replace(tag, '')
    return cmd


def action(command):
    print("Action initiated...")
    if "open" in command:
        speak(autoutilities.open_app(screen_command(command, 'open ')))
    elif 'image' in command:
        speak(autoutilities.image(screen_command(command, '')))
    elif 'search' in command:
        speak(autoutilities.search(screen_command(command, 'search ')))
    elif 'what is' in command or 'explain' in command:
        speak(autoutilities.chat_llama(screen_command(command, '')))
    elif 'write a' in command:
        autoutilities.code_llama(screen_command(command, ''))
        speak("Here is your code")
    else:
        speak("I didn't get you")


def analyze(command):
    print("Analyzing ...")
    try:
        if 'exit' in command or 'stop' in command:
            hour = datetime.now().hour
            if 21 <= hour < 6:
                speak("Good night sir, take care!")
            else:
                speak('Have a good day sir!')
            exit()
        else:
            speak(choice(opening_text))
            action(command)
    except Exception:
        speak('Sorry, I could not understand. Could you please say that again?')
        command = 'None'


def listening():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.energy_threshold = 10000
        r.adjust_for_ambient_noise(source, 1.2)
        print('Listening....')
        try:
            r.pause_threshold = 1
            audio = r.listen(source)
            text = r.recognize_google(audio, language='en-in')
        except Exception as e:
            print("Waiting....")
            speak(' ')
            return
        print(text)
        analyze(text)


greet_user()
while True:
    listening()
    print("Process terminated...")
