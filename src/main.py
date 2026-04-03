#!/usr/bin/env python3
"""
MiMi Assistant - Main Application Entry Point
Real-time gesture recognition assistant activated by voice
"""

import os
import signal
import subprocess
import sys
import time

from colorama import Fore, Style, init

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from voice.openwakeword_activator import OpenWakeWordActivator

# Initialize colorama for cross-platform colored output
init()


class MiMiAssistant:
    def __init__(self):
        self.running = False
        self.voice_activator = OpenWakeWordActivator()
        self.camera_process = None

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n{Fore.YELLOW}Shutting down MiMi Assistant...{Style.RESET_ALL}")
        self.stop()

    def on_voice_activation(self):
        """Callback when voice activation is detected"""
        print(f"{Fore.GREEN}🎤 MiMi Assistant Activated!{Style.RESET_ALL}")

        if self.camera_process and self.camera_process.poll() is None:
            print(f"{Fore.YELLOW}Camera is already running!{Style.RESET_ALL}")
            return

        camera_script = os.path.join(
            os.path.dirname(__file__), "camera", "camera_app.py"
        )

        if not os.path.exists(camera_script):
            print(
                f"{Fore.RED}Camera script not found: {camera_script}{Style.RESET_ALL}"
            )
            return

        self.camera_process = subprocess.Popen(
            [sys.executable, camera_script],
        )
        print(f"{Fore.GREEN}📷 Camera process launched — loading...{Style.RESET_ALL}")

    def start(self):
        """Start the MiMi Assistant"""
        print(f"{Fore.BLUE}🚀 Starting MiMi Assistant...{Style.RESET_ALL}")

        # Test microphone
        if not self.voice_activator.test_microphone():
            print(
                f"{Fore.RED}❌ Microphone test failed. Please check your audio setup.{Style.RESET_ALL}"
            )
            return

        # Set activation callback
        self.voice_activator.set_activation_callback(self.on_voice_activation)

        # Start voice listening
        self.voice_activator.start_listening()

        self.running = True
        print(f"{Fore.GREEN}✅ MiMi Assistant is running!{Style.RESET_ALL}")
        print(
            f"{Fore.CYAN}Say 'Hey Mycroft' to activate the assistant.{Style.RESET_ALL}"
        )
        print(f"{Fore.YELLOW}Press Ctrl+C to stop.{Style.RESET_ALL}")

        # Keep the main thread alive
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop the MiMi Assistant"""
        self.running = False
        if self.voice_activator:
            self.voice_activator.stop_listening()
        if self.camera_process and self.camera_process.poll() is None:
            self.camera_process.terminate()
            self.camera_process.wait(timeout=5)
        print(f"{Fore.GREEN}👋 MiMi Assistant stopped.{Style.RESET_ALL}")


def main():
    """Main entry point"""
    assistant = MiMiAssistant()

    try:
        assistant.start()
    except Exception as e:
        print(f"{Fore.RED}❌ Error starting MiMi Assistant: {e}{Style.RESET_ALL}")
        assistant.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
