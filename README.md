# Live Captions Transcriber

## Description

This project is a Live Captions Transcriber that uses speech recognition to provide real-time captions for audio input. It displays the captions in a graphical user interface and saves the transcript to a file.

## Features

- Real-time speech-to-text conversion
- Live caption display
- Transcript saving
- Post-processing of transcripts for improved readability

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/xsmorris/caption-audio-device.git
   ```
2. Navigate to the project directory:
   ```
   cd caption-audio-device
   ```
3. Install the required dependencies:
   ```
   pip install sounddevice boto3 amazon-transcribe numpy tkinter
   ```

## Usage

1. Run the main script:
   ```
   python listen.py
   ```
2. Speak into your microphone or play audio through your system.
3. View the live captions in the GUI window.
4. Find the saved transcript in the `transcripts` folder after closing the application.

## Configuration

- Adjust the audio input device in the `listen.py` file if needed.
-- The variable `AUDIO_DEVICE_INDEX` should be set to the index of the audio device to capture.
- Modify the post-processing rules in the `post_process_transcript` method to suit your needs.
