# Piano Note Recognition

This project is a real-time piano note recognition application designed to help users practice playing the piano. It visually displays sheet music from a MusicXML file and provides instant feedback by listening to the user play on a piano. The application can distinguish between single notes and chords, offering a comprehensive practice experience.

## Features

- **Sheet Music Display**: Loads and renders sheet music from MusicXML (.mxl, .xml) files.
- **Real-time Note Recognition**: Listens to your piano playing through a microphone and identifies the notes being played.
- **Two Recognition Modes**:
    - **Single Note Mode**: For passages with individual notes, the application listens for one note at a time.
    - **Chord Mode**: For chords (two or more notes played simultaneously), the application listens for all the notes in the chord.
- **Interactive Practice**: The sheet music display advances automatically as you play the correct notes or chords.
- **User-Friendly Interface**: A simple interface built with Kivy allows you to load different pieces of music, control the practice session (play, pause, restart), and view the notes being detected in real-time.

## How It Works

The application is built in Python and uses a combination of libraries to achieve its functionality:

- **User Interface**: The graphical user interface is built using the [Kivy](https://kivy.org/) framework.
- **MusicXML Parsing**: The [music21](http://web.mit.edu/music21/) library is used to parse and interpret the MusicXML files, extracting the notes, chords, and other musical information.
- **Audio Input and Pitch Detection**: The [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) and [aubio](https://aubio.org/) libraries are used to capture audio from the microphone and perform real-time pitch detection.
- **Practice Logic**: A custom practice engine manages the user's progress through the sheet music, comparing the detected notes with the expected notes and advancing the music accordingly.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/piano-note-recognition.git
   cd piano-note-recognition
   ```

2. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the application:**
   ```bash
   python main.py
   ```

2. **Load a MusicXML file:**
   - The application will start with a sample MusicXML file loaded.
   - To load your own file, enter the path to the file in the text box at the top of the window and click "Load Score".

3. **Start practicing:**
   - Click the "Mic On" button to start the note recognition.
   - Play the notes on your piano as they appear on the sheet music.
   - The application will highlight the current note or chord and advance as you play correctly.

## Future Improvements

- **MIDI Input**: In addition to microphone input, the application could be extended to support MIDI keyboards for more accurate note detection.
- **More Advanced Feedback**: The application could provide more detailed feedback on the user's playing, such as timing and rhythm accuracy.
- **Wider Range of Musical Notation**: The application could be improved to support a wider range of musical notation, such as grace notes, trills, and other ornaments.
