import sys
import threading
import ctypes
import ctypes.wintypes as wintypes
import time
import requests
import urllib3

from PySide6.QtCore import (
    Qt,
    QObject,
    Signal,
    QAbstractNativeEventFilter,
    QEvent,
    QTimer,
)
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtGui import QCursor, QPixmap

# Disable warnings for self-signed certificates on localhost.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from ctypes import windll

# Constants for setting the extended window style.
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20


def set_click_through(widget):
    hwnd = int(widget.winId())
    ex_style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    windll.user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED | WS_EX_TRANSPARENT
    )


def set_window_ex_transparent(hwnd, transparent=True):
    """Toggle WS_EX_TRANSPARENT on a window given by hwnd."""
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if transparent:
        ex_style |= WS_EX_TRANSPARENT
    else:
        ex_style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)


# ========= Detection Code Using WinEventHook =========

league_focused = None  # Global state to track focus.


class FocusNotifier(QObject):
    focusChanged = Signal(bool)  # True if focused, False otherwise


notifier = FocusNotifier()

# Define required types from Windows API.
HWINEVENTHOOK = ctypes.c_void_p
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WINEVENTPROC = ctypes.WINFUNCTYPE(
    None,
    HWINEVENTHOOK,  # hWinEventHook
    wintypes.DWORD,  # event
    wintypes.HWND,  # hwnd
    wintypes.LONG,  # idObject
    wintypes.LONG,  # idChild
    wintypes.DWORD,  # dwEventThread
    wintypes.DWORD,  # dwmsEventTime
)


def detection_callback(
    hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime
):
    global league_focused
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buffer, 512)
    title = buffer.value
    # Debug print: you’ll see every foreground change.
    print(f"Detection callback: event={event}, hwnd={hwnd}, title='{title}'")
    if title == "League of Legends (TM) Client":
        if league_focused != True:
            league_focused = True
            notifier.focusChanged.emit(True)
    else:
        if league_focused == True:
            league_focused = False
            notifier.focusChanged.emit(False)


wineventproc = WINEVENTPROC(detection_callback)

EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002
dwFlags = WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS


def detection_thread():
    hook = user32.SetWinEventHook(
        EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND, 0, wineventproc, 0, 0, dwFlags
    )
    print("Detection hook handle:", hook)
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    print("Detection thread exiting.")


# ========= Overlay Window with CS/min Update =========


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        # Set the window to be frameless, always on top, and transparent.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.NoFocus)

        layout = QVBoxLayout()
        self.label = QLabel("CS: 0.0")
        self.label.setStyleSheet(
            "color: white; font-family: 'Segoe UI'; font-size: 12pt; font-weight: bold;"
        )
        layout.addWidget(self.label, alignment=Qt.AlignTop | Qt.AlignRight)
        self.setLayout(layout)

        # Start hidden.
        self.hide()

        # Initially, make the window click-through.
        self.hwnd = int(self.winId())
        set_window_ex_transparent(self.hwnd, True)

    def showOverlay(self):
        if not self.isVisible():
            print("Showing overlay.")
            self.showFullScreen()

    def hideOverlay(self):
        if self.isVisible():
            print("Hiding overlay.")
            self.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.dragPos = event.globalPos() - self.frameGeometry().topLeft()
            # Temporarily disable click-through so we can capture events.
            set_window_ex_transparent(self.hwnd, False)
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, "dragging", False):
            self.move(event.globalPos() - self.dragPos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, "dragging", False):
            self.dragging = False
            # Restore click-through behavior.
            set_window_ex_transparent(self.hwnd, True)
            event.accept()


WM_SETCURSOR = 0x20


class NoCursorChangeFilter(QAbstractNativeEventFilter):
    def __init__(self, window_ids):
        super().__init__()
        self.window_ids = window_ids

    def nativeEventFilter(self, eventType, message):
        if eventType == "windows_generic_MSG":
            msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
            if msg.message == WM_SETCURSOR and int(msg.hWnd) in self.window_ids:
                return True, 0  # Suppress cursor change
        return False, 0


class NoCursorChangeLabel(QLabel):
    def event(self, event):
        if event.type() == QEvent.CursorChange:
            return True
        return super().event(event)


# ========= Functions to Fetch Data from League Client API =========


def fetch_active_player_name():
    """Return the active player name from the League client."""
    try:
        url = "https://127.0.0.1:2999/liveclientdata/activeplayername"
        response = requests.get(url, verify=False, timeout=1)
        return response.text.strip('"')
    except Exception as e:
        print("Error fetching active player name:", e)
        return None


def fetch_player_scores(riot_id):
    """Return the player scores JSON for the given riotId."""
    try:
        url = f"https://127.0.0.1:2999/liveclientdata/playerscores?riotId={riot_id}"
        print("Fetching player scores from:", url)
        # Use verify=False to ignore SSL certificate warnings.
        response = requests.get(url, verify=False, timeout=1)
        return response.json()
    except Exception as e:
        print("Error fetching player scores:", e)
        return None


def update_cs(overlay):
    """Query the League client API and update the overlay label with CS per minute."""
    if not overlay.isVisible():
        return
    try:
        active_player = fetch_active_player_name()
        print(active_player)
        if active_player:
            scores = fetch_player_scores(active_player)
            if scores:
                print("Player scores:", scores)
                total_cs = scores.get("creepScore", 0)
                # Fetch game time (in seconds) and convert to minutes.
                game_stats = requests.get(
                    "https://127.0.0.1:2999/liveclientdata/gamestats",
                    verify=False,
                    timeout=1,
                ).json()
                game_time = game_stats.get("gameTime", 0) / 60.0  # minutes
                if game_time > 0:
                    cs_per_min = int(total_cs) / game_time
                    overlay.label.setText("CS: %.1f" % cs_per_min)
    except Exception as e:
        print("Error updating CS:", e)


# ========= Main Program =========


def main():
    app = QApplication(sys.argv)
    overlay = OverlayWindow()

    # Connect the focusChanged signal to show or hide the overlay.
    notifier.focusChanged.connect(
        lambda focused: overlay.showOverlay() if focused else overlay.hideOverlay()
    )

    # Start the detection thread.
    t = threading.Thread(target=detection_thread, daemon=True)
    t.start()

    # Set up a QTimer to update the CS value every second.
    timer = QTimer()
    timer.timeout.connect(lambda: update_cs(overlay))
    timer.start(1000)  # update every 1000 milliseconds

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
