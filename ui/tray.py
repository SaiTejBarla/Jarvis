"""
ui/tray.py — JARVIS system tray icon (Phase 6).

Puts JARVIS in the Windows system tray with a right-click context menu
for quick actions: Open HUD, Open Web UI, Voice mode, Exit.

Requires:
    pip install PyQt6
"""

import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter
    from PyQt6.QtCore import Qt, QSize
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


def _make_icon() -> "QIcon":
    """Generate a simple cyan 'J' icon programmatically (no image file needed)."""
    pix = QPixmap(QSize(32, 32))
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Background circle
    painter.setBrush(QColor(5, 15, 30))
    painter.setPen(QColor(0, 212, 255))
    painter.drawEllipse(1, 1, 30, 30)
    # Letter J
    from PyQt6.QtGui import QFont as _QFont
    font = _QFont("Segoe UI", 16, _QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(0, 212, 255))
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "J")
    painter.end()
    return QIcon(pix)


class JarvisTray:
    """JARVIS system tray icon with context menu."""

    def __init__(self, engine=None) -> None:
        if not PYQT6_AVAILABLE:
            raise RuntimeError("PyQt6 not installed. Run: pip install PyQt6")

        self._engine = engine
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._hud = None

        self._tray = QSystemTrayIcon(_make_icon(), self._app)
        self._tray.setToolTip("JARVIS — Click to open HUD")
        self._tray.activated.connect(self._on_activate)

        self._build_menu()
        self._tray.show()

    def _build_menu(self):
        menu = QMenu()

        menu.addSection("J.A.R.V.I.S.")

        act_hud = menu.addAction("🖥️  Open HUD")
        act_hud.triggered.connect(self._open_hud)

        act_web = menu.addAction("🌐  Open Web UI")
        act_web.triggered.connect(self._open_web)

        act_voice = menu.addAction("🎤  Start Voice Mode")
        act_voice.triggered.connect(self._start_voice)

        menu.addSeparator()

        act_status = menu.addAction("● JARVIS Online")
        act_status.setEnabled(False)

        menu.addSeparator()

        act_exit = menu.addAction("✕  Exit JARVIS")
        act_exit.triggered.connect(self._exit)

        self._tray.setContextMenu(menu)

    def _on_activate(self, reason):
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._open_hud()

    def _open_hud(self):
        from ui.hud import HUDWindow
        if self._hud is None or not self._hud.isVisible():
            self._hud = HUDWindow(engine=self._engine)
        self._hud.show()
        self._hud.raise_()
        self._hud.activateWindow()

    def _open_web(self):
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run",
             str(Path(__file__).parent / "app.py")],
            cwd=str(Path(__file__).parent.parent),
        )
        self._tray.showMessage(
            "JARVIS Web UI",
            "Opening web UI — check your browser at http://localhost:8501",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _start_voice(self):
        subprocess.Popen(
            [sys.executable, "main.py", "--voice"],
            cwd=str(Path(__file__).parent.parent),
        )
        self._tray.showMessage(
            "JARVIS Voice Mode",
            "Voice mode starting — say 'Hey Jarvis' to activate.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _exit(self):
        self._tray.hide()
        self._app.quit()

    def notify(self, title: str, message: str) -> None:
        """Show a system tray notification balloon."""
        if not PYQT6_AVAILABLE:
            return
        from PyQt6.QtWidgets import QSystemTrayIcon
        self._tray.showMessage(
            title, message,
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def run(self):
        """Block until the tray exits."""
        self._app.exec()


def run_tray(engine=None):
    """Launch the system tray. Blocks until exit."""
    if not PYQT6_AVAILABLE:
        print("[Tray] PyQt6 not installed. Run: pip install PyQt6")
        return
    tray = JarvisTray(engine=engine)
    tray.run()


if __name__ == "__main__":
    from core.engine import JarvisEngine
    import logging
    logging.basicConfig(level=logging.INFO)
    run_tray(engine=JarvisEngine())
