#!/usr/bin/env python3
"""
Whisper Voice Activator - High Accuracy Local Speech Recognition
Uses OpenAI's Whisper model for superior accuracy while running locally
"""

import pyaudio
import whisper
import time
import threading
import numpy as np
import ssl
import urllib.request
from colorama import Fore, Style
import logging
import io
import wave

# Fix SSL certificate issues for macOS
ssl._create_default_https_context = ssl._create_unverified_context

class WhisperVoiceActivator:
    def __init__(self, wake_word="hi mimi", model_size="tiny"):
        self.wake_word = wake_word.lower()
        self.model_size = model_size  # tiny, base, small, medium, large
        self.is_listening = False
        self.activation_callback = None
        self.audio_queue = []
        self.recording = False
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Audio setup
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk_size = 1024
        self.audio = pyaudio.PyAudio()
        
        # Load Whisper model
        print(f"{Fore.YELLOW}Loading Whisper model ({model_size})...{Style.RESET_ALL}")
        self.model = whisper.load_model(model_size)
        print(f"{Fore.GREEN}Whisper model loaded successfully!{Style.RESET_ALL}")
        
        # Setup microphone
        self._setup_microphone()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._process_audio, daemon=True)
        self.processing_thread.start()
    
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
            print(f"{Fore.GREEN}Whisper voice activator started. Say '{self.wake_word}' to activate.{Style.RESET_ALL}")
    
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
        
        audio_buffer = []
        silence_threshold = 500  # frames of silence
        silence_counter = 0
        min_audio_length = 16000  # 1 second of audio
        max_audio_length = 160000  # 10 seconds of audio
        
        try:
            while self.is_listening:
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                audio_buffer.append(data)
                
                # Convert to numpy array for volume detection
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()
                
                # Check for silence or speech
                if volume < 100:  # Silence threshold
                    silence_counter += 1
                else:
                    silence_counter = 0
                
                # If we have enough silence after speech, process the audio
                if (silence_counter > silence_threshold and 
                    len(audio_buffer) * self.chunk_size > min_audio_length):
                    
                    # Process the collected audio
                    self._process_audio_buffer(audio_buffer)
                    audio_buffer = []
                    silence_counter = 0
                
                # Prevent buffer from growing too large
                elif len(audio_buffer) * self.chunk_size > max_audio_length:
                    self._process_audio_buffer(audio_buffer)
                    audio_buffer = []
                    silence_counter = 0
                
        except Exception as e:
            self.logger.error(f"Error in audio stream: {e}")
        finally:
            stream.stop_stream()
            stream.close()
    
    def _process_audio_buffer(self, audio_buffer):
        """Process audio buffer with Whisper"""
        if not audio_buffer:
            return
        
        try:
            # Convert audio buffer to numpy array
            audio_data = b''.join(audio_buffer)
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_array, 
                language='en',
                initial_prompt="Wake word detection",
                fp16=False
            )
            
            text = result.get('text', '').lower().strip()
            
            if text:
                print(f"{Fore.YELLOW}Heard: '{text}'{Style.RESET_ALL}")
                
                # Check if wake word is detected
                if self._contains_wake_word(text):
                    print(f"{Fore.GREEN}Wake word detected! Activating MiMi Assistant...{Style.RESET_ALL}")
                    if self.activation_callback:
                        self.activation_callback()
                    time.sleep(2)  # Prevent immediate re-activation
        
        except Exception as e:
            self.logger.error(f"Error processing audio: {e}")
    
    def _process_audio(self):
        """Placeholder for processing thread"""
        pass
    
    def _contains_wake_word(self, text):
        """Check if text contains wake word with improved matching"""
        # Clean up the text
        text = text.lower().strip()
        wake_parts = self.wake_word.split()
        text_words = text.split()
        
        # Debug output
        print(f"  Debug - Wake parts: {wake_parts}, Text words: {text_words}")
        
        # Check for exact match first
        if self.wake_word in text:
            print(f"  Debug - Exact match found!")
            return True
        
        # Check for partial matches (more lenient)
        if len(wake_parts) >= 2:
            # Check if both parts are present in any order
            if all(part in text_words for part in wake_parts):
                print(f"  Debug - All parts found!")
                return True
        
        # Check for individual words with fuzzy matching
        for part in wake_parts:
            for word in text_words:
                # Check if word contains the wake word part
                if part in word or word in part:
                    print(f"  Debug - Partial match: '{part}' in '{word}'")
                    return True
        
        # Check for similar sounding words (basic phonetic matching)
        similar_words = {
            'hi': ['hey', 'he', 'high', 'hie'],
            'mimi': ['me', 'me me', 'meme', 'mimi']
        }
        
        for part in wake_parts:
            if part in similar_words:
                for similar in similar_words[part]:
                    if similar in text_words:
                        print(f"  Debug - Similar word match: '{similar}' for '{part}'")
                        return True
            
        return False
    
    def test_microphone(self):
        """Test microphone access and audio levels"""
        try:
            stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.microphone_index,
                frames_per_buffer=self.chunk_size
            )
            
            print("Testing microphone...")
            for i in range(5):
                data = stream.read(self.chunk_size, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio_data).mean()
                print(f"Audio sample {i+1}/5 - Volume: {volume:.2f}")
            
            stream.stop_stream()
            stream.close()
            print(f"{Fore.GREEN}Microphone test successful!{Style.RESET_ALL}")
            return True
            
        except Exception as e:
            print(f"Microphone test failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'audio'):
            self.audio.terminate()
