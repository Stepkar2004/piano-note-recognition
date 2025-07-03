# (imports remain the same)
import pyaudio, numpy as np, music21, queue, threading, collections
from scipy.signal import find_peaks


class ChordDetector:
    def __init__(self, update_queue: queue.Queue):
        self.update_queue = update_queue
        self.is_running = False
        self.thread = None
        self.CHUNK = 2048 * 4
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.TARGET_NOTE_SET = set()
        self.PEAK_HEIGHT = 50000
        self.PEAK_PROMINENCE = 10000
        self.CONFIRMATION_BUFFER_SIZE = 4
        self.correctness_history = collections.deque(maxlen=self.CONFIRMATION_BUFFER_SIZE)

    def set_target_notes(self, notes: set[str]):
        print(f"ChordDetector: New target notes set -> {notes}")
        self.TARGET_NOTE_SET = notes
        # --- FIX: ALWAYS clear the history when a new target is set ---
        self.correctness_history.clear()

    def frequency_to_note(self, freq):
        if freq < 20: return None
        try:
            p = music21.pitch.Pitch()
            p.frequency = freq
            return p.nameWithOctave
        except music21.pitch.PitchException:
            return None

    def verify_chord(self, data):
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms_volume = np.sqrt(np.mean(samples ** 2))
        if rms_volume < 100:
            # If volume is too low, it's definitely not correct
            return {}, False

        samples *= np.hanning(len(samples))
        fft_result = np.fft.rfft(samples)
        fft_freqs = np.fft.rfftfreq(len(samples), 1.0 / self.RATE)
        magnitude_spectrum = np.abs(fft_result)
        peak_indices, _ = find_peaks(magnitude_spectrum, height=self.PEAK_HEIGHT, prominence=self.PEAK_PROMINENCE)
        found_peak_freqs = fft_freqs[peak_indices]
        detected_note_set = {self.frequency_to_note(freq) for freq in found_peak_freqs if self.frequency_to_note(freq)}

        # Check if ALL target notes are present in the detected notes
        is_subset = self.TARGET_NOTE_SET.issubset(detected_note_set)
        notes_found_this_chunk = {note: note in detected_note_set for note in self.TARGET_NOTE_SET}
        return notes_found_this_chunk, is_subset

    def audio_processing_loop(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE,
                        input=True, frames_per_buffer=self.CHUNK)
        self.is_running = True
        print("--- ChordDetector: Listening started ---")

        while self.is_running:
            try:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                # --- FIX: Ensure a value is always put in the queue each loop ---
                found_notes_dict, is_correct_now = self.verify_chord(data)

                self.correctness_history.append(is_correct_now)
                is_stable_correct = (len(self.correctness_history) == self.CONFIRMATION_BUFFER_SIZE and
                                     all(self.correctness_history))

                update_data = {'found_notes': found_notes_dict, 'is_correct': is_stable_correct}
                self.update_queue.put(update_data)
            except (IOError, ValueError):
                # On error, put a "not correct" state in the queue to keep UI updated
                self.update_queue.put({'found_notes': {}, 'is_correct': False})
                continue

        if stream: stream.close()
        p.terminate()
        print("--- ChordDetector: Listening stopped ---")

    def start(self):
        if self.is_running: return
        self.is_running = True
        self.thread = threading.Thread(target=self.audio_processing_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False