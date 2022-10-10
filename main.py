import pyttsx3 as p
import speech_recognition as sr
import pyaudio as pyadio

import autoutilities

engine = p.init()
rate = engine.getProperty('rate')
engine.setProperty('rate', 190)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)
greet = "Hello Sir, Trixie is online..., How can i help you"
my_commands_list = {'open': autoutilities.open, 'search': autoutilities.search}


def speak(value):
    engine.say(value)
    engine.runAndWait()


def screen_command(cd, tag):
    index = cd.find(tag)
    cmd = cd[index:]
    cmd = cmd.replace(tag, '')
    return cmd


def analyze(command):

    # for key,value in my_commands_list.items():
    #     if key in command:
    #         my_commands_list[key](screen_command(command, key))
    # else:
    #     speak("I didn't get you")

    if "open" in command:
        autoutilities.open(screen_command(command, 'open '))
    elif 'search' in command:
        autoutilities.search(screen_command(command, 'search '))
    else:
        speak("I didn't get you")


speak(greet)
while True:
    print("Waiting for your command...")
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.energy_threshold = 10000
        r.adjust_for_ambient_noise(source, 1.2)
        print("listening...")
        audio = r.listen(source)
        text = r.recognize_google(audio)
        print(text)
        analyze(text)
