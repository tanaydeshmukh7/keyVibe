# KeyVibe

KeyVibe is a lightweight Windows desktop application that adds customizable
sound effects to keyboard presses. It runs in the background, listens for
global key events, and plays a short sound for each keystroke without saving
or transmitting the text that was typed.

The application includes built-in keyboard sound profiles, custom sound
uploads, volume control, click-length control, a Windows startup option, and a
simple responsive interface.

## Features

- Global keyboard sound playback while KeyVibe is running.
- Three generated built-in sound profiles:
  - **Mechanical**
  - **Soft**
  - **Retro**
- Custom sound upload support for:
  - WAV
  - OGG
  - MP3
- Master volume control from 0% to 100%.
- Key click length control from 30 ms to 300 ms.
- Test button for previewing the current sound.
- One-click enable/disable control.
- Optional launch at Windows startup.
- Persistent settings between launches.
- Responsive, scrollable PySide6 interface.
- Local-only processing: typed text is not stored or transmitted.

## How It Works

1. KeyVibe starts a PySide6 desktop window.
2. A background `pynput` keyboard listener watches for key press events.
3. When a key is pressed, KeyVibe plays the currently selected sound through
   `pygame`.
4. A short debounce interval prevents excessive overlapping playback during
   very rapid key presses.
5. Settings such as the enabled state, selected profile, volume, click length,
   custom sound path, and startup preference are saved using Qt
   `QSettings`.

KeyVibe reacts to key events only. It does not record, display, save, or send
the actual typed text.

## Requirements

- Windows 10 or later.
- Python 3.10 or newer recommended.
- A working audio output device.
- Permission to install Python packages.

The project currently targets Windows because its optional startup integration
creates a `.bat` launcher in the Windows Startup folder.

## Setup

### 1. Clone the repository

```powershell
git clone https://github.com/tanaydeshmukh7/keyVibe.git
cd keyVibe
```

### 2. Create a virtual environment

```powershell
py -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script activation, either allow locally created scripts
for the current user or activate the environment from Command Prompt:

```bat
.venv\Scripts\activate.bat
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install PySide6 pynput pygame
```

To build a standalone Windows executable, also install PyInstaller:

```powershell
python -m pip install pyinstaller
```

## Running the Application

With the virtual environment activated, run:

```powershell
python main.py
```

The KeyVibe window opens and starts listening for keyboard input immediately.
Keep the application running while you want keyboard sounds to play.

## Using KeyVibe

### Enable or disable sounds

Use the button in the status panel to turn keyboard sound playback on or off.
Disabling playback does not close the application or stop the keyboard listener.

### Select a sound profile

Choose **Mechanical**, **Soft**, or **Retro** from the **Sound profile**
selector. Built-in WAV files are generated automatically in the system
temporary directory the first time they are needed.

### Upload a custom sound

Select **Upload**, choose a supported audio file, and KeyVibe will use it for
future key presses. The sound is trimmed to the selected click length.

Changing back to a built-in profile clears the selected custom sound.

### Adjust volume and click length

- **Master volume** controls playback volume from 0% to 100%.
- **Key click length** controls how much of the selected audio is played,
  from 30 ms to 300 ms.

Use **Test** to preview the current sound.

### Launch with Windows

Enable **Launch KeyVibe when Windows starts** to create:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KeyVibe.bat
```

Disable the option to remove that launcher.

## Building a Standalone Executable

After installing PyInstaller, build the application with the included
specification:

```powershell
pyinstaller KeyVibe.spec
```

The executable is generated under:

```text
dist\KeyVibe.exe
```

The spec file creates a windowed executable without a console window and
collects the required PySide6 runtime files.

To run the built application:

```powershell
.\dist\KeyVibe.exe
```

## Project Structure

```text
KeyVibe/
├── .gitignore       # Excludes virtual environments and generated files
├── KeyVibe.spec     # PyInstaller build configuration
├── README.md        # Project documentation
└── main.py          # Application UI, settings, keyboard listener, and audio logic
```

Generated or local-only directories are intentionally not committed:

```text
.venv/               # Python virtual environment
.venv313/            # Alternate local virtual environment
build/               # PyInstaller temporary build files
dist/                # Built executable output
__pycache__/          # Python bytecode cache
```

## Main Components in `main.py`

| Component | Responsibility |
| --- | --- |
| `make_click()` | Generates the built-in PCM WAV profiles |
| `KeyVibeWindow` | Builds and controls the desktop interface |
| `load_sound()` | Loads a custom or generated sound |
| `load_trimmed_sound()` | Limits audio playback to the configured click length |
| `start_keyboard_listener()` | Starts global keyboard event monitoring |
| `on_key_press()` | Plays the current sound for each accepted key press |
| `update_startup_entry()` | Adds or removes the Windows startup launcher |
| `main()` | Creates the Qt application and starts the event loop |

## Settings and Local Files

KeyVibe stores preferences through Qt `QSettings` using:

```text
Organization: NorthupStudio
Application:  KeyVibe
```

The following preferences are persisted:

- Whether keyboard sounds are enabled.
- Selected built-in sound profile.
- Master volume.
- Key click length.
- Custom sound file path.
- Windows startup preference.

Generated built-in sounds are stored temporarily under:

```text
%TEMP%\KeyVibeSounds\
```

## Troubleshooting

### No sound is playing

1. Confirm the status says **Keyboard sounds are ON**.
2. Check that the master volume is above 0%.
3. Click **Test** to check the selected audio.
4. Confirm Windows has an active output device and the volume is not muted.
5. Restart KeyVibe if another application changed the audio device.

### The keyboard listener cannot start

Close other keyboard-hooking utilities temporarily and restart KeyVibe. Some
security tools may restrict global keyboard listeners. KeyVibe does not need
the typed text, but Windows or security software may still require permission
for global key event monitoring.

### A custom sound cannot be loaded

Use a valid WAV, OGG, or MP3 file. WAV or OGG is recommended for the most
consistent compatibility. The file must be readable by the current user.

### Startup launch does not work

Verify that the startup checkbox is enabled and that this folder exists:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
```

If the application is run from a virtual environment, the generated launcher
uses the available Python interpreter. If it is packaged, it uses the built
executable.

## Development Notes

- Audio is initialized at 44,100 Hz, 16-bit, mono.
- Built-in sounds are generated deterministically from fixed random seeds.
- Playback is limited to one sound object using the configured volume.
- Key events are rate-limited by a short 18 ms interval.
- The application cleans up the keyboard listener and audio mixer on exit.

## Privacy

KeyVibe is designed for local keyboard sound effects. It does not save or
transmit typed text, and it does not require an internet connection while
running.

## License

No license has been added to this repository yet. Add a license file before
redistributing the project or accepting external contributions under a
specific open-source license.
