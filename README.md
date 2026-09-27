# SpeakEasy V1

SpeakEasy is an offline, real-time Roman Hinglish Speech-to-Text (ASR) desktop application built with Python and PyQt6.

Designed with efficiency in mind, SpeakEasy runs entirely locally (offline) on your CPU using `faster-whisper`. It provides low-latency transcription of Hindi and Hinglish speech into Roman script without the need for cloud services.

## Features

- **Offline Transcription**: Completely private and fast offline speech-to-text powered by `faster-whisper`.
- **Roman Hinglish Output**: Optimized for understanding conversational Hindi/Hinglish and outputting text in Romanized script.
- **Dual-Display Interface**: Unique split-panel UI (Left Eye / Right Eye) for flexible reading or dual-monitor setups.
- **Voice Activity Detection (VAD)**: Smart dual-layer VAD (RMS energy + voiced-fraction check) to filter out silence and reduce unnecessary processing, saving system resources.
- **Live VU Meter & Stats**: Real-time microphone level monitoring, word count tracking, and session duration.
- **Noise Control**: Built-in toggle for light noise environments to improve transcription accuracy.

## Prerequisites

- Python 3.8 or higher.
- A working microphone connected to your system.

## Installation

1. Navigate to the project directory:
   ```bash
   cd idea
   ```

2. **Create and activate a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: The project uses `faster-whisper` instead of standard `openai-whisper` for 3-4x less RAM usage and 2-3x faster CPU inference.*

## Usage

To start the SpeakEasy desktop application, simply run the `main.py` entry point:

```bash
python main.py
```

### Interface Overview

- **Top Bar**: Shows microphone status, offline indicator, and a "Clear" button to reset the transcript.
- **Sidebar**: Provides controls to change font size, text opacity, toggle noise filtering, and mute/unmute the microphone.
- **Split Panels**: Two independent text views that update simultaneously with the spoken text.
- **Bottom Bar**: Displays the live VU meter, ASR status, total word count, and session duration.

## Architecture

- **Frontend**: Built with `PyQt6` for a modern, responsive UI. Uses `QThread` to keep the interface smooth during heavy ASR processing.
- **Backend**: Uses `sounddevice` for low-level audio capture into a thread-safe chunk queue. The audio pipeline handles Voice Activity Detection (VAD) and hands over processed audio buffers to the inference engine.
- **ASR Engine**: Powered by `faster-whisper`. Runs in a dedicated daemon thread to continuously transcribe incoming audio chunks.

## License

This project contains a `LICENSE` file. Please refer to it for more details.
