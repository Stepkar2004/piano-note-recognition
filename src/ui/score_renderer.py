import os
import music21
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse, InstructionGroup, Rectangle
from kivy.core.image import Image as CoreImage
from kivy.properties import ObjectProperty, NumericProperty, StringProperty
from kivy.event import EventDispatcher

from src.core.sheet_music import SheetMusic, Note, Chord

DIATONIC_PITCH_STEPS = {'C': 0, 'D': 1, 'E': 2, 'F': 3, 'G': 4, 'A': 5, 'B': 6}


class ScoreRenderer(Widget, EventDispatcher):
    sheet_music = ObjectProperty(None, allownone=True)
    minimum_height = NumericProperty(0)
    STAFF_SEPARATION = 130
    cursor_index = NumericProperty(0)

    # --- NEW: Property to hold the wrong note to draw ---
    # It will be a string like 'C#4'. We bind it to the redraw method.
    wrong_note_to_draw = StringProperty(None, allownone=True)

    __events__ = ('on_moment_select',)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.moment_hitboxes = []
        # --- NEW: Bind the new property to the redraw method ---
        self.bind(sheet_music=self.draw_score, size=self.draw_score, pos=self.draw_score,
                  cursor_index=self.draw_score, wrong_note_to_draw=self.draw_score)

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        assets_path = os.path.join(base_dir, 'assets')
        self.treble_clef_texture = CoreImage(os.path.join(assets_path, 'treble_clef.png')).texture
        self.bass_clef_texture = CoreImage(os.path.join(assets_path, 'bass_clef.png')).texture
        self.sharp_texture = CoreImage(os.path.join(assets_path, 'sharp_symbol.png')).texture
        self.flat_texture = CoreImage(os.path.join(assets_path, 'flat_symbol.png')).texture

        self.note_instructions = InstructionGroup()
        self.canvas.add(self.note_instructions)

    def on_moment_select(self, moment_index: int):
        pass

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            local_pos = self.to_local(*touch.pos)
            for hitbox, index in self.moment_hitboxes:
                if hitbox.collide_point(*local_pos):
                    self.dispatch('on_moment_select', index)
                    return True
        return super().on_touch_down(touch)

    def _draw_grand_staff_system(self, y_pos, staff_line_spacing):
        # This method remains the same
        system_group = InstructionGroup()
        system_group.add(Color(0, 0, 0, 1))
        treble_y_base = y_pos
        for i in range(5):
            y = treble_y_base + i * staff_line_spacing
            system_group.add(Line(points=[10, y, self.width - 10, y], width=1))

        clef_height = staff_line_spacing * 7
        clef_width = clef_height * (self.treble_clef_texture.width / self.treble_clef_texture.height)
        system_group.add(Rectangle(texture=self.treble_clef_texture, pos=(15, treble_y_base - staff_line_spacing),
                                   size=(clef_width, clef_height)))

        bass_y_base = y_pos - self.STAFF_SEPARATION
        for i in range(5):
            y = bass_y_base + i * staff_line_spacing
            system_group.add(Line(points=[10, y, self.width - 10, y], width=1))

        clef_height = staff_line_spacing * 4
        clef_width = clef_height * (self.bass_clef_texture.width / self.bass_clef_texture.height)
        system_group.add(Rectangle(texture=self.bass_clef_texture, pos=(15, bass_y_base + staff_line_spacing / 2),
                                   size=(clef_width, clef_height)))

        system_group.add(Line(points=[10, bass_y_base, 10, treble_y_base + (staff_line_spacing * 4)], width=2))
        return system_group

    def draw_score(self, *args):
        self.note_instructions.clear()
        self.moment_hitboxes.clear()

        if not self.sheet_music or not self.sheet_music.moments or self.width <= 100:
            self.minimum_height = self.height
            return

        STAFF_LINE_SPACING = 15
        NOTE_HEAD_DIAMETER = 14
        STEP_HEIGHT = STAFF_LINE_SPACING / 2
        LEFT_MARGIN = 80
        RIGHT_MARGIN = 30
        SYSTEM_SPACING = 250

        current_x = LEFT_MARGIN
        current_system_y = self.height - 100
        num_systems = 1

        self.note_instructions.add(self._draw_grand_staff_system(current_system_y, STAFF_LINE_SPACING))

        for i, moment in enumerate(self.sheet_music.moments):
            first_event = moment.events[0]
            moment_width = first_event.duration * 40 + 25

            if current_x + moment_width > self.width - RIGHT_MARGIN:
                current_x = LEFT_MARGIN
                current_system_y -= SYSTEM_SPACING
                num_systems += 1
                self.note_instructions.add(self._draw_grand_staff_system(current_system_y, STAFF_LINE_SPACING))

            cursor_y = current_system_y - self.STAFF_SEPARATION - (STAFF_LINE_SPACING * 2)
            cursor_height = self.STAFF_SEPARATION + (STAFF_LINE_SPACING * 6)

            hitbox = Widget(pos=(current_x, cursor_y), size=(moment_width, cursor_height))
            self.moment_hitboxes.append((hitbox, i))

            if i == self.cursor_index:
                # Draw the blue cursor
                cursor_width = 20
                cursor_x = current_x + (NOTE_HEAD_DIAMETER / 2) - (cursor_width / 2)
                self.note_instructions.add(Color(0, 0.5, 1, 0.5))
                self.note_instructions.add(Rectangle(pos=(cursor_x, cursor_y), size=(cursor_width, cursor_height)))

                # --- NEW: Draw the red "wrong note" if it exists ---
                if self.wrong_note_to_draw:
                    # Create a temporary Note object to pass to our drawing function
                    temp_note = Note(pitch=self.wrong_note_to_draw, duration=0, staff='treble')
                    # We draw it at the same horizontal position as the cursor
                    self._draw_note(temp_note, current_x, current_system_y, STEP_HEIGHT, NOTE_HEAD_DIAMETER,
                                    is_wrong=True)

            # Draw the actual black notes from the score
            for event in moment.events:
                notes_to_draw = event.notes if isinstance(event, Chord) else [event]
                for note in notes_to_draw:
                    if isinstance(note, Note):
                        self._draw_note(note, current_x, current_system_y, STEP_HEIGHT, NOTE_HEAD_DIAMETER)

            current_x += moment_width

        self.minimum_height = num_systems * SYSTEM_SPACING

    def _draw_note(self, note, x, system_y_base, step_height, diameter, is_wrong=False):
        try:
            p = music21.pitch.Pitch(note.pitch)
        except music21.pitch.PitchException:
            return

        if note.staff == 'treble':
            staff_y_base = system_y_base
            ref_step = DIATONIC_PITCH_STEPS['E'] + 4 * 7
        else:
            staff_y_base = system_y_base - self.STAFF_SEPARATION
            ref_step = DIATONIC_PITCH_STEPS['G'] + 2 * 7

        total_steps = DIATONIC_PITCH_STEPS[p.step] + p.octave * 7
        relative_steps = total_steps - ref_step
        y = staff_y_base + (relative_steps * step_height) - (diameter / 2)

        # --- NEW: Set color based on whether the note is wrong ---
        if is_wrong:
            self.note_instructions.add(Color(1, 0, 0, 0.8))  # Red and slightly transparent
        else:
            self.note_instructions.add(Color(0, 0, 0, 1))  # Black

        self.note_instructions.add(Ellipse(pos=(x, y), size=(diameter, diameter)))

        # Don't draw ledger lines or accidentals for temporary wrong notes
        if is_wrong:
            return

        # Ledger Line Logic
        if relative_steps > 8:
            for i in range(10, int(relative_steps) + 1, 2):
                ledger_y = staff_y_base + (i * step_height)
                self.note_instructions.add(Line(points=[x - 5, ledger_y, x + diameter + 5, ledger_y], width=1.5))
        if relative_steps < 0:
            for i in range(-2, int(relative_steps) - 1, -2):
                ledger_y = staff_y_base + (i * step_height)
                self.note_instructions.add(Line(points=[x - 5, ledger_y, x + diameter + 5, ledger_y], width=1.5))

        # Accidental Logic
        if p.accidental:
            accidental_texture = None
            if p.accidental.name == 'sharp':
                accidental_texture = self.sharp_texture
            elif p.accidental.name == 'flat':
                accidental_texture = self.flat_texture
            if accidental_texture:
                acc_height = diameter * 1.8
                acc_width = acc_height * (accidental_texture.width / accidental_texture.height)
                self.note_instructions.add(Rectangle(texture=accidental_texture,
                                                     pos=(x - diameter * 1.5, y - diameter * 0.4),
                                                     size=(acc_width, acc_height)))