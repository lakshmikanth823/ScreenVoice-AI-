"""
app_gui.py - CustomTkinter Desktop Application for GameVocalize
Provides a dark modern desktop interface with controls, settings, live text log, ROI selection,
Movie & Video Subtitle Mode (Ultra-Fast 80ms live reader), Story Game Mode, and Sweet Female / Male Voice Selection.
"""

import logging
import threading
import time
from typing import Callable, Dict, List, Tuple, Optional

import customtkinter as ctk

logger = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AppGUI(ctk.CTk):
    """Main Desktop GUI Window for GameVocalize."""

    def __init__(self, controller):
        super().__init__()

        self.controller = controller

        # Window Configuration
        self.title("GameVocalize — Movie Subtitles & Game Dialogue Screen Reader")
        self.geometry("1020x720")
        self.minsize(860, 600)

        # Configure Grid Layout (2 columns, 3 rows)
        self.grid_columnconfigure(0, weight=1)  # Left Controls (40%)
        self.grid_columnconfigure(1, weight=2)  # Right Live Text Log (60%)
        self.grid_rowconfigure(0, weight=0)     # Header
        self.grid_rowconfigure(1, weight=1)     # Main Body
        self.grid_rowconfigure(2, weight=0)     # Status Bar

        self._build_header()
        self._build_left_panel()
        self._build_right_panel()
        self._build_status_bar()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_header(self):
        """Top Header Bar with App Title and Active State Badge."""
        self.header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e1e2e")
        self.header_frame.grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="ew")

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="🎬 GameVocalize",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#89b4fa"
        )
        self.title_label.pack(side="left", padx=16, pady=10)

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Ultra-Fast Movie Subtitle & RPG Game Live Screen Reader",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#a6adc8"
        )
        self.subtitle_label.pack(side="left", padx=10, pady=10)

        # Active State Badge
        self.state_badge = ctk.CTkLabel(
            self.header_frame,
            text=" 🟢 ACTIVE ",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color="#1a4d2e",
            text_color="#a6e3a1",
            corner_radius=8
        )
        self.state_badge.pack(side="right", padx=16, pady=10)

    def _build_left_panel(self):
        """Left Column: Control Buttons, Voice Switcher, and Settings Sliders."""
        self.left_frame = ctk.CTkScrollableFrame(self, corner_radius=10, fg_color="#181825")
        self.left_frame.grid(row=1, column=0, padx=(12, 6), pady=(6, 6), sticky="nsew")

        # --- Section 1: 🎬 Movie & Video Subtitle Reader Mode ---
        ctk.CTkLabel(
            self.left_frame,
            text="🎬 MOVIE & VIDEO SUBTITLES",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f9e2af"
        ).pack(anchor="w", padx=10, pady=(10, 4))

        self.btn_movie_mode = ctk.CTkButton(
            self.left_frame,
            text="🎬 Start Movie Subtitle Reader (Ctrl+Alt+M)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#f9e2af",
            text_color="#11111b",
            hover_color="#fab387",
            height=40,
            command=self.controller.toggle_movie_mode
        )
        self.btn_movie_mode.pack(fill="x", padx=10, pady=4)

        self.btn_auto_bottom = ctk.CTkButton(
            self.left_frame,
            text="📐 Auto-Target Bottom Screen Subtitles (1-Click)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#89dceb",
            text_color="#11111b",
            hover_color="#74c7ec",
            height=32,
            command=self.controller.set_bottom_subtitle_roi
        )
        self.btn_auto_bottom.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(
            self.left_frame,
            text="⚡ Ultra-fast 80ms live OCR for scrolling & fast movie subtitles.\nReads foreign film subtitles in real-time as scenes change.",
            font=ctk.CTkFont(size=11),
            text_color="#bac2de",
            justify="left"
        ).pack(anchor="w", padx=12, pady=(2, 10))

        # --- Section 2: 🎮 Game Story Mode ---
        ctk.CTkLabel(
            self.left_frame,
            text="🎮 RPG GAME STORY MODE",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#a6e3a1"
        ).pack(anchor="w", padx=10, pady=(6, 4))

        self.btn_story_mode = ctk.CTkButton(
            self.left_frame,
            text="📖 Start Story Mode (Auto Dialogue)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#a6e3a1",
            text_color="#11111b",
            hover_color="#94e2d5",
            height=36,
            command=self.controller.toggle_story_mode
        )
        self.btn_story_mode.pack(fill="x", padx=10, pady=4)

        # --- Section 3: 🎤 Voice Selection (Female / Male) ---
        ctk.CTkLabel(
            self.left_frame,
            text="🎤 VOICE SELECTION",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f5c2e7"
        ).pack(anchor="w", padx=10, pady=(12, 4))

        voice_frame = ctk.CTkFrame(self.left_frame, fg_color="#1e1e2e", corner_radius=8)
        voice_frame.pack(fill="x", padx=10, pady=2)

        self.seg_voice = ctk.CTkSegmentedButton(
            voice_frame,
            values=["👩 Sweet Female (Zira)", "👨 Male (David)"],
            command=self.on_voice_changed,
            selected_color="#f5c2e7",
            selected_hover_color="#cba6f7",
            unselected_color="#313244",
            text_color="#11111b"
        )
        initial_val = "👩 Sweet Female (Zira)" if "david" not in self.controller.config.voice_name.lower() else "👨 Male (David)"
        self.seg_voice.set(initial_val)
        self.seg_voice.pack(fill="x", padx=8, pady=8)

        self.btn_test_voice = ctk.CTkButton(
            self.left_frame,
            text="🔊 Test Current Voice",
            font=ctk.CTkFont(size=12),
            fg_color="#313244",
            hover_color="#45475a",
            height=28,
            command=self.controller.test_voice
        )
        self.btn_test_voice.pack(fill="x", padx=10, pady=2)

        # --- Section 4: ⚡ Quick Controls ---
        ctk.CTkLabel(
            self.left_frame,
            text="⚡ QUICK CONTROLS",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#89b4fa"
        ).pack(anchor="w", padx=10, pady=(12, 4))

        # Master Toggle Button
        self.btn_toggle = ctk.CTkButton(
            self.left_frame,
            text="⏸ Pause Reader (Ctrl+Alt+X)",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#313244",
            hover_color="#45475a",
            height=34,
            command=self.controller.toggle_reader
        )
        self.btn_toggle.pack(fill="x", padx=10, pady=4)

        # Custom ROI Selector
        self.btn_define_roi = ctk.CTkButton(
            self.left_frame,
            text="🎯 Custom Draw Subtitle/Dialogue Box (Ctrl+Alt+D)",
            font=ctk.CTkFont(size=13),
            fg_color="#cba6f7",
            text_color="#11111b",
            hover_color="#f5c2e7",
            height=34,
            command=self.controller.define_roi
        )
        self.btn_define_roi.pack(fill="x", padx=10, pady=4)

        # Read Screen & Region Buttons
        self.btn_read_screen = ctk.CTkButton(
            self.left_frame,
            text="📸 Read Full Screen (Ctrl+Alt+F)",
            font=ctk.CTkFont(size=13),
            fg_color="#89b4fa",
            text_color="#11111b",
            hover_color="#b4befe",
            height=32,
            command=self.controller.read_full_screen
        )
        self.btn_read_screen.pack(fill="x", padx=10, pady=3)

        self.btn_read_roi = ctk.CTkButton(
            self.left_frame,
            text="📍 Read Selected Region Now (Ctrl+Alt+R)",
            font=ctk.CTkFont(size=13),
            fg_color="#313244",
            hover_color="#45475a",
            height=32,
            command=self.controller.read_regions
        )
        self.btn_read_roi.pack(fill="x", padx=10, pady=3)

        self.btn_stop_speech = ctk.CTkButton(
            self.left_frame,
            text="🔇 Silence Speech (Ctrl+Alt+S)",
            font=ctk.CTkFont(size=13),
            fg_color="#f38ba8",
            text_color="#11111b",
            hover_color="#eba0ac",
            height=32,
            command=self.controller.stop_speech
        )
        self.btn_stop_speech.pack(fill="x", padx=10, pady=3)

        # --- Section 5: ⚙️ Audio & Settings Sliders ---
        ctk.CTkLabel(
            self.left_frame,
            text="⚙️ AUDIO & SPEED SETTINGS",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#89b4fa"
        ).pack(anchor="w", padx=10, pady=(14, 4))

        # Volume Slider
        self.lbl_volume = ctk.CTkLabel(
            self.left_frame,
            text=f"🔊 Reader Volume: {self.controller.config.speech_volume}%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a6e3a1"
        )
        self.lbl_volume.pack(anchor="w", padx=12, pady=(4, 0))

        self.slider_volume = ctk.CTkSlider(
            self.left_frame,
            from_=0,
            to=100,
            number_of_steps=20,
            command=self.on_volume_changed
        )
        self.slider_volume.set(self.controller.config.speech_volume)
        self.slider_volume.pack(fill="x", padx=10, pady=(0, 8))

        # Speech Rate
        self.lbl_speed = ctk.CTkLabel(
            self.left_frame,
            text=f"Speech Speed: {self.controller.config.speech_rate} WPM",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_speed.pack(anchor="w", padx=12, pady=(4, 0))

        self.slider_speed = ctk.CTkSlider(
            self.left_frame,
            from_=50,
            to=400,
            number_of_steps=35,
            command=self.on_speed_changed
        )
        self.slider_speed.set(self.controller.config.speech_rate)
        self.slider_speed.pack(fill="x", padx=10, pady=(0, 8))

        # Subtitle / Dialogue Scan Responsiveness
        self.lbl_interval = ctk.CTkLabel(
            self.left_frame,
            text=f"Scan Speed: {self.controller.config.auto_read_interval}s",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_interval.pack(anchor="w", padx=12, pady=(4, 0))

        self.slider_interval = ctk.CTkSlider(
            self.left_frame,
            from_=0.05,
            to=2.0,
            number_of_steps=39,
            command=self.on_interval_changed
        )
        self.slider_interval.set(self.controller.config.auto_read_interval)
        self.slider_interval.pack(fill="x", padx=10, pady=(0, 10))

    def _build_right_panel(self):
        """Right Column: Real-Time Detected Text Box & Log."""
        self.right_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#181825")
        self.right_frame.grid(row=1, column=1, padx=(6, 12), pady=(6, 6), sticky="nsew")

        # Header for text log
        log_header = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            log_header,
            text="📜 REAL-TIME SUBTITLE & DIALOGUE STREAM",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#89b4fa"
        ).pack(side="left")

        ctk.CTkButton(
            log_header,
            text="Clear Log",
            width=70,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="#313244",
            hover_color="#45475a",
            command=self.clear_text_log
        ).pack(side="right")

        # Textbox for displaying detected text
        self.text_log = ctk.CTkTextbox(
            self.right_frame,
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#1e1e2e",
            text_color="#cdd6f4",
            corner_radius=8,
            wrap="word"
        )
        self.text_log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _build_status_bar(self):
        """Bottom Status Bar."""
        self.status_frame = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#11111b")
        self.status_frame.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.lbl_status = ctk.CTkLabel(
            self.status_frame,
            text="Engine Ready | Backend: " + getattr(self.controller.capture, "backend", "MSS") + " | Active Regions: 0",
            font=ctk.CTkFont(size=12),
            text_color="#a6adc8"
        )
        self.lbl_status.pack(side="left", padx=16, pady=4)

    def append_log(self, text: str):
        self.after(0, self._append_log_internal, text)

    def _append_log_internal(self, text: str):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.text_log.insert("end", f"{timestamp}{text}\n\n")
        self.text_log.see("end")

    def clear_text_log(self):
        self.text_log.delete("1.0", "end")

    def update_status_bar(self, status_text: str):
        self.after(0, lambda: self.lbl_status.configure(text=status_text))

    def update_active_state(self, active: bool):
        def _update():
            if active:
                self.state_badge.configure(text=" 🟢 ACTIVE ", fg_color="#1a4d2e", text_color="#a6e3a1")
                self.btn_toggle.configure(text="⏸ Pause Reader (Ctrl+Alt+X)", fg_color="#313244")
            else:
                self.state_badge.configure(text=" 🔴 PAUSED ", fg_color="#585b70", text_color="#f38ba8")
                self.btn_toggle.configure(text="▶ Resume Reader (Ctrl+Alt+X)", fg_color="#a6e3a1", text_color="#11111b")
        self.after(0, _update)

    def update_movie_mode_button(self, active: bool):
        def _update():
            if active:
                self.btn_movie_mode.configure(
                    text="⏹ Stop Movie Mode (Reading Subtitles)",
                    fg_color="#f38ba8",
                    hover_color="#eba0ac"
                )
            else:
                self.btn_movie_mode.configure(
                    text="🎬 Start Movie Subtitle Reader (Ctrl+Alt+M)",
                    fg_color="#f9e2af",
                    hover_color="#fab387"
                )
        self.after(0, _update)

    def update_story_mode_button(self, active: bool):
        def _update():
            if active:
                self.btn_story_mode.configure(
                    text="⏹ Stop Story Mode (Watching Dialogue)",
                    fg_color="#f38ba8",
                    hover_color="#eba0ac"
                )
            else:
                self.btn_story_mode.configure(
                    text="📖 Start Story Mode (Auto Dialogue)",
                    fg_color="#a6e3a1",
                    hover_color="#94e2d5"
                )
        self.after(0, _update)

    def on_voice_changed(self, value):
        if "david" in value.lower() or "male" in value.lower():
            self.controller.set_voice("David")
        else:
            self.controller.set_voice("Zira")

    def on_volume_changed(self, value):
        vol = int(value)
        self.lbl_volume.configure(text=f"🔊 Reader Volume: {vol}%")
        self.controller.set_volume(vol)

    def on_speed_changed(self, value):
        wpm = int(value)
        self.lbl_speed.configure(text=f"Speech Speed: {wpm} WPM")
        self.controller.config.speech_rate = wpm
        sapi_rate = int((wpm - 200) / 15)
        self.controller.tts.set_rate(sapi_rate)

    def on_interval_changed(self, value):
        val = round(float(value), 2)
        self.lbl_interval.configure(text=f"Scan Speed: {val}s")
        self.controller.config.auto_read_interval = val
        self.controller.config.movie_scan_interval = val

    def on_close(self):
        logger.info("GUI close requested.")
        self.controller.quit_app()
        self.destroy()
