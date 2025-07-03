import music21
from src.core.sheet_music import SheetMusic, Note, Chord


class PracticeEngine:
    def __init__(self):
        self.sheet_music: SheetMusic | None = None
        self.current_moment_index: int = 0
        self.is_listening: bool = False

    def load_sheet_music(self, sheet_music: SheetMusic):
        self.sheet_music = sheet_music
        self.current_moment_index = 0

    def get_current_target_notes(self) -> set[str]:
        if not self.sheet_music or not self.sheet_music.moments: return set()
        target_notes = set()
        current_moment = self.sheet_music.moments[self.current_moment_index]
        for event in current_moment.events:
            if isinstance(event, Note):
                target_notes.add(event.pitch)
            elif isinstance(event, Chord):
                for note in event.notes:
                    target_notes.add(note.pitch)
        return target_notes

    def check_single_note(self, played_note_str: str) -> bool:
        """
        Performs a a strict, octave-correct check for single notes.
        This is the method for the single-note detector.
        """
        target_notes = self.get_current_target_notes()
        if len(target_notes) != 1: return False

        # A simple, direct, and strict comparison.
        if played_note_str in target_notes:
            print(f"Correct (Single Note)! Played: {played_note_str}, Target was: {target_notes}")
            self.go_to_next_moment()
            return True

        return False

    def advance_after_chord(self):
        """Called by the AppView when the chord detector confirms a correct chord."""
        print("Correct (Chord)! Advancing.")
        self.go_to_next_moment()

    def go_to_next_moment(self):
        if not self.sheet_music: return
        if self.current_moment_index < len(self.sheet_music.moments) - 1:
            self.current_moment_index += 1

    def go_to_previous_moment(self):
        if not self.sheet_music: return
        if self.current_moment_index > 0:
            self.current_moment_index -= 1

    def restart(self):
        self.current_moment_index = 0

    def set_moment(self, index: int):
        if not self.sheet_music: return
        if 0 <= index < len(self.sheet_music.moments):
            self.current_moment_index = index