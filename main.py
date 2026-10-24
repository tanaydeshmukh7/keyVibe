import math
import os
import random
import struct
import sys
import tempfile
import time
import wave
from pathlib import Path

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget,
    QStyle, QSizePolicy, QFileDialog, QScrollArea
)
from pynput import keyboard
import pygame

APP_NAME = "KeyVibe"
APP_ORG = "NorthupStudio"
SAMPLE_RATE = 44100
PROFILES = ("Mechanical", "Soft", "Retro")


def make_click(path: Path, style: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    duration = {"Mechanical": 0.045, "Soft": 0.065, "Retro": 0.035}[style]
    count = int(SAMPLE_RATE * duration)
    rng = random.Random({"Mechanical": 19, "Soft": 23, "Retro": 29}[style])
    samples = []
    for i in range(count):
        t = i / SAMPLE_RATE
        envelope = math.exp(-t * {"Mechanical": 95, "Soft": 48, "Retro": 130}[style])
        noise = rng.uniform(-1, 1)
        if style == "Mechanical":
            tone = math.sin(2 * math.pi * 1750 * t) * 0.42 + math.sin(2 * math.pi * 3200 * t) * 0.18
            value = (noise * 0.55 + tone) * envelope
        elif style == "Soft":
            tone = math.sin(2 * math.pi * 950 * t) * 0.25
            value = (noise * 0.20 + tone) * envelope
        else:
            tone = math.sin(2 * math.pi * 1200 * t) * 0.45
            value = (noise * 0.35 + tone) * envelope
        samples.append(int(max(-1, min(1, value)) * 19000))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))


class KeyVibeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(APP_ORG, APP_NAME)
        self.enabled = self.settings.value("enabled", True, type=bool)
        self.sound_style = self.settings.value("sound_style", "Mechanical", type=str)
        if self.sound_style not in PROFILES:
            self.sound_style = "Mechanical"
        self.volume = self.settings.value("volume", 65, type=int)
        self.start_with_windows = self.settings.value("startup", False, type=bool)
        self.custom_sound_path = self.settings.value("custom_sound_path", "", type=str)
        self.click_duration_ms = self.settings.value("click_duration_ms", 80, type=int)
        self.last_sound_time = 0.0
        self.listener = None
        self.sound = None
        self.temp_dir = Path(tempfile.gettempdir()) / "KeyVibeSounds"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 256)
        pygame.mixer.init()
        self.load_sound()

        self.setWindowTitle("KeyVibe")
        self.setMinimumSize(580, 650)
        self.resize(640, 720)
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.build_ui()
        self.apply_settings()
        self.start_keyboard_listener()

    def build_ui(self):
        self.setStyleSheet("""
            QMainWindow { background: #F5F6FA; }
            QWidget { color: #202235; font-size: 10pt; }
            QLabel { background: transparent; }
            QLabel#muted { color: #73788C; }
            QLabel#eyebrow { color: #7650D5; font-size: 9pt; font-weight: 800; }
            QLabel#title { font-size: 28pt; font-weight: 800; color: #191A2A; }
            QLabel#section { font-size: 13pt; font-weight: 750; color: #222438; }
            QFrame#panel { background: #FFFFFF; border: 1px solid #E3E5EF; border-radius: 15px; }
            QFrame#panel QLabel { background: transparent; }
            QPushButton { background: #F1F1F8; color: #282A40; border: 1px solid #E0E1EC; border-radius: 9px; padding: 9px 12px; font-weight: 650; }
            QPushButton:hover { background: #E7E4F7; }
            QPushButton#primary { background: #7650D5; border: 1px solid #7650D5; color: white; }
            QPushButton#primary:hover { background: #6540C2; }
            QComboBox { background: #FFFFFF; border: 1px solid #DCDDEA; border-radius: 8px; padding: 7px 9px; min-width: 125px; min-height: 20px; }
            QComboBox QAbstractItemView { background: #FFFFFF; selection-background-color: #E9E2FC; color: #202235; }
            QSlider::groove:horizontal { height: 6px; background: #E0E1EC; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #9676E7; border-radius: 3px; }
            QSlider::handle:horizontal { background: #7650D5; width: 15px; margin: -5px 0; border-radius: 7px; }
            QCheckBox { spacing: 9px; color: #282A40; background: transparent; }
            QCheckBox::indicator { width: 18px; height: 18px; }
            QCheckBox::indicator:unchecked { background: #FFFFFF; border: 1px solid #C9CBDA; border-radius: 5px; }
            QCheckBox::indicator:checked { background: #7650D5; border: 1px solid #7650D5; border-radius: 5px; }
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        outer_layout.addWidget(scroll)
        self.setCentralWidget(outer)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        header.setSpacing(14)
        logo = QLabel("⌨")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(56, 56)
        logo.setStyleSheet("background:#7650D5; border-radius:15px; font-size:25pt; color:white;")
        header.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        eyebrow = QLabel("KEYBOARD SOUND STUDIO")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("KeyVibe")
        title.setObjectName("title")
        subtitle = QLabel("Give every keystroke a little character.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        title_col.addWidget(eyebrow)
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header.addLayout(title_col, 1)
        layout.addLayout(header)

        # Status panel
        self.status_panel = self.make_panel()
        status_layout = QHBoxLayout(self.status_panel)
        status_layout.setContentsMargins(16, 14, 16, 14)
        status_layout.setSpacing(12)
        status_col = QVBoxLayout()
        status_col.setSpacing(4)
        self.status_title = QLabel()
        self.status_title.setObjectName("section")
        self.status_subtitle = QLabel("Key events are processed locally on this computer.")
        self.status_subtitle.setObjectName("muted")
        self.status_subtitle.setWordWrap(True)
        status_col.addWidget(self.status_title)
        status_col.addWidget(self.status_subtitle)
        status_layout.addLayout(status_col, 1)
        self.toggle_btn = QPushButton()
        self.toggle_btn.setObjectName("primary")
        self.toggle_btn.setMinimumWidth(100)
        self.toggle_btn.clicked.connect(self.toggle_enabled)
        status_layout.addWidget(self.toggle_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.status_panel)

        # Sound settings
        sound_panel = self.make_panel()
        sound_layout = QVBoxLayout(sound_panel)
        sound_layout.setContentsMargins(16, 15, 16, 16)
        sound_layout.setSpacing(12)

        sound_head = QHBoxLayout()
        section = QLabel("Sound profile")
        section.setObjectName("section")
        sound_head.addWidget(section)
        sound_head.addStretch(1)
        self.upload_btn = QPushButton("＋ Upload")
        self.upload_btn.clicked.connect(self.upload_sound)
        sound_head.addWidget(self.upload_btn)
        self.test_btn = QPushButton("▶ Test")
        self.test_btn.clicked.connect(self.play_sound)
        sound_head.addWidget(self.test_btn)
        sound_layout.addLayout(sound_head)

        profile_row = QHBoxLayout()
        profile_row.setSpacing(12)
        profile_text = QVBoxLayout()
        profile_text.setSpacing(3)
        profile_label = QLabel("Keyboard sound")
        profile_label.setStyleSheet("font-weight:650;")
        profile_hint = QLabel("Choose a built-in profile")
        profile_hint.setObjectName("muted")
        profile_hint.setWordWrap(True)
        profile_text.addWidget(profile_label)
        profile_text.addWidget(profile_hint)
        profile_row.addLayout(profile_text, 1)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(PROFILES)
        self.profile_combo.setMinimumWidth(130)
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        profile_row.addWidget(self.profile_combo, 0, Qt.AlignmentFlag.AlignVCenter)
        sound_layout.addLayout(profile_row)

        self.sound_source_label = QLabel("Built-in sound")
        self.sound_source_label.setObjectName("muted")
        self.sound_source_label.setWordWrap(True)
        sound_layout.addWidget(self.sound_source_label)

        volume_head = QHBoxLayout()
        volume_label = QLabel("Master volume")
        volume_label.setStyleSheet("font-weight:650;")
        self.volume_value = QLabel()
        self.volume_value.setStyleSheet("color:#7650D5; font-weight:750;")
        volume_head.addWidget(volume_label)
        volume_head.addStretch(1)
        volume_head.addWidget(self.volume_value)
        sound_layout.addLayout(volume_head)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.valueChanged.connect(self.change_volume)
        sound_layout.addWidget(self.volume_slider)

        click_head = QHBoxLayout()
        click_label = QLabel("Key click length")
        click_label.setStyleSheet("font-weight:650;")
        self.click_value = QLabel()
        self.click_value.setStyleSheet("color:#7650D5; font-weight:750;")
        click_head.addWidget(click_label)
        click_head.addStretch(1)
        click_head.addWidget(self.click_value)
        sound_layout.addLayout(click_head)
        self.click_slider = QSlider(Qt.Orientation.Horizontal)
        self.click_slider.setRange(30, 300)
        self.click_slider.setSingleStep(10)
        self.click_slider.setPageStep(20)
        self.click_slider.valueChanged.connect(self.change_click_duration)
        sound_layout.addWidget(self.click_slider)
        click_hint = QLabel("Shorter clicks feel more natural for typing.")
        click_hint.setObjectName("muted")
        click_hint.setWordWrap(True)
        sound_layout.addWidget(click_hint)
        layout.addWidget(sound_panel)

        # Preferences
        options_panel = self.make_panel()
        options_layout = QVBoxLayout(options_panel)
        options_layout.setContentsMargins(16, 15, 16, 16)
        options_layout.setSpacing(10)
        options_title = QLabel("Preferences")
        options_title.setObjectName("section")
        options_layout.addWidget(options_title)
        self.startup_check = QCheckBox("Launch KeyVibe when Windows starts")
        self.startup_check.setToolTip("Adds or removes a launcher in your Windows Startup folder.")
        self.startup_check.toggled.connect(self.change_startup)
        options_layout.addWidget(self.startup_check)
        privacy = QLabel("Privacy: KeyVibe reacts to key events only. It does not save or transmit typed text.")
        privacy.setObjectName("muted")
        privacy.setWordWrap(True)
        options_layout.addWidget(privacy)
        layout.addWidget(options_panel)

        # Footer stays in the scrollable content so small windows never crop controls.
        footer = QHBoxLayout()
        self.footer_status = QLabel("Ready")
        self.footer_status.setObjectName("muted")
        self.footer_status.setWordWrap(True)
        footer.addWidget(self.footer_status, 1)
        quit_btn = QPushButton("Quit KeyVibe")
        quit_btn.clicked.connect(self.quit_app)
        footer.addWidget(quit_btn)
        layout.addLayout(footer)
        layout.addStretch(1)

    def make_panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        return panel

    def load_sound(self):
        custom_path = Path(self.custom_sound_path) if self.custom_sound_path else None
        if custom_path and custom_path.is_file():
            path = custom_path
        else:
            self.custom_sound_path = ""
            self.settings.setValue("custom_sound_path", "")
            path = self.temp_dir / (self.sound_style.lower() + ".wav")
            if not path.exists():
                make_click(path, self.sound_style)
        self.sound = self.load_trimmed_sound(path)
        self.sound.set_volume(self.volume / 100.0)

    def load_trimmed_sound(self, path):
        """Load audio and keep only the first click_duration_ms of PCM audio."""
        original = pygame.mixer.Sound(str(path))
        mixer_info = pygame.mixer.get_init()
        if not mixer_info:
            return original
        frequency, sample_format, channels = mixer_info
        bytes_per_sample = abs(sample_format) // 8
        bytes_per_frame = bytes_per_sample * channels
        target_frames = max(1, int(frequency * self.click_duration_ms / 1000))
        target_bytes = target_frames * bytes_per_frame
        raw = original.get_raw()
        if len(raw) <= target_bytes:
            return original
        # Align to full sample frames so pygame receives valid PCM data.
        target_bytes = (target_bytes // bytes_per_frame) * bytes_per_frame
        return pygame.mixer.Sound(buffer=raw[:target_bytes])

    def upload_sound(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Choose a keyboard sound",
            str(Path.home()),
            "Audio files (*.wav *.ogg *.mp3);;WAV files (*.wav);;OGG files (*.ogg);;MP3 files (*.mp3)"
        )
        if not filename:
            return
        try:
            new_sound = self.load_trimmed_sound(filename)
            new_sound.set_volume(self.volume / 100.0)
            self.custom_sound_path = filename
            self.settings.setValue("custom_sound_path", filename)
            self.sound = new_sound
            self.sound_source_label.setText(f"Custom sound: {Path(filename).name}")
            self.footer_status.setText("Custom sound loaded")
            self.sound.play()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Could not load sound",
                "Please choose a supported audio file (WAV or OGG recommended).\\n\\n" + str(exc)
            )

    def apply_settings(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.setCurrentText(self.sound_style)
        self.profile_combo.blockSignals(False)
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(self.volume)
        self.volume_slider.blockSignals(False)
        self.click_slider.blockSignals(True)
        self.click_slider.setValue(max(30, min(300, self.click_duration_ms)))
        self.click_slider.blockSignals(False)
        self.click_value.setText(f"{self.click_duration_ms} ms")
        self.startup_check.blockSignals(True)
        self.startup_check.setChecked(self.start_with_windows)
        self.startup_check.blockSignals(False)
        self.update_enabled_ui()
        self.volume_value.setText(f"{self.volume}%")
        if self.custom_sound_path and Path(self.custom_sound_path).is_file():
            self.sound_source_label.setText(f"Custom sound: {Path(self.custom_sound_path).name}")
        else:
            self.sound_source_label.setText("Built-in sound")
        self.update_startup_entry()

    def update_enabled_ui(self):
        self.status_title.setText("Keyboard sounds are ON" if self.enabled else "Keyboard sounds are OFF")
        self.status_title.setStyleSheet("color:#16845B;" if self.enabled else "color:#C2414B;")
        self.toggle_btn.setText("Turn off" if self.enabled else "Turn on")
        self.footer_status.setText("Listening for key presses" if self.enabled else "Sound playback paused")

    def start_keyboard_listener(self):
        try:
            self.listener = keyboard.Listener(on_press=self.on_key_press)
            self.listener.daemon = True
            self.listener.start()
        except Exception as exc:
            QMessageBox.warning(self, "Keyboard listener unavailable", f"Could not start global keyboard detection.\n\n{exc}")

    def on_key_press(self, key):
        now = time.monotonic()
        if not self.enabled or now - self.last_sound_time < 0.018:
            return
        self.last_sound_time = now
        try:
            sound = self.sound
            if sound is not None and self.volume > 0:
                sound.play()
        except Exception:
            pass

    def play_sound(self):
        try:
            if self.sound:
                self.sound.play()
                self.footer_status.setText(f"Previewing {self.sound_style.lower()} sound")
        except Exception as exc:
            QMessageBox.warning(self, "Audio error", str(exc))

    def toggle_enabled(self):
        self.enabled = not self.enabled
        self.settings.setValue("enabled", self.enabled)
        self.update_enabled_ui()

    def change_profile(self, value):
        if value not in PROFILES:
            return
        self.sound_style = value
        self.custom_sound_path = ""
        self.settings.setValue("custom_sound_path", "")
        self.settings.setValue("sound_style", value)
        try:
            self.load_sound()
            self.sound_source_label.setText("Built-in sound")
            self.footer_status.setText(f"Sound profile: {value}")
        except Exception as exc:
            QMessageBox.warning(self, "Sound error", str(exc))

    def change_click_duration(self, value):
        self.click_duration_ms = value
        self.click_value.setText(f"{value} ms")
        self.settings.setValue("click_duration_ms", value)
        try:
            if self.custom_sound_path and Path(self.custom_sound_path).is_file():
                self.sound = self.load_trimmed_sound(self.custom_sound_path)
            else:
                self.sound = self.load_trimmed_sound(
                    self.temp_dir / (self.sound_style.lower() + ".wav")
                )
            self.sound.set_volume(self.volume / 100.0)
            self.footer_status.setText(f"Key click length: {value} ms")
        except Exception as exc:
            QMessageBox.warning(self, "Sound error", str(exc))

    def change_volume(self, value):
        self.volume = value
        self.volume_value.setText(f"{value}%")
        self.settings.setValue("volume", value)
        try:
            if self.sound:
                self.sound.set_volume(value / 100.0)
        except Exception:
            pass

    def startup_script_path(self):
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "KeyVibe.bat"

    def update_startup_entry(self):
        path = self.startup_script_path()
        if path is None:
            return
        if self.start_with_windows:
            path.parent.mkdir(parents=True, exist_ok=True)
            if getattr(sys, "frozen", False):
                command = f'start "" "{Path(sys.executable).resolve()}"'
            else:
                script = Path(__file__).resolve()
                python = Path(sys.executable).resolve()
                pythonw = python.with_name("pythonw.exe")
                interpreter = pythonw if pythonw.exists() else python
                command = f'start "" "{interpreter}" "{script}"'
            path.write_text("@echo off\r\n" + command + "\r\n", encoding="utf-8")
        elif path.exists():
            path.unlink()

    def change_startup(self, checked):
        previous = self.start_with_windows
        self.start_with_windows = checked
        try:
            self.update_startup_entry()
            self.settings.setValue("startup", checked)
            self.footer_status.setText("Windows startup enabled" if checked else "Windows startup disabled")
        except Exception as exc:
            self.start_with_windows = previous
            self.startup_check.blockSignals(True)
            self.startup_check.setChecked(previous)
            self.startup_check.blockSignals(False)
            QMessageBox.warning(self, "Startup setting failed", str(exc))

    def quit_app(self):
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
        try:
            pygame.mixer.quit()
            pygame.quit()
        except Exception:
            pass
        QApplication.quit()

    def closeEvent(self, event):
        self.quit_app()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    window = KeyVibeWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
