"""Jarvis command-line entry point."""

import argparse

from config import settings
from core.assistant import JarvisAssistant
from core.llm import LLMClient
from core.memory import MemoryManager


EXIT_COMMANDS = {"exit", "quit", "goodbye"}


def run_chat(assistant: JarvisAssistant, speak: bool = False) -> None:
    voice = None
    if speak:
        from voice.speech import VoiceInterface

        voice = VoiceInterface(
            settings.speech_rate,
            settings.neural_voice,
            settings.neural_voice_rate,
            settings.neural_voice_pitch,
        )
    print("Jarvis is ready. Type 'help' for commands or 'exit' to stop.")
    while True:
        try:
            user_input = input("\nYou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nJarvis > Goodbye.")
            return
        if user_input.lower() in EXIT_COMMANDS:
            print("Jarvis > Goodbye.")
            return
        response = assistant.respond(user_input)
        print(f"\nJarvis > {response}")
        if voice:
            voice.speak(response)


def run_voice(assistant: JarvisAssistant) -> None:
    from voice.speech import VoiceInterface

    voice = VoiceInterface(
        settings.speech_rate,
        settings.neural_voice,
        settings.neural_voice_rate,
        settings.neural_voice_pitch,
    )
    print("Voice mode is ready. Say 'exit' to stop.")
    voice.speak("Jarvis is ready.")
    while True:
        try:
            user_input = voice.listen(
                settings.listen_timeout, settings.phrase_time_limit
            )
        except RuntimeError as exc:
            print(f"Jarvis > {exc}")
            continue
        if not user_input:
            continue
        print(f"You > {user_input}")
        if user_input.lower() in EXIT_COMMANDS:
            voice.speak("Goodbye.")
            return
        response = assistant.respond(user_input)
        print(f"Jarvis > {response}")
        voice.speak(response)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local Jarvis assistant")
    parser.add_argument("--mode", choices=("chat", "voice", "desktop"), default="chat")
    parser.add_argument("--speak", action="store_true", help="Speak responses in chat mode")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with MemoryManager(settings.database_path) as memory:
        assistant = JarvisAssistant(
            memory,
            LLMClient(
                settings.model,
                settings.ollama_keep_alive,
                settings.max_response_tokens,
            ),
        )
        if args.mode == "desktop":
            from ui.desktop import run_desktop
            run_desktop(assistant)
        elif args.mode == "voice":
            run_voice(assistant)
        else:
            run_chat(assistant, args.speak)


if __name__ == "__main__":
    main()
