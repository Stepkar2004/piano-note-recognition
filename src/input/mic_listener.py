# This file should contain the robust single-note aubio listener.
# If you changed it, revert it to this known-good state.
import pyaudio
import numpy as np
import aubio
import music21
import queue
import threading
import time

class MicListener:
    def __init__(self, note_queue: queue.Queue):
        self.note_queue = note_queue
        self.is_running = False
        self.thread = None
        self.BUFFER_SIZE = 2048
        self.SAMPLE_RATE = 44100
        self.FORMAT = pyaudio.paFloat32
        self.pitch_detector = aubio.pitch("yin", self.BUFFER_SIZE, self.BUFFER_SIZE, self.SAMPLE_RATE)
        self.pitch_detector.set_unit("Hz")
        self.pitch_detector.set_silence(-40)
        self.CONFIDENCE_THRESHOLD = 0.8
        self.COOLDOWN_SECONDS = 0.5

    def _listen_thread(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=self.FORMAT, channels=1, rate=self.SAMPLE_RATE,
                        input=True, frames_per_buffer=self.BUFFER_SIZE)
        print("--- MicListener (Single Note): Listening started ---")
        last_note_time = 0

        while self.is_running:
            try:
                data = stream.read(self.BUFFER_SIZE, exception_on_overflow=False)
                samples = np.frombuffer(data, dtype=np.float32)
                pitch = self.pitch_detector(samples)[0]
                confidence = self.pitch_detector.get_confidence()

                current_time = time.time()
                if current_time - last_note_time < self.COOLDOWN_SECONDS:
                    continue

                if confidence > self.CONFIDENCE_THRESHOLD and pitch > 0:
                    try:
                        p_obj = music21.pitch.Pitch()
                        p_obj.frequency = pitch
                        note_name = p_obj.nameWithOctave
                        self.note_queue.put(note_name)
                        last_note_time = current_time
                    except music21.pitch.PitchException:
                        continue
            except Exception as e:
                print(f"ERROR in MicListener loop: {e}")
                time.sleep(1)

        print("--- MicListener (Single Note): Listening stopped ---")
        if stream: stream.close()
        if p: p.terminate()

    def start(self):
        if self.is_running: return
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_thread, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.is_running: return
        self.is_running = False
        if self.thread:
            self.thread.join()