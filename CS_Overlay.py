import sys
import threading
import ctypes
import ctypes.wintypes as wintypes
from ctypes import windll
import os
import json

from PySide6.QtCore import (
    Qt,
    QObject,
    Signal,
    QTimer,
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QVBoxLayout,
    QSystemTrayIcon,
    QMenu,
    QDialog,
    QFormLayout,
    QSpinBox,
    QTextEdit,
    QDialogButtonBox,
)
from PySide6.QtGui import QIcon, QAction

from Stats import CSOCR, gettime

try:
    base_path = sys._MEIPASS
except Exception:
    base_path = os.path.abspath(".")

icon_path = os.path.join(base_path, "draw.png")
config_path = os.path.join(base_path, "config.json")

print("Base path:", base_path)
print("Icon path:", icon_path)
print("Config path:", config_path)

# windows API thingies

# Constants for setting the extended window style.
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20


def set_window_ex_transparent(hwnd, transparent=True):
    """Toggle WS_EX_TRANSPARENT on a window given by hwnd."""
    ex_style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    if transparent:
        ex_style |= WS_EX_TRANSPARENT
    else:
        ex_style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style)


# ========= Detection Code Using WinEventHook =========

# Global state to track focus.
league_focused = False


# Global notifier (a QObject) that will emit signals to update the overlay.
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
    # Debug print: you’ll see every foreground change
    print(f"Detection callback: event={event}, hwnd={hwnd}, title='{title}'")
    if title == "League of Legends (TM) Client":
        if league_focused != True:
            league_focused = True
            notifier.focusChanged.emit(True)
    else:
        if league_focused != False:
            league_focused = False
            notifier.focusChanged.emit(False)


wineventproc = WINEVENTPROC(detection_callback)


# Add a helper function to get the current foreground window title
def get_foreground_window_title():
    hwnd = user32.GetForegroundWindow()
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buffer, 512)
    return buffer.value


# Function to check if League is focused
def check_league_focus():
    global league_focused
    title = get_foreground_window_title()
    was_focused = league_focused

    # Check if the title indicates League of Legends
    is_league = title == "League of Legends (TM) Client"

    # Only update and emit signals if the state has changed
    if is_league != was_focused:
        league_focused = is_league
        print(f"Focus check: '{title}' - {'Focused' if is_league else 'Not focused'}")
        notifier.focusChanged.emit(is_league)


# Constants for the hook.
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


# ========= PySide Overlay Window =========


class OverlayWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.show_cs = False
        self.show_time = False
        self.show_csmin = False
        self.custom_format = "{csmin}  CS/Min"
        self.font_size = 10  # new: store current font size
        self.force_visible = False
        self.initUI()

    def initUI(self):
        # Set the window to be frameless, always on top, and transparent.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background: transparent;")
        self.setAttribute(
            Qt.WA_TransparentForMouseEvents, True
        )  # probably does nothing
        self.setFocusPolicy(Qt.NoFocus)  # probably does nothing

        # Create a layout and label.
        layout = QVBoxLayout()
        # Note: leave desired margins; for example, right margin is 10 pixels.
        # layout.setContentsMargins(0, 60, 10, 0)
        layout.setContentsMargins(0, 0, 0, 0)  # stop using margins
        self.cs_label = QLabel("")
        self.cs_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.cs_label.setStyleSheet(
            "color: white; font-family: 'Segoe UI'; font-size: 10pt; font-weight: bold;"
        )

        layout.addWidget(self.cs_label, alignment=Qt.AlignTop | Qt.AlignRight)
        self.setLayout(layout)

        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            self.setGeometry(primary_screen.geometry())
            # Constrain the label width so it doesn't expand past the overlay width.
            available_width = self.width() - layout.contentsMargins().right()
            # available_width = (
            # self.width()
            # )  # just full monitor idc if it slightly overflows as long as it doesn't move anchor
            self.cs_label.setFixedWidth(available_width)

        # Start hidden.
        self.hide()

        self.hwnd = int(self.winId())
        set_window_ex_transparent(self.hwnd, True)  # actually does something

    def showOverlay(self):
        print("Showing overlay.")
        self.showFullScreen()

    def hideOverlay(self):
        if self.isVisible() and not self.force_visible:
            print("Hiding overlay.")
            self.hide()

    def update_display(self):
        cs_value = self.ocr.get_cs()
        if league_focused:
            current_time = gettime()
        else:
            current_time = 1
        minutes = int(current_time)
        seconds = int((current_time % 1) * 60)
        cs_per_min = cs_value / current_time if current_time > 0 else 0

        if self.custom_format:
            try:
                text = self.custom_format.format(
                    cs=cs_value,
                    time=f"{minutes}:{seconds:02d}",
                    csmin=f"{cs_per_min:.1f}",
                )
            except Exception as e:
                text = "Format error"
        else:
            lines = []
            if self.show_cs:
                lines.append(str(cs_value))
            if self.show_time:
                lines.append(f"{minutes}:{seconds:02d}")
            if self.show_csmin:
                lines.append(f"{cs_per_min:.1f}")
            text = "\n".join(lines)

        self.cs_label.setText(text)


# Options Window
# New: Options dialog that allows setting the overlay position and custom format.
class OptionsWindow(QDialog):
    def __init__(self, overlay, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Options")
        self.overlay = overlay

        if hasattr(overlay, "tray"):
            self.setWindowIcon(overlay.tray.icon())

        layout = QFormLayout()
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.setValue(overlay.x())
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.setValue(overlay.y())
        self.format_edit = QTextEdit()
        # if custom_format is not set, default to empty.
        self.format_edit.setText(overlay.custom_format if overlay.custom_format else "")

        # Add an instructions label for the custom format.
        instr_label = QLabel(
            "Instructions:\n"
            "• Use {cs} to display the CS count\n"
            "• Use {time} to display the current time (MM:SS)\n"
            "• Use {csmin} to display the CS per minute\n"
            "Multi-line format is allowed."
        )
        instr_label.setWordWrap(True)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(1, 10000)
        self.font_spin.setValue(10)

        layout.addRow("Overlay X:", self.x_spin)
        layout.addRow("Overlay Y:", self.y_spin)
        layout.addRow("Font Size:", self.font_spin)
        layout.addRow("Custom Format:", self.format_edit)
        layout.addRow("Format Instructions:", instr_label)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.Apply | QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        apply_btn = btn_box.button(QDialogButtonBox.Apply)
        apply_btn.clicked.connect(self.apply_changes)

        layout.addRow(btn_box)

        self.setLayout(layout)

    def apply_changes(self):
        # Update overlay position and custom format.
        self.overlay.move(self.x_spin.value(), self.y_spin.value())
        fmt = self.format_edit.toPlainText().strip()
        self.overlay.custom_format = fmt if fmt != "" else None

        font_size = self.font_spin.value()
        self.overlay.font_size = font_size  # store current font size
        self.overlay.cs_label.setStyleSheet(
            f"color: white; font-family: 'Segoe UI'; font-size: {font_size}pt; font-weight: bold;"
        )

        # Immediately update the overlay's display.
        self.overlay.update_display()

    def accept(self):
        self.apply_changes()
        super().accept()


def open_options(overlay):
    overlay.force_visible = True
    overlay.showOverlay()

    options_dialog = OptionsWindow(overlay)
    options_dialog.exec()

    overlay.force_visible = False
    overlay.hideOverlay()


# system tray and menu


def create_tray(app, overlay):
    # Create the system tray icon.
    tray = QSystemTrayIcon()

    tray.setIcon(QIcon(icon_path))
    tray.setToolTip("CS Overlay")

    # Connect double-click on the tray icon to open Options. # this is completely broken
    tray.activated.connect(
        lambda reason: (
            open_options(overlay) if reason == QSystemTrayIcon.DoubleClick else None
        )
    )

    # Create a context menu for the tray icon.
    menu = QMenu()
    menu.setMinimumWidth(50)  # Force a minimum width for the menu

    options_action = QAction("Options", app)
    options_action.triggered.connect(lambda: open_options(overlay))
    menu.addAction(options_action)

    exit_action = QAction("Exit", app)
    exit_action.triggered.connect(app.quit)
    menu.addAction(exit_action)

    tray.setContextMenu(menu)
    tray.show()
    return tray


# ========= Main Program =========


def load_config():
    try:
        with open(config_path, "r") as f:
            print("found config")
            return json.load(f)
    except Exception:
        print("did not load config, using defaults")
        # DEFAULTS
        return {
            "x": -10,
            "y": 60,
            "custom_format": "{csmin}  CS/Min",
            "font_size": 10,
        }


def save_config(config):
    print("Saving")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # because overlay is usually hidden
    overlay = OverlayWindow()
    ocr = CSOCR()
    overlay.ocr = ocr

    # Load configuration.
    config = load_config()
    if config:
        x = config.get("x", overlay.x())
        y = config.get("y", overlay.y())
        overlay.move(x, y)
        overlay.custom_format = config.get("custom_format", None)
        overlay.font_size = config.get("font_size", 10)
        overlay.cs_label.setStyleSheet(
            f"color: white; font-family: 'Segoe UI'; font-size: {overlay.font_size}pt; font-weight: bold;"
        )

    notifier.focusChanged.connect(
        lambda focused: overlay.showOverlay() if focused else overlay.hideOverlay()
    )

    # Set up the display update timer
    timer = QTimer()
    timer.setInterval(500)
    timer.timeout.connect(
        lambda: overlay.update_display() if overlay.isVisible() else None
    )
    timer.start()

    # Add a second timer for periodic focus checking
    focus_timer = QTimer()
    focus_timer.setInterval(1000)  # Check every second
    focus_timer.timeout.connect(check_league_focus)
    focus_timer.start()

    tray = create_tray(app, overlay)
    overlay.tray = tray

    # When the application is about to quit, save the latest configuration.
    def on_exit():
        config = {
            "x": overlay.x(),
            "y": overlay.y(),
            "custom_format": overlay.custom_format,
            "font_size": overlay.font_size,
        }
        save_config(config)

    app.aboutToQuit.connect(on_exit)

    t = threading.Thread(target=detection_thread, daemon=True)
    t.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
