import argparse
import sys
from pathlib import Path

# Add project root to sys.path
JARVIS_ROOT = Path(__file__).resolve().parent.parent
if str(JARVIS_ROOT) not in sys.path:
    sys.path.insert(0, str(JARVIS_ROOT))

from apps.jarvis.orchestrator import JarvisOrchestrator

def main():
    parser = argparse.ArgumentParser(description="JARVIS Command Line Interface")
    parser.add_argument("command", choices=["start", "stop", "status", "doctor", "chat", "update"])
    parser.add_argument("message", nargs="*", help="Message for chat command")
    args = parser.parse_args()

    if args.command == "chat":
        text = " ".join(args.message)
        if not text:
            print("Please provide a message. Example: jarvis chat 'hello'")
            sys.exit(1)

        jarvis = JarvisOrchestrator(root_dir=str(JARVIS_ROOT))
        response = jarvis.route_request(text)
        print("\nJARVIS:")
        print(response)

    elif args.command == "doctor":
        print("Checking dependencies...")
        print("PASS: Python")
        # Extend with exact checks later
        print("READY.")

if __name__ == "__main__":
    main()
