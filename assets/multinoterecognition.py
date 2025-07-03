import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np
import math
import threading
from scipy.signal import find_peaks
import collections  # Needed for the new confirmation buffer


# --- The Final Chord Verification Backend ---

class ChordVerifier:
    def __init__(self):
        self.CHUNK = 2048 * 4
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.TARGET_NOTES = ["B3", "F4", "G4", "G3"]
        self.TARGET_NOTE_SET = set(self.TARGET_NOTES)

        # --- YOUR PROVEN "GOLDEN" SETTINGS ---
        self.PEAK_HEIGHT = 50000
        self.PEAK_PROMINENCE = 10000
        self.TARGET_NOTE_TOLERANCE_PERCENT = 2.0

        self.A4_FREQ = 440.0
        self.NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]

        # --- THE FINAL SOLUTION: The Confirmation Buffer ---
        # A chord must be correct for this many consecutive chunks to be displayed.
        self.CONFIRMATION_BUFFER_SIZE = 4
        self.correctness_history = collections.deque(maxlen=self.CONFIRMATION_BUFFER_SIZE)

        self.found_notes = {note: False for note in self.TARGET_NOTES}
        self.is_correct = False
        self.current_volume = 0.0
        self.is_running = False
        self.p = pyaudio.PyAudio()
        self.stream = None

    def note_to_frequency(self, note_name):
        note_map = {name: i for i, name in enumerate(self.NOTES)}
        octave = int(note_name[-1])
        pitch = note_name[:-1]
        n = (octave - 4) * 12 + note_map.get(pitch, 0)
        return self.A4_FREQ * (2 ** (n / 12.0))

    def frequency_to_note(self, freq):
        """Converts a single frequency to its closest note name."""
        if freq < 20: return None
        n = int(round(12 * math.log2(freq / self.A4_FREQ)))
        note_index = n % 12
        octave = 4 + (n + 9) // 12
        return f"{self.NOTES[note_index]}{octave}"

    def verify_chord(self, data):
        """Analyzes audio using robust Peak-to-Note Mapping."""
        self.current_volume = np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16).astype(np.float32) ** 2))
        if self.current_volume < 100:
            return {note: False for note in self.TARGET_NOTES}, False

        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        window = np.hanning(len(samples))
        samples *= window
        fft_result = np.fft.rfft(samples)
        fft_freqs = np.fft.rfftfreq(len(samples), 1.0 / self.RATE)
        magnitude_spectrum = np.abs(fft_result)

        peak_indices, _ = find_peaks(magnitude_spectrum, height=self.PEAK_HEIGHT, prominence=self.PEAK_PROMINENCE)
        found_peak_freqs = fft_freqs[peak_indices]

        detected_note_set = {self.frequency_to_note(freq) for freq in found_peak_freqs if self.frequency_to_note(freq)}

        is_subset = self.TARGET_NOTE_SET.issubset(detected_note_set)

        notes_found_this_chunk = {note: note in detected_note_set for note in self.TARGET_NOTES}

        return notes_found_this_chunk, is_subset

    def audio_processing_loop(self):
        self.stream = self.p.open(
            format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE,
            input=True, frames_per_buffer=self.CHUNK
        )
        self.is_running = True

        while self.is_running:
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                instant_found_notes, instant_is_correct = self.verify_chord(data)
                self.found_notes = instant_found_notes

                # --- APPLYING THE CONFIRMATION BUFFER ---
                self.correctness_history.append(instant_is_correct)

                # The final status is only "Correct" if the buffer is full AND all items in it are True.
                if len(self.correctness_history) == self.CONFIRMATION_BUFFER_SIZE and all(self.correctness_history):
                    self.is_correct = True
                else:
                    self.is_correct = False

            except (IOError, ValueError):
                continue

        if self.stream: self.stream.close()
        self.p.terminate()

    def stop(self):
        self.is_running = False


# --- The Final, Polished GUI ---
class ChordVerifierApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Chord Verifier")
        self.root.geometry("450x500")
        self.root.configure(bg="#2c3e50")

        self.detector = ChordVerifier()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", troughcolor='#34495e', background='#2ecc71')
        style.configure("TLabelframe", background="#34495e", bordercolor="#34495e")
        style.configure("TLabelframe.Label", foreground="#ecf0f1", background="#34495e", font=("Helvetica", 11, "bold"))

        self.status_label = tk.Label(self.root, text="Play the target chord...", font=("Helvetica", 24, "bold"),
                                     fg="#ecf0f1", bg="#2c3e50")
        self.status_label.pack(pady=20)

        target_frame = ttk.Labelframe(self.root, text="Target Notes")
        target_frame.pack(pady=10, padx=20, fill='x')

        self.note_labels = {}
        for note in self.detector.TARGET_NOTES:
            lbl = tk.Label(target_frame, text=note, font=("Helvetica", 36, "bold"), fg="#7f8c8d", bg="#34495e", width=4)
            lbl.pack(side=tk.LEFT, expand=True, padx=10, pady=10)
            self.note_labels[note] = lbl

        volume_frame = ttk.Labelframe(self.root, text="Live Input Volume")
        volume_frame.pack(pady=20, padx=20, fill='x')
        self.volume_bar = ttk.Progressbar(volume_frame, length=300, mode='determinate', style="TProgressbar")
        self.volume_bar.pack(pady=10, padx=10)

        self.thread = threading.Thread(target=self.detector.audio_processing_loop, daemon=True)
        self.thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_gui()

    def update_gui(self):
        # The visual feedback for individual notes remains instant
        for note, found in self.detector.found_notes.items():
            color = "#2ecc71" if found else "#7f8c8d"
            self.note_labels[note].config(fg=color)

        # The final "Correct!" status is now buffered and stable
        if self.detector.is_correct:
            self.status_label.config(text="Correct!", fg="#2ecc71")
        else:
            self.status_label.config(text="Keep Trying...", fg="#ecf0f1")

        self.volume_bar['value'] = (self.detector.current_volume / 15000) * 100
        self.root.after(50, self.update_gui)

    def on_closing(self):
        self.detector.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChordVerifierApp(root)
    root.mainloop()