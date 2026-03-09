#!/usr/bin/env python3
"""
MiMi Assistant - Main Application Entry Point
Real-time gesture recognition assistant activated by voice
"""

import sys
import os
import time
import signal
import subprocess
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
        print(f"{Fore.CYAN}📷 Starting simple camera test...{Style.RESET_ALL}")
        
        # Check if camera is already running
        if self.camera_process and self.camera_process.poll() is None:
            print(f"{Fore.YELLOW}Camera is already running!{Style.RESET_ALL}")
            return
        
        try:
            # Get the path to cameratest.py
            camera_script = os.path.join(os.path.dirname(__file__), 'camera', 'camera_app.py')
            
            if not os.path.exists(camera_script):
                print(f"{Fore.RED}Camera test script not found: {camera_script}{Style.RESET_ALL}")
                return
            
            # Start the camera test script
            self.camera_process = subprocess.Popen(
                [sys.executable, camera_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print(f"{Fore.GREEN}✅ Simple camera test started!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Camera will run until you say 'Hey Mycroft' again or press Ctrl+C{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Error starting camera test: {e}{Style.RESET_ALL}")
    
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
        
        # Stop camera process if running
        if self.camera_process and self.camera_process.poll() is None:
            print(f"{Fore.YELLOW}Stopping camera test...{Style.RESET_ALL}")
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
