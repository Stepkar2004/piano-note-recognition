import os
import queue
import time
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock

from src.parsing.musicxml_parser import MusicXMLParser
from src.core.practice_engine import PracticeEngine
from src.input.mic_listener import MicListener  # <-- We need this again
from src.input.chord_detector import ChordDetector
from src.ui.score_renderer import ScoreRenderer
from src.ui.chord_display import ChordDisplayWidget

try:
    import tkinter as tk
    from tkinter import filedialog

    root_tk = tk.Tk()
    root_tk.withdraw()
    FILE_BROWSER_AVAILABLE = True
except ImportError:
    FILE_BROWSER_AVAILABLE = False


class PianoTutorApp(App):
    def build(self):
        self.title = "Piano Tutor"
        Window.clearcolor = (1, 1, 1, 1)
        self.parser = MusicXMLParser()
        self.engine = PracticeEngine()

        # --- NEW: We have two queues and two detectors again ---
        self.single_note_queue = queue.Queue()
        self.mic_listener = MicListener(self.single_note_queue)

        self.chord_detector_queue = queue.Queue()
        self.chord_detector = ChordDetector(self.chord_detector_queue)
        self.active_detector = 'none'

        self.show_detector_panel = True
        self.last_correct_time = 0
        self.DETECTOR_COOLDOWN = 0.25

        # --- UI Setup ---
        root_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        top_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        self.path_input = TextInput(text="assets/sample.mxl", multiline=False)
        load_button = Button(text="Load Score", size_hint_x=0.3);
        load_button.bind(on_press=self.load_score_from_path)
        top_bar.add_widget(self.path_input)
        if FILE_BROWSER_AVAILABLE:
            browse_button = Button(text="Browse...", size_hint_x=0.2);
            browse_button.bind(on_press=self.browse_for_file)
            top_bar.add_widget(browse_button)
        top_bar.add_widget(load_button)

        scroll_container = ScrollView(do_scroll_x=False)
        self.score_renderer = ScoreRenderer(size_hint_y=None)
        self.score_renderer.bind(minimum_height=self.score_renderer.setter('height'))
        self.score_renderer.bind(on_moment_select=self.on_score_click)
        scroll_container.add_widget(self.score_renderer)

        self.bottom_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        self.chord_display_widget = ChordDisplayWidget()

        root_layout.add_widget(top_bar);
        root_layout.add_widget(scroll_container);
        root_layout.add_widget(self.bottom_bar)

        Clock.schedule_interval(self.check_for_updates, 1.0 / 30.0)
        return root_layout

    def on_stop(self):
        self.mic_listener.stop()
        self.chord_detector.stop()

    def check_for_updates(self, dt):
        """Checks the queue of the currently active detector."""
        if not self.engine.is_listening or (time.time() - self.last_correct_time < self.DETECTOR_COOLDOWN):
            return  # Implement cooldown by simply not checking queues

        # --- RESTORED: Hybrid logic to check the correct queue ---
        if self.active_detector == 'single':
            self.check_single_note_detector()
        elif self.active_detector == 'chord':
            self.check_chord_detector()

    def check_single_note_detector(self):
        try:
            note_name = self.single_note_queue.get_nowait()
            was_correct = self.engine.check_single_note(note_name)
            if was_correct:
                self.last_correct_time = time.time()
                self.update_score_and_detector()
            else:
                # Update the display panel to show the wrong note
                if self.chord_display_widget.parent:
                    target_notes = self.engine.get_current_target_notes()
                    self.chord_display_widget.update_display(target_notes, {note_name: True}, False, True)

        except queue.Empty:
            # If nothing is played, ensure the display is up-to-date
            if self.chord_display_widget.parent:
                target_notes = self.engine.get_current_target_notes()
                self.chord_display_widget.update_display(target_notes, {}, False, True)

    def check_chord_detector(self):
        try:
            detector_state = self.chord_detector_queue.get_nowait()
            target_notes = self.engine.get_current_target_notes()

            # --- FIX for flickering ---
            # We only update the visual display if the panel is actually visible
            if self.chord_display_widget.parent:
                self.chord_display_widget.update_display(
                    target_notes, detector_state['found_notes'], detector_state['is_correct'], True
                )

            if detector_state.get('is_correct', False):
                self.engine.advance_after_chord()
                self.last_correct_time = time.time()
                self.update_score_and_detector()
        except queue.Empty:
            pass

    def toggle_mic(self, instance):
        if instance.state == 'down':
            instance.text = "Mic ON"
            self.engine.is_listening = True
            self.update_detector_mode()
        else:
            instance.text = "Mic Off"
            self.engine.is_listening = False
            self.stop_all_detectors()
            if self.chord_display_widget.parent:
                self.chord_display_widget.update_display(set(), {}, False, False)

    def toggle_display_panel(self, instance):
        self.show_detector_panel = instance.state == 'down'
        if self.show_detector_panel and not self.chord_display_widget.parent:
            self.root.add_widget(self.chord_display_widget, index=0)
            instance.text = "Hide Panel"
        elif not self.show_detector_panel and self.chord_display_widget.parent:
            self.root.remove_widget(self.chord_display_widget)
            instance.text = "Show Panel"

    def update_detector_mode(self):
        """The core of the hybrid logic. Checks the target and starts the correct detector."""
        self.stop_all_detectors()

        target_notes = self.engine.get_current_target_notes()
        num_notes = len(target_notes)

        if num_notes == 1:
            print("==> HYBRID MODE: Activating SINGLE note detector.")
            self.active_detector = 'single'
            self.mic_listener.start()
        elif num_notes > 1:
            print(f"==> HYBRID MODE: Activating CHORD detector for {num_notes} notes.")
            self.active_detector = 'chord'
            self.chord_detector.set_target_notes(target_notes)
            self.chord_detector.start()
        else:
            print("==> HYBRID MODE: It's a rest. No detector active.")
            self.active_detector = 'none'

    def stop_all_detectors(self):
        """Stops both detectors and clears their queues."""
        self.mic_listener.stop()
        self.chord_detector.stop()
        while not self.single_note_queue.empty(): self.single_note_queue.get()
        while not self.chord_detector_queue.empty(): self.chord_detector_queue.get()

    def update_score_and_detector(self):
        """Helper to update the score view and then switch detector mode."""
        self.update_score_view()
        if self.engine.is_listening:
            self.update_detector_mode()

    # --- Other methods remain the same ---
    def load_score_from_path(self, instance):
        path = self.path_input.text
        if not os.path.exists(path): return
        sheet_music = self.parser.parse(path)
        if not sheet_music or not sheet_music.moments: return
        self.engine.load_sheet_music(sheet_music)
        self.update_score_view()
        self.update_ui_controls()

    def update_ui_controls(self):
        self.bottom_bar.clear_widgets()
        if self.engine.sheet_music:
            restart_button = Button(text="Restart");
            restart_button.bind(on_press=self.restart_piece)
            prev_button = Button(text="<|");
            prev_button.bind(on_press=self.go_to_previous_moment)
            next_button = Button(text="|>");
            next_button.bind(on_press=self.go_to_next_moment)
            display_toggle = ToggleButton(text="Hide Panel", state='down', group='display_toggle')
            display_toggle.bind(on_press=self.toggle_display_panel)
            mic_button = ToggleButton(text="Mic Off", group='mic_toggle');
            mic_button.bind(on_press=self.toggle_mic)
            self.bottom_bar.add_widget(Label());
            self.bottom_bar.add_widget(restart_button);
            self.bottom_bar.add_widget(prev_button);
            self.bottom_bar.add_widget(next_button);
            self.bottom_bar.add_widget(display_toggle);
            self.bottom_bar.add_widget(mic_button);
            self.bottom_bar.add_widget(Label())
            if self.show_detector_panel and not self.chord_display_widget.parent:
                self.root.add_widget(self.chord_display_widget, index=0)

    def on_score_click(self, renderer_instance, moment_index: int):
        self.engine.set_moment(moment_index)
        self.update_score_and_detector()

    def restart_piece(self, instance):
        self.engine.restart()
        self.update_score_and_detector()

    def go_to_previous_moment(self, instance):
        self.engine.go_to_previous_moment()
        self.update_score_and_detector()

    def go_to_next_moment(self, instance):
        self.engine.go_to_next_moment()
        self.update_score_and_detector()

    def browse_for_file(self, instance):
        file_path = filedialog.askopenfilename(title="Select a MusicXML file", filetypes=(
        ("MusicXML files", "*.musicxml *.mxl *.xml"), ("All files", "*.*")))
        if file_path: self.path_input.text = file_path

    def update_score_view(self):
        self.score_renderer.sheet_music = self.engine.sheet_music
        self.score_renderer.cursor_index = self.engine.current_moment_index
        if self.score_renderer.parent and self.engine.current_moment_index == 0: self.root._trigger_layout()