import sounddevice as sd
import numpy as np
import boto3
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import asyncio
import tkinter as tk
import threading
import datetime
import os
import re

AUDIO_DEVICE_INDEX = 1

class CaptionDisplay:
    def __init__(self, on_closing):
        self.root = tk.Tk()
        self.root.title("Live Captions")
        self.label = tk.Label(self.root, text="", font=("Arial", 24), wraplength=600, justify="center")
        self.label.pack(pady=20)
        self.root.protocol("WM_DELETE_WINDOW", on_closing)

    def update_caption(self, text):
        self.label.config(text=text)

    def run(self):
        self.root.mainloop()

class MyEventHandler(TranscriptResultStreamHandler):
    def __init__(self, stream, caption_display, transcript_file):
        super().__init__(stream)
        self.latest_results = []
        self.last_processed_time = 0
        self.caption_display = caption_display
        self.transcript_file = transcript_file

    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        results = transcript_event.transcript.results
        for result in results:
            if len(result.alternatives) > 0:
                transcript = result.alternatives[0]
                if not result.is_partial:
                    self.latest_results.append(transcript)
                    self.display_caption()

    def display_caption(self):
        if len(self.latest_results) > 0:
            latest = self.latest_results[-1]
            words = latest.items
            if len(words) > 0:
                new_words = [word for word in words if word.start_time > self.last_processed_time]
                if new_words:
                    start_time = new_words[0].start_time
                    end_time = new_words[-1].end_time
                    caption = ' '.join([word.content for word in new_words])
                    caption = self.post_process_transcript(caption)
                    display_text = f"[{start_time:.2f} - {end_time:.2f}] {caption}"
                    print(display_text)
                    self.caption_display.root.after(0, self.caption_display.update_caption, display_text)
                    self.last_processed_time = end_time
                    
                    # Save to file
                    with open(self.transcript_file, 'a') as f:
                        f.write(f"{display_text}\n")

    def post_process_transcript(self, transcript):
        # Convert to proper case (capitalize first letter of sentences)
        transcript = re.sub(r'(^|[.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), transcript)
        
        # Correct common mistakes
        corrections = {
            'i ': "I ",
            'i\'m': "I'm",
            'don\'t': "don't",
            'can\'t': "can't",
            # Add more corrections as needed
        }
        for mistake, correction in corrections.items():
            transcript = transcript.replace(mistake, correction)
        
        # Remove spaces before commas, periods, question marks, and exclamation points
        transcript = re.sub(r'\s+([,.:!?])', r'\1', transcript)
        
        # Ensure a space after these punctuation marks if followed by a word
        transcript = re.sub(r'([,.:!?])(\w)', r'\1 \2', transcript)
        
        # Remove extra spaces
        transcript = ' '.join(transcript.split())
        
        return transcript

class AudioTranscriber:
    def __init__(self):
        self.shutdown_flag = False
        self.caption_display = CaptionDisplay(self.on_closing)
        self.stream = None
        self.client = None
        self.transcript_file = self.create_transcript_file()

    def create_transcript_file(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{timestamp}.txt"
        os.makedirs("transcripts", exist_ok=True)
        return os.path.join("transcripts", filename)

    def on_closing(self):
        print("Shutting down...")
        self.shutdown_flag = True
        self.caption_display.root.quit()
        print(f"Transcript saved to: {self.transcript_file}")

    async def mic_stream(self):
        loop = asyncio.get_event_loop()
        input_queue = asyncio.Queue()

        def callback(indata, frame_count, time_info, status):
            loop.call_soon_threadsafe(input_queue.put_nowait, (bytes(indata), status))

        stream = sd.RawInputStream(
            channels=1,
            samplerate=16000,
            callback=callback,
            blocksize=1024 * 2,
            dtype="int16",
            device=AUDIO_DEVICE_INDEX
        )
        
        with stream:
            while not self.shutdown_flag:
                indata, status = await input_queue.get()
                yield indata, status

    async def write_chunks(self, stream):
        async for chunk, status in self.mic_stream():
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
            if self.shutdown_flag:
                break
        await stream.input_stream.end_stream()

    async def basic_transcribe(self):
        self.client = TranscribeStreamingClient(region="us-west-2")

        self.stream = await self.client.start_stream_transcription(
            language_code="en-US",
            media_sample_rate_hz=16000,
            media_encoding="pcm"
        )

        handler = MyEventHandler(self.stream.output_stream, self.caption_display, self.transcript_file)
        await asyncio.gather(self.write_chunks(self.stream), handler.handle_events())

    def run_transcribe(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.basic_transcribe())
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            loop.close()
            if self.stream:
                loop.run_until_complete(self.stream.input_stream.end_stream())
            if self.client:
                self.client.close()

    def run(self):
        transcribe_thread = threading.Thread(target=self.run_transcribe)
        transcribe_thread.start()
        self.caption_display.run()
        transcribe_thread.join()

if __name__ == "__main__":
    transcriber = AudioTranscriber()
    transcriber.run()
