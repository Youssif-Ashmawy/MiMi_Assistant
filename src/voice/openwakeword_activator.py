#!/usr/bin/env python3
"""
OpenWakeWord Voice Activator - Ultra-fast Wake Word Detection
Uses openWakeWord for real-time, low-latency wake word detection
"""

import pyaudio
import openwakeword
import time
import threading
import numpy as np
from colorama import Fore, Style
import logging

class OpenWakeWordActivator:
    def __init__(self, wake_word="hey_mycroft"):
        self.wake_word = wake_word.lower()
        self.is_listening = False
        self.activation_callback = None
        self.last_activation_time = 0  # Track last activation time
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Audio setup - optimized for openWakeWord
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk_size = 1280  # 80ms at 16kHz (optimal for openWakeWord)
        self.audio = pyaudio.PyAudio()
        
        # Setup microphone
        self._setup_microphone()
        
        # Initialize openWakeWord model with only hey_mycroft
        print(f"{Fore.YELLOW}Loading openWakeWord models...{Style.RESET_ALL}")
        
        # Download models if not present
        try:
            openwakeword.utils.download_models()
        except Exception as e:
            print(f"{Fore.YELLOW}Models may already exist or download failed: {e}{Style.RESET_ALL}")
        
        # Initialize model with only hey_mycroft
        try:
            self.model = openwakeword.Model(
                wakeword_models=["hey_mycroft"]
            )
            print(f"{Fore.GREEN}openWakeWord loaded with hey_mycroft model!{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error loading openWakeWord: {e}{Style.RESET_ALL}")
            raise
    
    def _setup_microphone(self):
        """Find and setup the best available microphone"""
        try:
            # List all available microphones
            mics = []
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                if device_info['maxInputChannels'] > 0:
                    mics.append((i, device_info['name']))
            
            print(f"Available microphones:")
            for i, mic_name in mics:
                print(f"  {i}: {mic_name}")
            
            # Use default microphone
            self.microphone_index = None
            print(f"Using default microphone")
                
        except Exception as e:
            print(f"Error setting up microphone: {e}")
    
    def set_activation_callback(self, callback):
        """Set callback function to be called when wake word is detected"""
        self.activation_callback = callback
    
    def start_listening(self):
        """Start listening for wake word in background thread"""
        if not self.is_listening:
            self.is_listening = True
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            print(f"{Fore.GREEN}openWakeWord activator started. Say 'hey mycroft' to activate.{Style.RESET_ALL}")
    
    def stop_listening(self):
        """Stop listening for wake word"""
        self.is_listening = False
    
    def _listen_loop(self):
        """Main listening loop for wake word detection"""
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=self.microphone_index,
            frames_per_buffer=self.chunk_size
        )
        
        try:
            while self.is_listening:
                # Read audio data
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                
                # Convert to numpy array
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Get predictions from openWakeWord
                try:
                    predictions = self.model.predict(audio_data)
                    
                    # Check for hey_mycroft detection
                    for phrase, score in predictions.items():
                        if score > 0.3 and phrase == "hey_mycroft":  # Only accept hey_mycroft
                            current_time = time.time()
                            
                            # Check if enough time has passed since last activation (3 seconds)
                            if current_time - self.last_activation_time > 3:
                                print(f"{Fore.GREEN}Wake word detected! ({phrase}: {score:.3f}){Style.RESET_ALL}")
                                if self.activation_callback:
                                    self.activation_callback()
                                self.last_activation_time = current_time
                            break
                
                except Exception as e:
                    self.logger.error(f"Error in prediction: {e}")
                
        except Exception as e:
            self.logger.error(f"Error in audio stream: {e}")
        finally:
            stream.stop_stream()
            stream.close()
    
    def _matches_wake_word(self, detected_phrase):
        """Check if detected phrase matches our wake word"""
        detected_phrase = detected_phrase.lower().strip()
        
        # Direct match for hey_mycroft
        if detected_phrase == "hey_mycroft":
            return True
            
        return False
    
    def test_microphone(self):
        """Test microphone access and audio levels"""
        try:
            # Try to get available devices first
            import pyaudio
            audio = pyaudio.PyAudio()
            
            device_count = audio.get_device_count()
            print(f"Found {device_count} audio devices:")
            
            for i in range(device_count):
                device_info = audio.get_device_info_by_index(i)
                print(f"  {i}: {device_info['name']}")
            
            # Try to open default device
            try:
                stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    input_device_index=None,  # Use default device
                    frames_per_buffer=self.chunk_size
                )
            except Exception as e:
                print(f"Error opening default device: {e}")
                # Try first available device
                try:
                    stream = self.audio.open(
                        format=self.format,
                        channels=self.channels,
                        rate=self.rate,
                        input=True,
                        input_device_index=0,  # Try first device
                        frames_per_buffer=self.chunk_size
                    )
                except Exception as e2:
                    print(f"Error opening device 0: {e2}")
                    return False
            
            print("Testing microphone with openWakeWord...")
            for i in range(5):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()
                
                # Test prediction on audio
                try:
                    predictions = self.model.predict(audio_data)
                    max_score = max(predictions.values()) if predictions else 0
                    print(f"Audio sample {i+1}/5 - Volume: {volume:.2f}, Max prediction: {max_score:.3f}")
                except:
                    print(f"Audio sample {i+1}/5 - Volume: {volume:.2f}")
            
            stream.stop_stream()
            stream.close()
            print(f"{Fore.GREEN}Microphone test successful!{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"{Fore.RED}Microphone test failed: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}This might be a macOS audio permissions issue.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Try: System Preferences > Security & Privacy > Microphone{Style.RESET_ALL}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'audio'):
            self.audio.terminate()
