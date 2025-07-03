from dataclasses import dataclass, field
from typing import List, Union

@dataclass
class Note:
    """Represents a single musical note."""
    pitch: str
    duration: float
    staff: str  # <-- ADDED: 'treble' or 'bass'

@dataclass
class Chord:
    """Represents multiple notes played at the same time in a single hand/staff."""
    notes: List[Note]
    duration: float
    staff: str  # <-- ADDED: 'treble' or 'bass'

@dataclass
class Rest:
    """Represents a period of silence."""
    duration: float
    staff: str  # <-- ADDED: 'treble' or 'bass'

MusicalEvent = Union[Note, Chord, Rest]

@dataclass
class Moment:
    """Represents a single point in time, containing all events that start at this offset."""
    events: List[MusicalEvent]
    offset: float

@dataclass
class SheetMusic:
    """Represents the entire piece of music as a sequence of Moments."""
    moments: List[Moment] = field(default_factory=list)