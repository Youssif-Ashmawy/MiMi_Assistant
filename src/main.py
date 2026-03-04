#!/usr/bin/env python3
"""
MiMi Assistant - Main Application Entry Point
Real-time gesture recognition assistant activated by voice
"""

import sys
import os
import time
import signal
from colorama import Fore, Style, init

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from voice.openwakeword_activator import OpenWakeWordActivator

# Initialize colorama for cross-platform colored output
init()

class MiMiAssistant:
    def __init__(self):
        self.running = False
        self.voice_activator = OpenWakeWordActivator()
        
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
        print(f"{Fore.CYAN}📷 Opening camera for gesture recognition...{Style.RESET_ALL}")
        
        # TODO: Implement camera and gesture recognition
        # This will be implemented in the next phase
        print(f"{Fore.YELLOW}Camera and gesture recognition coming soon!{Style.RESET_ALL}")
    
    def start(self):
        """Start the MiMi Assistant"""
        print(f"{Fore.BLUE}🚀 Starting MiMi Assistant...{Style.RESET_ALL}")
        
        # Test microphone
        if not self.voice_activator.test_microphone():
            print(f"{Fore.RED}❌ Microphone test failed. Please check your audio setup.{Style.RESET_ALL}")
            return
        
        # Set activation callback
        self.voice_activator.set_activation_callback(self.on_voice_activation)
        
        # Start voice listening
        self.voice_activator.start_listening()
        
        self.running = True
        print(f"{Fore.GREEN}✅ MiMi Assistant is running!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Say 'Hey Mycroft' to activate the assistant.{Style.RESET_ALL}")
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
