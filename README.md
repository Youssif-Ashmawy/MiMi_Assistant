# MiMi Assistant

A real-time gesture recognition assistant that activates with voice commands and performs system actions based on hand gestures.

## Features

- **Local Voice Activation**: Uses openWakeWord for ultra-fast offline wake word detection
- **Wake Word Detection**: Activated by saying "Hey Mycroft" with high accuracy
- **Real-time Gesture Recognition**: Uses camera to detect hand gestures
- **System Actions Examples**:
  - Fist pump for 3 seconds → Take screenshot
  - Two hands bye bye for 5 seconds → Logout
- **Privacy-Focused**: All processing happens locally, no internet required after setup
- **Extensible**: Easy to add new gestures and actions

## Project Structure

```
MiMi_Assistant/
├── src/
│   ├── voice/           # Voice recognition and activation
│   │   ├── openwakeword_activator.py     # Fast openWakeWord-based activator (CURRENT)
│   │   └── whisper_voice_activator.py    # Initial Whisper-based activator (Old but kept for reference)
│   ├── camera/          # Camera capture and processing ~ TO DO
│   ├── gestures/        # Gesture recognition logic ~ TO DO
│   ├── actions/         # System action implementations ~ TO DO
│   ├── utils/           # Utility functions ~ TO DO
│   └── main.py          # Main application entry point
├── config/
│   └── app_config.yaml  # This should be created to ease the modification of any parameter across the application ~ TO DO
├── tests/               # Test files ~ TO DO
└── requirements.txt     # Python dependencies
```

## Setup

1. **Install System Dependencies** (required first):
   - **macOS**: Install PortAudio for PyAudio
     ```bash
     brew install portaudio
     ```

2. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate 
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**:
   ```bash
   source venv/bin/activate
   cd src
   python main.py
   ```

**Note**: The first run will download openWakeWord models (~60MB) for local wake word detection. After this initial download, the application works completely offline with ultra-fast response times.

## Usage

1. Start the application:
   ```bash
   source venv/bin/activate
   cd src
   python main.py
   ```

2. The application will:
   - Test your microphone
   - Load openWakeWord models (first run only)
   - Start listening for the wake word

3. Say "Hey Mycroft" to activate the assistant
   - The system uses openWakeWord for fast wake word detection
   - Debug output shows what was heard

4. The camera will open and start listening for gestures

5. Perform gestures to trigger actions:
   - More to be added soon

6. Press Ctrl+C to stop the application

## Development

The project is organized into modular components:

### Voice Recognition
- **Primary**: openWakeWord for ultra-fast wake word detection
- **Features**: 80ms response time, high accuracy, minimal CPU usage

### Next Phases
- Camera and gesture recognition implementation
- Action execution system
- Configuration management improvements

## License

MIT License (For now as it is a private repo)
