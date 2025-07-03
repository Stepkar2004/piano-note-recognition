import music21
from collections import defaultdict
from src.core.sheet_music import SheetMusic, Note, Chord, Rest, Moment, MusicalEvent


class MusicXMLParser:
    """
    Parses a MusicXML file using a robust two-pass strategy to ensure
    correct timing and staff assignment for all notes.
    """

    def parse(self, file_path: str) -> SheetMusic:
        """
        Loads and parses a MusicXML file into a SheetMusic object.
        """
        try:
            score = music21.converter.parse(file_path)
        except Exception as e:
            print(f"Error parsing file with music21: {e}")
            return SheetMusic()

        # PASS 1: Create a reliable lookup table for absolute offsets.
        offset_map = {id(el): el.offset for el in score.flatten().notesAndRests}

        events_by_offset = defaultdict(list)

        # PASS 2: Iterate through the original structure to get correct staff context.
        for part in score.parts:
            # --- THE DEFINITIVE FIX ---
            # Search RECURSIVELY within the part to find the first clef.
            # This handles cases where the clef is nested inside a measure.
            clef = part.recurse().getElementsByClass('Clef').first()

            staff_type = 'bass' if clef and isinstance(clef, music21.clef.BassClef) else 'treble'

            for element in part.recurse().notesAndRests:
                offset = offset_map.get(id(element))
                if offset is None:
                    continue

                event: MusicalEvent

                if isinstance(element, music21.note.Note):
                    event = Note(
                        pitch=element.pitch.nameWithOctave,
                        duration=element.duration.quarterLength,
                        staff=staff_type
                    )
                elif isinstance(element, music21.chord.Chord):
                    chord_notes = [Note(p.nameWithOctave, element.duration.quarterLength, staff=staff_type) for p in
                                   element.pitches]
                    event = Chord(
                        notes=chord_notes,
                        duration=element.duration.quarterLength,
                        staff=staff_type
                    )
                elif isinstance(element, music21.note.Rest):
                    event = Rest(
                        duration=element.duration.quarterLength,
                        staff=staff_type
                    )
                else:
                    continue

                events_by_offset[offset].append(event)

        sorted_offsets = sorted(events_by_offset.keys())
        moments = [Moment(events=events_by_offset[offset], offset=offset) for offset in sorted_offsets]

        return SheetMusic(moments=moments)