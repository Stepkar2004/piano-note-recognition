import pyaudio
import numpy as np
import aubio
import music21
import queue
import threading
import time


class MicListener:
    """
    Listens to the microphone using aubio, but with the advanced stability
    and thresholding logic for reliable note detection.
    """

    def __init__(self, note_queue: queue.Queue):
        self.note_queue = note_queue
        self.is_running = False
        self.thread = None

        # Audio Stream Parameters
        self.BUFFER_SIZE = 2048
        self.SAMPLE_RATE = 44100
        self.FORMAT = pyaudio.paFloat32

        # Aubio Pitch Detection Setup
        self.pitch_detector = aubio.pitch("yin", self.BUFFER_SIZE, self.BUFFER_SIZE, self.SAMPLE_RATE)
        self.pitch_detector.set_unit("Hz")
        self.pitch_detector.set_silence(-40)

        # Tunable Detection Parameters
        self.CONFIDENCE_THRESHOLD = 0.8
        self.VOLUME_THRESHOLD = 0.015
        self.STABILITY_WINDOW = 3
        self.COOLDOWN_SECONDS = 0.5

    def _listen_thread(self):
        """The main workhorse method that runs in the background."""
        p = pyaudio.PyAudio()
        stream = p.open(format=self.FORMAT,
                        channels=1,
                        rate=self.SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=self.BUFFER_SIZE)

        print("--- MicListener: Robust 'aubio' listener started ---")

        note_history = []
        last_note_time = 0

        while self.is_running:
            try:
                # --- THE FIX: Changed BUFFER_M back to BUFFER_SIZE ---
                data = stream.read(self.BUFFER_SIZE, exception_on_overflow=False)
                samples = np.frombuffer(data, dtype=np.float32)

                rms = np.sqrt(np.mean(samples ** 2))

                if rms > self.VOLUME_THRESHOLD:
                    pitch = self.pitch_detector(samples)[0]
                    confidence = self.pitch_detector.get_confidence()

                    current_time = time.time()
                    if current_time - last_note_time < self.COOLDOWN_SECONDS:
                        continue

                    note_name = "---"
                    if confidence > self.CONFIDENCE_THRESHOLD and pitch > 0:
                        try:
                            p_obj = music21.pitch.Pitch()
                            p_obj.frequency = pitch
                            note_name = p_obj.nameWithOctave
                        except music21.pitch.PitchException:
                            note_name = "---"

                    note_history.append(note_name)
                    if len(note_history) > self.STABILITY_WINDOW:
                        note_history.pop(0)

                    if len(note_history) == self.STABILITY_WINDOW:
                        stable_note = max(set(note_history), key=note_history.count)
                        if stable_note != "---":
                            print(f"    --> STABLE NOTE DETECTED: {stable_note}")
                            self.note_queue.put(stable_note)
                            last_note_time = time.time()
                            note_history.clear()
                else:
                    note_history.clear()

            except Exception as e:
                print(f"ERROR in MicListener loop: {e}")
                time.sleep(1)

        print("--- MicListener: Listening stopped ---")
        if stream:
            stream.stop_stream()
            stream.close()
        if p:
            p.terminate()

    def start(self):
        if self.is_running: return
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_thread)
        self.thread.start()

    def stop(self):
        if not self.is_running: return
        self.is_running = False
        if self.thread:
            self.thread.join()