"""
roi_selector.py - Transparent Fullscreen Overlay for Region Selection
Supports drawing bounding boxes over game dialogue and movie subtitle windows.
Thread-safe Toplevel window attached to main Tkinter root.
"""

import tkinter as tk
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class RoiSelector:
    """Provides a transparent fullscreen overlay to select regions of interest (ROIs)."""

    def __init__(self, parent: Optional[tk.Tk] = None):
        self.parent = parent
        self._rectangles: List[Tuple[int, int, int, int]] = []
        self._cancelled = False
        self._current_start: Optional[Tuple[int, int]] = None
        self._current_rect_id = None

        self.top: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.drawn_items: List[int] = []
        self.text_items: List[int] = []

    def _on_mouse_down(self, event):
        self._current_start = (event.x, event.y)

    def _on_mouse_drag(self, event):
        if not self._current_start or not self.canvas:
            return

        x0, y0 = self._current_start
        x1, y1 = event.x, event.y

        if self._current_rect_id:
            self.canvas.coords(self._current_rect_id, x0, y0, x1, y1)
        else:
            self._current_rect_id = self.canvas.create_rectangle(
                x0, y0, x1, y1, outline="#a6e3a1", width=3, fill="#a6e3a1", stipple="gray25"
            )

    def _on_mouse_up(self, event):
        if not self._current_start or not self._current_rect_id or not self.canvas:
            self._current_start = None
            self._current_rect_id = None
            return

        x0, y0 = self._current_start
        x1, y1 = event.x, event.y

        x = min(x0, x1)
        y = min(y0, y1)
        w = abs(x1 - x0)
        h = abs(y1 - y0)

        if w > 5 and h > 5:
            self._rectangles.append((x, y, w, h))
            self.drawn_items.append(self._current_rect_id)

            label = f" Region #{len(self._rectangles)}: ({x}, {y}, {w}x{h}) "
            text_id = self.canvas.create_text(
                x + 5, max(15, y - 10), text=label, fill="#a6e3a1",
                font=("Consolas", 12, "bold"), anchor="nw"
            )
            self.text_items.append(text_id)
        else:
            self.canvas.delete(self._current_rect_id)

        self._current_start = None
        self._current_rect_id = None

    def _on_right_click(self, event):
        if self._rectangles and self.canvas:
            self._rectangles.pop()
            rect_id = self.drawn_items.pop()
            self.canvas.delete(rect_id)
            text_id = self.text_items.pop()
            self.canvas.delete(text_id)

    def _on_enter(self, event):
        self._cancelled = False
        if self.top:
            self.top.destroy()

    def _on_escape(self, event):
        self._cancelled = True
        if self.top:
            self.top.destroy()

    def select(self) -> Optional[List[Tuple[int, int, int, int]]]:
        """Open transparent overlay and return selected regions."""
        logger.info("Opening ROI selector overlay...")
        self._rectangles = []
        self.drawn_items = []
        self.text_items = []
        self._cancelled = False

        if self.parent:
            self.parent.withdraw()

        if self.parent:
            self.top = tk.Toplevel(self.parent)
        else:
            self.top = tk.Tk()

        self.top.attributes('-alpha', 0.35)
        self.top.attributes('-topmost', True)
        self.top.overrideredirect(True)

        screen_width = self.top.winfo_screenwidth()
        screen_height = self.top.winfo_screenheight()
        self.top.geometry(f"{screen_width}x{screen_height}+0+0")

        self.canvas = tk.Canvas(self.top, cursor="cross", bg="#11111b", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Instruction Banner
        self.canvas.create_rectangle(0, 0, screen_width, 60, fill="#181825", outline="")
        self.canvas.create_text(
            screen_width // 2, 30,
            text="📖 DRAG MOUSE TO DRAW DIALOGUE / SUBTITLE BOX | RIGHT-CLICK TO UNDO | PRESS ENTER TO CONFIRM | PRESS ESC TO CANCEL",
            fill="#89b4fa", font=("Segoe UI", 13, "bold"), justify=tk.CENTER
        )

        self.top.bind("<Button-1>", self._on_mouse_down)
        self.top.bind("<B1-Motion>", self._on_mouse_drag)
        self.top.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.top.bind("<Button-3>", self._on_right_click)
        self.top.bind("<Return>", self._on_enter)
        self.top.bind("<Escape>", self._on_escape)

        self.top.focus_force()

        if self.parent:
            self.top.wait_window()
            self.parent.deiconify()
        else:
            self.top.mainloop()

        logger.info(f"ROI selector closed. Selected {len(self._rectangles)} region(s).")

        if self._cancelled:
            return None
        return list(self._rectangles)
