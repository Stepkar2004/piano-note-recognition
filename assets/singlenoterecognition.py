import tkinter as tk
from tkinter import ttk
import pyaudio
import numpy as np
import math
import threading
from scipy.signal import butter, lfilter
import librosa  # --- NEW: Import the professional audio analysis library ---


# --- The Final Audio Processing Backend ---

class NoteDetector:
    def __init__(self, volume_var, stability_var):
        self.CHUNK = 2048 * 2
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.A4_FREQ = 440.0
        self.NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]

        # --- Linking UI controls and setting up state ---
        self.volume_threshold_var = volume_var
        self.stability_var = stability_var
        self.note_history = []
        self.stable_note = "---"
        self.stable_frequency = 0.0
        self.current_volume = 0.0
        self.is_running = False
        self.p = pyaudio.PyAudio()
        self.stream = None

        self.attack_rejection_counter = 0
        self.last_volume = 0
        self.ATTACK_REJECTION_CHUNKS = 2

        # --- MODIFIED: Lowered the filter cutoff to protect low notes ---
        self.filter_cutoff = 50  # Lowered from 80 Hz to 50 Hz to allow C2/D2
        self.filter_order = 4
        nyquist = 0.5 * self.RATE
        normal_cutoff = self.filter_cutoff / nyquist
        self.b, self.a = butter(self.filter_order, normal_cutoff, btype='high', analog=False)

    def frequency_to_note(self, freq):
        """Converts a frequency in Hz to the closest musical note."""
        if freq is None or freq < 20: return "---"
        n = int(round(12 * math.log2(freq / self.A4_FREQ)))
        note_index = n % 12
        octave = 4 + (n + 9) // 12
        return f"{self.NOTES[note_index]}{octave}"

    def process_chunk(self, data):
        """Processes an audio chunk. Returns note, freq, and current volume."""
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(samples ** 2))

        # --- UPGRADE: Replace HPS with the more accurate YIN algorithm ---
        # The PYIN version is excellent as it provides voicing confidence.
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y=samples,
            fmin=librosa.note_to_hz('C2'),  # Start searching from C2
            fmax=librosa.note_to_hz('C7'),  # Search up to C7
            sr=self.RATE
        )

        # Filter for confident, voiced frequencies
        confident_f0 = f0[voiced_flag]

        if confident_f0.size == 0:
            return "---", 0.0, rms

        # Use the median of confident frequencies for stability
        dominant_freq = np.median(confident_f0)
        note_name = self.frequency_to_note(dominant_freq)

        return note_name, dominant_freq, rms

    def audio_processing_loop(self):
        """The main loop that will run in a separate thread."""
        self.stream = self.p.open(
            format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE,
            input=True, frames_per_buffer=self.CHUNK
        )
        self.is_running = True

        while self.is_running:
            try:
                current_threshold = self.volume_threshold_var.get()
                current_stability = self.stability_var.get()
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)

                note, freq, rms = self.process_chunk(data)
                self.current_volume = rms

                if rms > current_threshold and self.last_volume < current_threshold:
                    self.attack_rejection_counter = self.ATTACK_REJECTION_CHUNKS
                    self.note_history.clear()

                self.last_volume = rms

                if self.attack_rejection_counter > 0:
                    self.attack_rejection_counter -= 1
                    continue

                if rms > current_threshold:
                    self.note_history.append(note)
                    if len(self.note_history) > current_stability:
                        self.note_history = self.note_history[-current_stability:]

                    self.stable_note = max(set(self.note_history), key=self.note_history.count)
                    if self.stable_note != "---": self.stable_frequency = freq

            except (IOError, ValueError):
                continue

        if self.stream: self.stream.close()
        self.p.terminate()

    def stop(self):
        self.is_running = False


# --- The Final GUI (with your preferred defaults) ---
class NoteDetectorApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Piano Note Detector")
        self.root.geometry("500x550")
        self.root.configure(bg="#2c3e50")

        self.volume_threshold_var = tk.IntVar(value=40)
        self.stability_var = tk.IntVar(value=8)
        self.detector = NoteDetector(self.volume_threshold_var, self.stability_var)

        # GUI Setup... (This part is unchanged)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", troughcolor='#34495e', background='#2ecc71')
        style.configure("TScale", troughcolor='#34495e', background='#27ae60')
        style.configure("TLabelframe", background="#34495e", bordercolor="#34495e")
        style.configure("TLabelframe.Label", foreground="#ecf0f1", background="#34495e", font=("Helvetica", 11, "bold"))
        display_frame = tk.Frame(self.root, bg="#2c3e50")
        display_frame.pack(pady=20, fill='x', padx=20)
        self.note_label = tk.Label(display_frame, text="---", font=("Helvetica", 96, "bold"), fg="#ecf0f1",
                                   bg="#2c3e50")
        self.note_label.pack()
        self.freq_label = tk.Label(display_frame, text="Frequency: 0.00 Hz", font=("Helvetica", 16), fg="#bdc3c7",
                                   bg="#2c3e50")
        self.freq_label.pack(pady=5)
        volume_frame = ttk.Labelframe(self.root, text="Live Input Volume")
        volume_frame.pack(pady=10, padx=20, fill='x')
        self.volume_bar = ttk.Progressbar(volume_frame, length=300, mode='determinate', style="TProgressbar")
        self.volume_bar.pack(pady=10, padx=10)
        settings_frame = ttk.Labelframe(self.root, text="Tuning Controls")
        settings_frame.pack(pady=10, padx=20, fill='x')
        threshold_frame = tk.Frame(settings_frame, bg="#34495e")
        threshold_frame.pack(fill='x', padx=10, pady=(5, 0))
        tk.Label(threshold_frame, text="Volume Threshold", fg="#ecf0f1", bg="#34495e").pack(side=tk.LEFT)
        self.threshold_value_label = tk.Label(threshold_frame, text="40", fg="#ffffff", bg="#34495e",
                                              font=("Helvetica", 10, "bold"))
        self.threshold_value_label.pack(side=tk.RIGHT)
        ttk.Scale(settings_frame, from_=0, to=5000, orient='horizontal', variable=self.volume_threshold_var, length=400,
                  style="TScale").pack(pady=(0, 10), padx=10)
        stability_frame = tk.Frame(settings_frame, bg="#34495e")
        stability_frame.pack(fill='x', padx=10, pady=(5, 0))
        tk.Label(stability_frame, text="Detection Stability", fg="#ecf0f1", bg="#34495e").pack(side=tk.LEFT)
        self.stability_value_label = tk.Label(stability_frame, text="8", fg="#ffffff", bg="#34495e",
                                              font=("Helvetica", 10, "bold"))
        self.stability_value_label.pack(side=tk.RIGHT)
        tk.Label(settings_frame, text="(Higher = More Stable, Slower Response)", fg="#bdc3c7", bg="#34495e",
                 font=("Helvetica", 9)).pack()
        ttk.Scale(settings_frame, from_=1, to=20, orient='horizontal', variable=self.stability_var, length=400,
                  style="TScale").pack(pady=(0, 10), padx=10)

        self.thread = threading.Thread(target=self.detector.audio_processing_loop, daemon=True)
        self.thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_gui()

    def update_gui(self):
        self.note_label.config(text=self.detector.stable_note)
        freq_text = "---"
        if self.detector.stable_note != "---":
            self.freq_label.config(text=f"Frequency: {self.detector.stable_frequency:.2f} Hz")
        else:
            self.freq_label.config(text="Frequency: ---")

        max_volume = 15000
        self.volume_bar['value'] = (self.detector.current_volume / max_volume) * 100
        self.threshold_value_label.config(text=f"{self.volume_threshold_var.get()}")
        self.stability_value_label.config(text=f"{self.stability_var.get()}")
        self.root.after(50, self.update_gui)

    def on_closing(self):
        self.detector.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = NoteDetectorApp(root)
    root.mainloop()