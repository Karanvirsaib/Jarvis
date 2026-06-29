import speech_recognition as sr
import pyttsx3
from brain import get_response

# ---------------- VOICE ENGINE ----------------
engine = pyttsx3.init()
engine.setProperty("rate", 175)


def speak(text):
    print("Jarvis:", text)
    engine.say(text)
    engine.runAndWait()


# ---------------- SPEECH ENGINE ----------------
recognizer = sr.Recognizer()


def listen_once():
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        return recognizer.recognize_google(audio)
    except:
        return ""

# ---------------- WAKE WORD LOGIC ----------------


def wait_for_wake_word():
    print("🟡 Waiting for wake word: 'Jarvis'...")

    while True:
        text = listen_once().lower()

        if not text:
            continue

        print("Heard:", text)

        if "jarvis" in text:
            speak("Yes?")
            return

# ---------------- COMMAND MODE ----------------


def command_mode():
    print("🟢 Command mode active")

    while True:
        text = listen_once()

        if not text:
            continue

        print("You:", text)

        if text.lower() in ["exit", "stop", "sleep"]:
            speak("Going back to sleep.")
            return

        response = get_response(text)
        speak(response)

# ---------------- MAIN LOOP ----------------


print("🤖 Jarvis Wake Word System Started")

while True:
    wait_for_wake_word()
    command_mode()
