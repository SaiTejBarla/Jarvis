"""
ui/hud.py — JARVIS Desktop HUD overlay (Phase 6).

An always-on-top, semi-transparent desktop overlay inspired by Iron Man's HUD.
Displays JARVIS status, last reply, and a text input field.

Run standalone:
    python ui/hud.py

Or launched from main.py --hud

Requires:
    pip install PyQt6
"""

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QTextEdit, QSizePolicy,
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    from PyQt6.QtGui import QColor, QPalette, QFont, QKeySequence, QShortcut
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


# ── Signal bridge (thread-safe UI updates) ───────────────────────────────────

class _Bridge(QObject):
    reply_received = pyqtSignal(str)
    status_changed = pyqtSignal(str)


_bridge = _Bridge() if PYQT6_AVAILABLE else None


# ── HUD Window ────────────────────────────────────────────────────────────────

_HUD_CSS = """
QWidget#hud {
    background-color: rgba(5, 15, 30, 210);
    border: 1px solid #00d4ff44;
    border-radius: 10px;
}
QLabel#title {
    color: #00d4ff;
    font-size: 18px;
    font-weight: bold;
    letter-spacing: 4px;
}
QLabel#status {
    color: #00ff88;
    font-size: 11px;
}
QTextEdit#output {
    background-color: rgba(0, 20, 40, 180);
    color: #c8e8ff;
    border: 1px solid #00d4ff22;
    border-radius: 4px;
    font-size: 12px;
    padding: 6px;
}
QLineEdit#input {
    background-color: rgba(0, 20, 40, 200);
    color: #00d4ff;
    border: 1px solid #00d4ff55;
    border-radius: 4px;
    font-size: 12px;
    padding: 6px;
}
QPushButton {
    background-color: rgba(0, 212, 255, 30);
    color: #00d4ff;
    border: 1px solid #00d4ff44;
    border-radius: 4px;
    padding: 4px 10px;
    font-size: 11px;
}
QPushButton:hover {
    background-color: rgba(0, 212, 255, 60);
}
"""


class HUDWindow(QWidget):
    def __init__(self, engine=None):
        super().__init__()
        self._engine = engine
        self._setup_window()
        self._build_ui()
        self._connect_signals()

    def _setup_window(self):
        self.setObjectName("hud")
        self.setWindowTitle("JARVIS HUD")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(420, 300)
        self.resize(460, 340)
        # Position: bottom-right corner
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 480, screen.height() - 380)
        self.setStyleSheet(_HUD_CSS)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(6)

        # Title bar
        title_row = QHBoxLayout()
        title = QLabel("J.A.R.V.I.S.")
        title.setObjectName("title")
        self._status = QLabel("● ONLINE")
        self._status.setObjectName("status")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self._status)

        # Close / minimise buttons
        btn_min = QPushButton("−")
        btn_min.setFixedSize(22, 22)
        btn_min.clicked.connect(self.showMinimized)
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(22, 22)
        btn_close.clicked.connect(self.hide)
        title_row.addWidget(btn_min)
        title_row.addWidget(btn_close)
        root.addLayout(title_row)

        # Output area
        self._output = QTextEdit()
        self._output.setObjectName("output")
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("JARVIS responses will appear here…")
        self._output.setMinimumHeight(180)
        root.addWidget(self._output)

        # Input row
        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setObjectName("input")
        self._input.setPlaceholderText("Ask JARVIS…  (Enter to send)")
        self._input.returnPressed.connect(self._send)
        self._btn_send = QPushButton("Send")
        self._btn_send.clicked.connect(self._send)
        input_row.addWidget(self._input)
        input_row.addWidget(self._btn_send)
        root.addLayout(input_row)

    def _connect_signals(self):
        if _bridge:
            _bridge.reply_received.connect(self._on_reply)
            _bridge.status_changed.connect(self._on_status)

    # ── Drag to move (frameless window) ──────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ── Send message ─────────────────────────────────────────────────────────
    def _send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._output.append(f'<span style="color:#00d4ff">You: {text}</span>')
        self._on_status("● THINKING…")

        def _run():
            if self._engine:
                reply = self._engine.process(text)
            else:
                reply = "(No engine connected)"
            if _bridge:
                _bridge.reply_received.emit(reply)

        threading.Thread(target=_run, daemon=True).start()

    def _on_reply(self, text: str):
        self._output.append(f'<span style="color:#00ff88">JARVIS: {text}</span><br>')
        self._output.verticalScrollBar().setValue(
            self._output.verticalScrollBar().maximum()
        )
        self._on_status("● ONLINE")

    def _on_status(self, text: str):
        self._status.setText(text)

    def set_reply(self, text: str):
        """Thread-safe: update HUD with a new JARVIS reply."""
        if _bridge:
            _bridge.reply_received.emit(text)

    def set_status(self, text: str):
        if _bridge:
            _bridge.status_changed.emit(text)


# ── Entry point ───────────────────────────────────────────────────────────────

def run_hud(engine=None):
    """Launch the HUD. Blocks until window is closed."""
    if not PYQT6_AVAILABLE:
        print("[HUD] PyQt6 not installed. Run: pip install PyQt6")
        return

    app = QApplication.instance() or QApplication(sys.argv)
    window = HUDWindow(engine=engine)
    window.show()
    app.exec()


if __name__ == "__main__":
    import config
    from core.engine import JarvisEngine
    import logging, sys as _sys
    logging.basicConfig(level=logging.INFO, stream=_sys.stdout)
    eng = JarvisEngine()
    run_hud(engine=eng)
