from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle


class ChordDisplayWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 150
        self.spacing = 10
        self.padding = 10

        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 0.95)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        self.status_label = Label(text="...", font_size='20sp', bold=True)
        self.notes_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=2)

        self.add_widget(self.status_label)
        self.add_widget(self.notes_layout)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def update_display(self, target_notes: set, found_notes: dict, is_correct: bool, is_listening: bool):
        """Rebuilds the display with the latest detection state."""
        # --- NEW: More informative status logic ---
        if not is_listening:
            self.status_label.text = "Mic is Off"
            self.status_label.color = (0.7, 0.7, 0.7, 1)  # Grey
        elif is_correct:
            self.status_label.text = "Correct!"
            self.status_label.color = (0.1, 1, 0.1, 1)  # Green
        else:
            self.status_label.text = "Listening..."
            self.status_label.color = (1, 1, 1, 1)  # White

        self.notes_layout.clear_widgets()

        if not target_notes:
            # Handle rests gracefully
            self.notes_layout.add_widget(Label(text="Rest", font_size='30sp', color=(0.5, 0.5, 0.5, 1)))
            return

        sorted_target_notes = sorted(list(target_notes))

        for note in sorted_target_notes:
            is_found = found_notes.get(note, False)
            color = (0.1, 1, 0.1, 1) if is_found else (0.5, 0.5, 0.5, 1)

            note_label = Label(text=note, font_size='30sp', bold=True, color=color)
            self.notes_layout.add_widget(note_label)