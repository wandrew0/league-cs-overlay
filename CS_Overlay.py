import ctypes
import ctypes.wintypes as wintypes
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import tempfile
import threading

from Stats import CSOCR, gettime


try:
    base_path = sys._MEIPASS
except Exception:
    base_path = os.path.abspath(".")

icon_path = os.path.join(base_path, "draw.ico")
config_path = os.path.join(base_path, "config.json")
runtime_dir = (
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
log_dir = runtime_dir if os.access(runtime_dir, os.W_OK) else tempfile.gettempdir()
log_path = os.path.join(log_dir, "cs_overlay.log")


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

if not hasattr(wintypes, "LRESULT"):
    wintypes.LRESULT = (
        ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
    )
if not hasattr(wintypes, "UINT_PTR"):
    wintypes.UINT_PTR = (
        ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint
    )
if not hasattr(wintypes, "HANDLE"):
    wintypes.HANDLE = ctypes.c_void_p

_handle_aliases = [
    "HINSTANCE",
    "HMODULE",
    "HWND",
    "HMENU",
    "HICON",
    "HCURSOR",
    "HBRUSH",
    "HBITMAP",
    "HGDIOBJ",
]
for _handle_name in _handle_aliases:
    if not hasattr(wintypes, _handle_name):
        setattr(wintypes, _handle_name, wintypes.HANDLE)

if not hasattr(wintypes, "COLORREF"):
    wintypes.COLORREF = wintypes.DWORD

user32.CreateWindowExW.restype = wintypes.HWND
user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.TranslateMessage.restype = wintypes.BOOL
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = wintypes.LRESULT


def rgb(r, g, b):
    return r | (g << 8) | (b << 16)


GWL_EXSTYLE = -20
SRCCOPY = 0x00CC0020
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_OVERLAPPED = 0x00000000
WS_CAPTION = 0x00C00000
WS_SYSMENU = 0x00080000

SW_HIDE = 0
SW_SHOWNOACTIVATE = 4

HWND_TOPMOST = -1

SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOSENDCHANGING = 0x0400

LWA_COLORKEY = 0x00000001

WM_PAINT = 0x000F
WM_TIMER = 0x0113
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_NCHITTEST = 0x0084
WM_CREATE = 0x0001
WM_COMMAND = 0x0111
WM_DISPLAYCHANGE = 0x007E
WM_SETTINGCHANGE = 0x001A
WM_DPICHANGED = 0x02E0
WM_DWMCOMPOSITIONCHANGED = 0x031E

WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1
WM_FOCUS_CHANGED = WM_APP + 2
WM_CTLCOLORSTATIC = 0x0138
WM_CTLCOLOREDIT = 0x0133

HTTRANSPARENT = -1

TIMER_UPDATE = 1
TIMER_FOCUS_POLL = 2

EVENT_SYSTEM_FOREGROUND = 0x0003
WINEVENT_OUTOFCONTEXT = 0x0000
WINEVENT_SKIPOWNPROCESS = 0x0002

LEAGUE_TITLES = {"League of Legends (TM) Client"}
LEAGUE_PROCESS_NAMES = {"League of Legends.exe"}

ID_TRAY_OPTIONS = 1001
ID_TRAY_EXIT = 1002

ERROR_ALREADY_EXISTS = 183
MB_OK = 0x00000000
MB_ICONINFORMATION = 0x00000040

IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

TPM_RETURNCMD = 0x0100
TPM_NONOTIFY = 0x0080

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

COLOR_WINDOW = 5
COLOR_BTNFACE = 15

MIN_TIMER_MS = 50
MAX_TIMER_MS = 60000

WS_CHILD = 0x40000000
WS_BORDER = 0x00800000
WS_TABSTOP = 0x00010000
WS_VSCROLL = 0x00200000

ES_MULTILINE = 0x0004
ES_AUTOVSCROLL = 0x0040
ES_WANTRETURN = 0x1000

DT_RIGHT = 0x0002
DT_TOP = 0x0000
DT_NOPREFIX = 0x0800


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", wintypes.HDC),
        ("fErase", wintypes.BOOL),
        ("rcPaint", RECT),
        ("fRestore", wintypes.BOOL),
        ("fIncUpdate", wintypes.BOOL),
        ("rgbReserved", ctypes.c_byte * 32),
    ]


class LOGFONTW(ctypes.Structure):
    _fields_ = [
        ("lfHeight", wintypes.LONG),
        ("lfWidth", wintypes.LONG),
        ("lfEscapement", wintypes.LONG),
        ("lfOrientation", wintypes.LONG),
        ("lfWeight", wintypes.LONG),
        ("lfItalic", wintypes.BYTE),
        ("lfUnderline", wintypes.BYTE),
        ("lfStrikeOut", wintypes.BYTE),
        ("lfCharSet", wintypes.BYTE),
        ("lfOutPrecision", wintypes.BYTE),
        ("lfClipPrecision", wintypes.BYTE),
        ("lfQuality", wintypes.BYTE),
        ("lfPitchAndFamily", wintypes.BYTE),
        ("lfFaceName", wintypes.WCHAR * 32),
    ]


WNDPROC = ctypes.WINFUNCTYPE(
    wintypes.LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)

WINEVENTPROC = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD,
)


class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


if not hasattr(wintypes, "ATOM"):
    wintypes.ATOM = wintypes.WORD

user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [
    ctypes.c_void_p,
    wintypes.BOOL,
    wintypes.LPCWSTR,
]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.SetLastError.argtypes = [wintypes.DWORD]
kernel32.SetLastError.restype = None
kernel32.GetLastError.restype = wintypes.DWORD
kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
user32.SetWinEventHook.argtypes = [
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HMODULE,
    WINEVENTPROC,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
]
user32.SetWinEventHook.restype = wintypes.HANDLE
user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]
user32.UnhookWinEvent.restype = wintypes.BOOL
user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND,
    wintypes.DWORD,
    wintypes.BYTE,
    wintypes.DWORD,
]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.UINT,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.MessageBoxW.argtypes = [
    wintypes.HWND,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.UINT,
]
user32.MessageBoxW.restype = ctypes.c_int
user32.PostMessageW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostMessageW.restype = wintypes.BOOL
user32.InvalidateRect.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(RECT),
    wintypes.BOOL,
]
user32.InvalidateRect.restype = wintypes.BOOL
user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.BeginPaint.restype = wintypes.HDC
user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
user32.EndPaint.restype = wintypes.BOOL
user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(RECT), wintypes.HBRUSH]
user32.FillRect.restype = ctypes.c_int
user32.DrawTextW.argtypes = [
    wintypes.HDC,
    wintypes.LPCWSTR,
    ctypes.c_int,
    ctypes.POINTER(RECT),
    wintypes.UINT,
]
user32.DrawTextW.restype = ctypes.c_int
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.GetSysColorBrush.argtypes = [ctypes.c_int]
user32.GetSysColorBrush.restype = wintypes.HBRUSH
user32.GetSysColor.argtypes = [ctypes.c_int]
user32.GetSysColor.restype = wintypes.DWORD
user32.AdjustWindowRectEx.argtypes = [
    ctypes.POINTER(RECT),
    wintypes.DWORD,
    wintypes.BOOL,
    wintypes.DWORD,
]
user32.AdjustWindowRectEx.restype = wintypes.BOOL
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    wintypes.UINT_PTR,
    wintypes.LPCWSTR,
]
user32.AppendMenuW.restype = wintypes.BOOL
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.c_void_p,
]
user32.TrackPopupMenu.restype = wintypes.UINT
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.DestroyMenu.restype = wintypes.BOOL
user32.SetTimer.argtypes = [
    wintypes.HWND,
    wintypes.UINT_PTR,
    wintypes.UINT,
    ctypes.c_void_p,
]
user32.SetTimer.restype = wintypes.UINT_PTR
user32.KillTimer.argtypes = [wintypes.HWND, wintypes.UINT_PTR]
user32.KillTimer.restype = wintypes.BOOL
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATA)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
gdi32.SetBkMode.restype = ctypes.c_int
gdi32.SetBkColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetBkColor.restype = wintypes.COLORREF
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetTextColor.restype = wintypes.COLORREF
gdi32.BitBlt.argtypes = [
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HDC,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.DWORD,
]
gdi32.BitBlt.restype = wintypes.BOOL


overlay_instance = None
options_dialog = None
league_focused = False
single_instance_mutex = None

options_bg_brush = user32.GetSysColorBrush(COLOR_BTNFACE)
options_edit_brush = user32.GetSysColorBrush(COLOR_WINDOW)

user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.DefWindowProcW.restype = wintypes.LRESULT


def setup_logging():
    logger = logging.getLogger("cs_overlay")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = RotatingFileHandler(
        log_path, maxBytes=512 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(message)s")
    )
    logger.addHandler(handler)
    logger.info(
        "Logging started pid=%s frozen=%s runtime_dir=%s base_path=%s config_path=%s log_path=%s",
        os.getpid(),
        getattr(sys, "frozen", False),
        runtime_dir,
        base_path,
        config_path,
        log_path,
    )
    return logger


logger = setup_logging()
TASKBAR_CREATED = user32.RegisterWindowMessageW("TaskbarCreated")


def format_last_error():
    error_code = kernel32.GetLastError()
    if not error_code:
        return "0"
    return f"{error_code} ({ctypes.FormatError(error_code).strip()})"


def install_exception_logging():
    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.exception(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_exception

    if hasattr(threading, "excepthook"):
        def thread_exception_handler(args):
            logger.exception(
                "Unhandled thread exception in %s",
                args.thread.name if args.thread else "unknown",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = thread_exception_handler


def get_window_state_summary(hwnd):
    if not hwnd:
        return "hwnd=0"

    rect = RECT()
    rect_text = "unknown"
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        rect_text = f"{rect.left},{rect.top},{rect.right},{rect.bottom}"

    return (
        f"hwnd=0x{int(hwnd):X} "
        f"is_window={bool(user32.IsWindow(hwnd))} "
        f"is_visible={bool(user32.IsWindowVisible(hwnd))} "
        f"rect={rect_text}"
    )


def log_window_event(event, hwnd=None, **kwargs):
    details = [get_window_state_summary(hwnd or (overlay_instance.hwnd if overlay_instance else 0))]
    for key, value in kwargs.items():
        details.append(f"{key}={value}")
    logger.info("%s %s", event, " ".join(details))


def ensure_single_instance():
    global single_instance_mutex
    kernel32.SetLastError(0)
    mutex = kernel32.CreateMutexW(None, False, "Local\\CSOverlaySingleInstance")
    if not mutex:
        logger.warning("CreateMutexW failed last_error=%s", format_last_error())
        return True

    single_instance_mutex = mutex
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        logger.warning("Another CS Overlay instance is already running")
        user32.MessageBoxW(
            None,
            "CS Overlay is already running. Check the system tray for the existing instance.",
            "CS Overlay",
            MB_OK | MB_ICONINFORMATION,
        )
        kernel32.CloseHandle(single_instance_mutex)
        single_instance_mutex = None
        return False

    logger.info("Single-instance mutex acquired")
    return True


def release_single_instance():
    global single_instance_mutex
    if single_instance_mutex:
        kernel32.ReleaseMutex(single_instance_mutex)
        kernel32.CloseHandle(single_instance_mutex)
        logger.info("Single-instance mutex released")
        single_instance_mutex = None


def set_dpi_awareness():
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def get_window_title(hwnd):
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buffer, 512)
    return buffer.value


def get_process_name(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if not pid.value:
        return ""
    process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not process:
        return ""
    try:
        size = wintypes.DWORD(260)
        buffer = ctypes.create_unicode_buffer(260)
        if kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
            return os.path.basename(buffer.value)
    finally:
        kernel32.CloseHandle(process)
    return ""


def is_league_window(hwnd):
    if not hwnd:
        return False
    title = get_window_title(hwnd)
    if title in LEAGUE_TITLES:
        return True
    process_name = get_process_name(hwnd)
    return process_name in LEAGUE_PROCESS_NAMES


def update_focus_state(is_focused):
    global league_focused
    if is_focused != league_focused:
        league_focused = is_focused
        logger.info("League focus changed focused=%s", is_focused)
        if overlay_instance and overlay_instance.hwnd:
            user32.PostMessageW(
                overlay_instance.hwnd, WM_FOCUS_CHANGED, 1 if is_focused else 0, 0
            )


def check_league_focus():
    hwnd = user32.GetForegroundWindow()
    update_focus_state(is_league_window(hwnd))


def detection_callback(
    hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime
):
    if event == EVENT_SYSTEM_FOREGROUND:
        logger.info(
            "Foreground window changed hwnd=0x%X title=%r process=%r",
            int(hwnd) if hwnd else 0,
            get_window_title(hwnd),
            get_process_name(hwnd),
        )
        update_focus_state(is_league_window(hwnd))


win_event_proc = WINEVENTPROC(detection_callback)


def detection_thread():
    kernel32.SetLastError(0)
    hook = user32.SetWinEventHook(
        EVENT_SYSTEM_FOREGROUND,
        EVENT_SYSTEM_FOREGROUND,
        0,
        win_event_proc,
        0,
        0,
        WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS,
    )
    if not hook:
        logger.warning("SetWinEventHook failed last_error=%s", format_last_error())
    msg = wintypes.MSG()
    result = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
    while result > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
        result = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
    if result == -1:
        logger.error("Detection thread GetMessageW failed last_error=%s", format_last_error())
    if hook:
        user32.UnhookWinEvent(hook)


class OverlayWindow:
    def __init__(self):
        self.hwnd = None
        self.font = None
        self.font_size = 10
        self.custom_format = "{csmin}  CS/Min"
        self.update_interval_ms = 500
        self.focus_poll_interval_ms = 1000
        self.show_cs = False
        self.show_time = False
        self.show_csmin = False
        self.force_visible = False
        self.visible = False
        self.text = ""
        self.x = -10
        self.y = 60
        self.width = user32.GetSystemMetrics(0)
        self.height = user32.GetSystemMetrics(1)
        self.tray_icon = None
        self.tray_nid = None
        self.ocr = None
        self.ex_style = (
            WS_EX_LAYERED
            | WS_EX_TRANSPARENT
            | WS_EX_TOOLWINDOW
            | WS_EX_TOPMOST
            | WS_EX_NOACTIVATE
        )
        self.style = WS_POPUP

    def create_window(self):
        class_name = "CSOverlayWindow"
        hinst = kernel32.GetModuleHandleW(None)
        wndclass = WNDCLASS()
        wndclass.lpfnWndProc = overlay_wndproc
        wndclass.hInstance = hinst
        wndclass.lpszClassName = class_name
        wndclass.hCursor = user32.LoadCursorW(None, 32512)
        user32.RegisterClassW(ctypes.byref(wndclass))

        kernel32.SetLastError(0)
        self.hwnd = user32.CreateWindowExW(
            self.ex_style,
            class_name,
            "CS Overlay",
            self.style,
            self.x,
            self.y,
            self.width,
            self.height,
            None,
            None,
            hinst,
            None,
        )
        if not self.hwnd:
            logger.error("CreateWindowExW failed last_error=%s", format_last_error())
            raise ctypes.WinError()
        log_window_event("Overlay window created", self.hwnd)
        self.refresh_metrics()
        self.refresh_window_state(show_window=False)
        self.update_font()
        self.hide()

    def refresh_metrics(self):
        old_width = self.width
        old_height = self.height
        self.width = user32.GetSystemMetrics(0)
        self.height = user32.GetSystemMetrics(1)
        if self.width != old_width or self.height != old_height:
            logger.info(
                "Screen metrics updated width=%s height=%s old_width=%s old_height=%s",
                self.width,
                self.height,
                old_width,
                old_height,
            )

    def refresh_window_state(self, show_window):
        if not self.hwnd:
            return
        self.refresh_metrics()
        kernel32.SetLastError(0)
        if not user32.SetLayeredWindowAttributes(
            self.hwnd, rgb(0, 0, 0), 0, LWA_COLORKEY
        ):
            logger.warning(
                "SetLayeredWindowAttributes failed last_error=%s",
                format_last_error(),
            )
        kernel32.SetLastError(0)
        if not user32.SetWindowPos(
            self.hwnd,
            HWND_TOPMOST,
            self.x,
            self.y,
            self.width,
            self.height,
            SWP_NOACTIVATE
            | SWP_NOSENDCHANGING
            | (SWP_SHOWWINDOW if show_window else 0),
        ):
            logger.warning("SetWindowPos failed last_error=%s", format_last_error())
        log_window_event(
            "Overlay window refreshed",
            self.hwnd,
            show_window=show_window,
            force_visible=self.force_visible,
            visible_flag=self.visible,
            width=self.width,
            height=self.height,
            x=self.x,
            y=self.y,
        )

    def update_font(self):
        if self.font:
            gdi32.DeleteObject(self.font)
            self.font = None
        dpi = 96
        try:
            dpi = user32.GetDpiForWindow(self.hwnd)
        except Exception:
            pass
        lf = LOGFONTW()
        lf.lfHeight = -int(self.font_size * dpi / 72)
        lf.lfWeight = 700
        lf.lfQuality = 5
        lf.lfFaceName = "Segoe UI"
        self.font = gdi32.CreateFontIndirectW(ctypes.byref(lf))
        if not self.font:
            logger.warning("CreateFontIndirectW failed last_error=%s", format_last_error())
        else:
            logger.info("Overlay font updated font_size=%s dpi=%s", self.font_size, dpi)

    def update_position(self):
        self.refresh_window_state(show_window=self.visible or self.force_visible)

    def show(self):
        self.visible = True
        self.refresh_window_state(show_window=True)
        kernel32.SetLastError(0)
        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
        log_window_event(
            "Overlay show requested",
            self.hwnd,
            force_visible=self.force_visible,
            league_focused=league_focused,
        )
        self.update_display()

    def apply_timers(self):
        if not self.hwnd:
            return
        user32.KillTimer(self.hwnd, TIMER_UPDATE)
        user32.KillTimer(self.hwnd, TIMER_FOCUS_POLL)
        user32.SetTimer(self.hwnd, TIMER_UPDATE, self.update_interval_ms, None)
        user32.SetTimer(self.hwnd, TIMER_FOCUS_POLL, self.focus_poll_interval_ms, None)

    def hide(self):
        if not self.force_visible:
            self.visible = False
            kernel32.SetLastError(0)
            user32.ShowWindow(self.hwnd, SW_HIDE)
            log_window_event(
                "Overlay hide requested",
                self.hwnd,
                force_visible=self.force_visible,
                league_focused=league_focused,
            )

    def update_display(self):
        if not self.ocr:
            return
        cs_value = self.ocr.get_cs()
        current_time = gettime() if league_focused else 1
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
            except Exception:
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

        self.text = text
        if self.visible or self.force_visible:
            if not user32.InvalidateRect(self.hwnd, None, True):
                logger.warning("InvalidateRect failed last_error=%s", format_last_error())

    def on_timer(self, timer_id):
        if timer_id == TIMER_UPDATE:
            if self.visible or self.force_visible:
                self.update_display()
        elif timer_id == TIMER_FOCUS_POLL:
            check_league_focus()

    def handle_system_change(self, reason):
        logger.info("System change received reason=%s", reason)
        self.refresh_metrics()
        self.update_font()
        if self.visible or self.force_visible:
            self.refresh_window_state(show_window=True)
            self.update_display()
        else:
            self.refresh_window_state(show_window=False)

    def on_paint(self):
        ps = PAINTSTRUCT()
        hdc = user32.BeginPaint(self.hwnd, ctypes.byref(ps))
        if not hdc:
            logger.warning("BeginPaint returned null last_error=%s", format_last_error())
            return
        memdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, self.width, self.height)
        old_bmp = gdi32.SelectObject(memdc, bmp)

        rect = RECT(0, 0, self.width, self.height)
        brush = gdi32.CreateSolidBrush(rgb(0, 0, 0))
        user32.FillRect(memdc, ctypes.byref(rect), brush)
        gdi32.DeleteObject(brush)

        if self.font:
            gdi32.SelectObject(memdc, self.font)
        gdi32.SetBkMode(memdc, 1)
        gdi32.SetTextColor(memdc, rgb(255, 255, 255))

        flags = DT_RIGHT | DT_TOP | DT_NOPREFIX
        user32.DrawTextW(memdc, self.text, -1, ctypes.byref(rect), flags)

        gdi32.BitBlt(hdc, 0, 0, self.width, self.height, memdc, 0, 0, SRCCOPY)

        gdi32.SelectObject(memdc, old_bmp)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(memdc)
        user32.EndPaint(self.hwnd, ctypes.byref(ps))

    def create_tray(self):
        if self.tray_nid:
            return
        icon = user32.LoadImageW(
            None, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
        )
        if not icon:
            icon = user32.LoadIconW(None, 32512)
        self.tray_icon = icon

        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = icon
        nid.szTip = "CS Overlay"

        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        self.tray_nid = nid

    def remove_tray(self):
        if self.tray_nid:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.tray_nid))
            self.tray_nid = None
        if self.tray_icon:
            user32.DestroyIcon(self.tray_icon)
            self.tray_icon = None


class OptionsDialog:
    def __init__(self, overlay):
        self.overlay = overlay
        self.hwnd = None
        self.controls = {}

    def _layout_metrics(self):
        margin = 10
        label_w = 90
        input_w = 100
        row_h = 22
        row_gap = 4
        section_gap = 6
        format_h = 80
        instructions_h = 72
        btn_h = 24

        y = margin
        y += row_h + row_gap
        y += row_h + row_gap
        y += row_h + section_gap

        y += row_h + row_gap
        y += row_h + row_gap
        y += row_h + section_gap

        y += row_h
        y += format_h + section_gap
        y += instructions_h + section_gap

        btn_y = y
        client_height = btn_y + btn_h + margin

        return {
            "margin": margin,
            "label_w": label_w,
            "input_w": input_w,
            "row_h": row_h,
            "row_gap": row_gap,
            "section_gap": section_gap,
            "format_h": format_h,
            "instructions_h": instructions_h,
            "btn_h": btn_h,
            "btn_y": btn_y,
            "client_height": client_height,
        }

    def create(self):
        class_name = "CSOverlayOptions"
        hinst = kernel32.GetModuleHandleW(None)
        wndclass = WNDCLASS()
        wndclass.lpfnWndProc = options_wndproc
        wndclass.hInstance = hinst
        wndclass.lpszClassName = class_name
        wndclass.hCursor = user32.LoadCursorW(None, 32512)
        wndclass.hbrBackground = ctypes.c_void_p(COLOR_BTNFACE + 1)
        user32.RegisterClassW(ctypes.byref(wndclass))

        metrics = self._layout_metrics()
        client_width = 420
        rect = RECT(0, 0, client_width, metrics["client_height"])
        style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU
        user32.AdjustWindowRectEx(ctypes.byref(rect), style, False, 0)
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        x = int((screen_w - width) / 2)
        y = int((screen_h - height) / 2)

        style = style | WS_VISIBLE
        self.hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "Options",
            style,
            x,
            y,
            width,
            height,
            None,
            None,
            hinst,
            None,
        )
        self._init_controls()
        user32.ShowWindow(self.hwnd, 1)
        user32.SetForegroundWindow(self.hwnd)

    def _init_controls(self):
        metrics = self._layout_metrics()
        margin = metrics["margin"]
        label_w = metrics["label_w"]
        input_w = metrics["input_w"]
        row_h = metrics["row_h"]
        row_gap = metrics["row_gap"]
        section_gap = metrics["section_gap"]
        y = margin

        default_font = gdi32.GetStockObject(17)

        def add_label(text, x, y, w, h):
            hwnd = user32.CreateWindowExW(
                0,
                "STATIC",
                text,
                WS_CHILD | WS_VISIBLE,
                x,
                y,
                w,
                h,
                self.hwnd,
                None,
                None,
                None,
            )
            user32.SendMessageW(hwnd, 0x0030, default_font, 1)
            return hwnd

        def add_edit(x, y, w, h, ctrl_id, multiline=False):
            style = WS_CHILD | WS_VISIBLE | WS_BORDER | WS_TABSTOP
            if multiline:
                style |= ES_MULTILINE | ES_AUTOVSCROLL | ES_WANTRETURN | WS_VSCROLL
            hwnd = user32.CreateWindowExW(
                0,
                "EDIT",
                "",
                style,
                x,
                y,
                w,
                h,
                self.hwnd,
                ctypes.c_void_p(ctrl_id),
                None,
                None,
            )
            user32.SendMessageW(hwnd, 0x0030, default_font, 1)
            return hwnd

        add_label("Overlay X:", margin, y, label_w, row_h)
        self.controls["x"] = add_edit(margin + label_w, y, input_w, row_h, 1001)
        y += row_h + row_gap
        add_label("Overlay Y:", margin, y, label_w, row_h)
        self.controls["y"] = add_edit(margin + label_w, y, input_w, row_h, 1002)
        y += row_h + row_gap
        add_label("Font Size:", margin, y, label_w, row_h)
        self.controls["font"] = add_edit(margin + label_w, y, input_w, row_h, 1003)
        y += row_h + section_gap

        add_label("Advanced (ms):", margin, y, 140, row_h)
        y += row_h + row_gap
        add_label("Update Poll:", margin, y, label_w, row_h)
        self.controls["update_ms"] = add_edit(margin + label_w, y, input_w, row_h, 1005)
        y += row_h + row_gap
        add_label("Focus Poll:", margin, y, label_w, row_h)
        self.controls["focus_ms"] = add_edit(margin + label_w, y, input_w, row_h, 1006)
        y += row_h + section_gap

        add_label("Custom Format:", margin, y, label_w, row_h)
        y += row_h
        self.controls["format"] = add_edit(
            margin, y, 380, metrics["format_h"], 1004, multiline=True
        )
        y += metrics["format_h"] + section_gap

        instructions = (
            "Instructions:\r\n"
            "- Use {cs} to display the CS count\r\n"
            "- Use {time} to display the current time (MM:SS)\r\n"
            "- Use {csmin} to display the CS per minute\r\n"
            "Multi-line format is allowed."
        )
        add_label(instructions, margin, y, 380, metrics["instructions_h"])

        btn_y = metrics["btn_y"]
        btn_w = 80
        btn_h = metrics["btn_h"]
        gap = 10
        btn_x = margin

        self.controls["apply"] = user32.CreateWindowExW(
            0,
            "BUTTON",
            "Apply",
            WS_CHILD | WS_VISIBLE,
            btn_x,
            btn_y,
            btn_w,
            btn_h,
            self.hwnd,
            ctypes.c_void_p(2001),
            None,
            None,
        )
        user32.SendMessageW(self.controls["apply"], 0x0030, default_font, 1)

        btn_x += btn_w + gap
        self.controls["ok"] = user32.CreateWindowExW(
            0,
            "BUTTON",
            "OK",
            WS_CHILD | WS_VISIBLE,
            btn_x,
            btn_y,
            btn_w,
            btn_h,
            self.hwnd,
            ctypes.c_void_p(2002),
            None,
            None,
        )
        user32.SendMessageW(self.controls["ok"], 0x0030, default_font, 1)

        btn_x += btn_w + gap
        self.controls["cancel"] = user32.CreateWindowExW(
            0,
            "BUTTON",
            "Cancel",
            WS_CHILD | WS_VISIBLE,
            btn_x,
            btn_y,
            btn_w,
            btn_h,
            self.hwnd,
            ctypes.c_void_p(2003),
            None,
            None,
        )
        user32.SendMessageW(self.controls["cancel"], 0x0030, default_font, 1)

        user32.SetWindowTextW(self.controls["x"], str(self.overlay.x))
        user32.SetWindowTextW(self.controls["y"], str(self.overlay.y))
        user32.SetWindowTextW(self.controls["font"], str(self.overlay.font_size))
        user32.SetWindowTextW(
            self.controls["update_ms"], str(self.overlay.update_interval_ms)
        )
        user32.SetWindowTextW(
            self.controls["focus_ms"], str(self.overlay.focus_poll_interval_ms)
        )
        if self.overlay.custom_format:
            user32.SetWindowTextW(
                self.controls["format"],
                self.overlay.custom_format.replace("\n", "\r\n"),
            )

    def _get_text(self, key):
        hwnd = self.controls.get(key)
        if not hwnd:
            return ""
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    def apply_changes(self):
        try:
            x = int(self._get_text("x").strip())
        except Exception:
            x = self.overlay.x
        try:
            y = int(self._get_text("y").strip())
        except Exception:
            y = self.overlay.y
        try:
            font = int(self._get_text("font").strip())
        except Exception:
            font = self.overlay.font_size
        try:
            update_ms = int(self._get_text("update_ms").strip())
        except Exception:
            update_ms = self.overlay.update_interval_ms
        try:
            focus_ms = int(self._get_text("focus_ms").strip())
        except Exception:
            focus_ms = self.overlay.focus_poll_interval_ms

        update_ms = max(MIN_TIMER_MS, min(MAX_TIMER_MS, update_ms))
        focus_ms = max(MIN_TIMER_MS, min(MAX_TIMER_MS, focus_ms))

        fmt = self._get_text("format").strip()
        fmt = fmt.replace("\r\n", "\n")
        self.overlay.custom_format = fmt if fmt != "" else None
        self.overlay.x = x
        self.overlay.y = y
        self.overlay.font_size = font
        self.overlay.update_interval_ms = update_ms
        self.overlay.focus_poll_interval_ms = focus_ms
        self.overlay.update_position()
        self.overlay.update_font()
        self.overlay.apply_timers()
        self.overlay.update_display()


def open_options():
    global options_dialog
    if options_dialog and options_dialog.hwnd and user32.IsWindow(options_dialog.hwnd):
        logger.info("Options already open; foregrounding existing dialog")
        user32.SetForegroundWindow(options_dialog.hwnd)
        return
    overlay_instance.force_visible = True
    logger.info("Opening options dialog and forcing overlay visible")
    overlay_instance.show()
    options_dialog = OptionsDialog(overlay_instance)
    options_dialog.create()


@WNDPROC
def overlay_wndproc(hwnd, msg, wparam, lparam):
    if msg == TASKBAR_CREATED:
        logger.info("TaskbarCreated received; recreating tray icon")
        overlay_instance.remove_tray()
        overlay_instance.create_tray()
        return 0
    if msg == WM_PAINT:
        overlay_instance.on_paint()
        return 0
    if msg == WM_TIMER:
        overlay_instance.on_timer(wparam)
        return 0
    if msg == WM_NCHITTEST:
        return HTTRANSPARENT
    if msg == WM_TRAYICON:
        if lparam == 0x0203:
            open_options()
        elif lparam == 0x0205:
            cursor = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(cursor))
            menu = user32.CreatePopupMenu()
            user32.AppendMenuW(menu, 0, ID_TRAY_OPTIONS, "Options")
            user32.AppendMenuW(menu, 0, ID_TRAY_EXIT, "Exit")
            user32.SetForegroundWindow(hwnd)
            cmd = user32.TrackPopupMenu(
                menu,
                TPM_RETURNCMD | TPM_NONOTIFY,
                cursor.x,
                cursor.y,
                0,
                hwnd,
                None,
            )
            if cmd == ID_TRAY_OPTIONS:
                open_options()
            elif cmd == ID_TRAY_EXIT:
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            user32.DestroyMenu(menu)
        return 0
    if msg == WM_FOCUS_CHANGED:
        if wparam:
            overlay_instance.show()
        else:
            overlay_instance.hide()
        return 0
    if msg in (WM_DISPLAYCHANGE, WM_DPICHANGED, WM_SETTINGCHANGE, WM_DWMCOMPOSITIONCHANGED):
        message_name = {
            WM_DISPLAYCHANGE: "WM_DISPLAYCHANGE",
            WM_DPICHANGED: "WM_DPICHANGED",
            WM_SETTINGCHANGE: "WM_SETTINGCHANGE",
            WM_DWMCOMPOSITIONCHANGED: "WM_DWMCOMPOSITIONCHANGED",
        }.get(msg, str(msg))
        overlay_instance.handle_system_change(message_name)
        return 0
    if msg == WM_CLOSE:
        user32.DestroyWindow(hwnd)
        return 0
    if msg == WM_DESTROY:
        overlay_instance.remove_tray()
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


@WNDPROC
def options_wndproc(hwnd, msg, wparam, lparam):
    global options_dialog
    if msg == WM_CTLCOLORSTATIC:
        hdc = wparam
        gdi32.SetTextColor(hdc, rgb(0, 0, 0))
        gdi32.SetBkMode(hdc, 2)
        gdi32.SetBkColor(hdc, user32.GetSysColor(COLOR_BTNFACE))
        return options_bg_brush
    if msg == WM_CTLCOLOREDIT:
        hdc = wparam
        gdi32.SetTextColor(hdc, rgb(0, 0, 0))
        gdi32.SetBkMode(hdc, 2)
        gdi32.SetBkColor(hdc, user32.GetSysColor(COLOR_WINDOW))
        return options_edit_brush
    if msg == WM_COMMAND:
        command_id = wparam & 0xFFFF
        if command_id == 2001:
            options_dialog.apply_changes()
            return 0
        if command_id == 2002:
            options_dialog.apply_changes()
            user32.DestroyWindow(hwnd)
            return 0
        if command_id == 2003:
            user32.DestroyWindow(hwnd)
            return 0
    if msg == WM_CLOSE:
        user32.DestroyWindow(hwnd)
        return 0
    if msg == WM_DESTROY:
        options_dialog = None
        overlay_instance.force_visible = False
        if not league_focused:
            overlay_instance.hide()
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def load_config():
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "x": -10,
            "y": 60,
            "custom_format": "{csmin}  CS/Min",
            "font_size": 10,
            "update_interval_ms": 500,
            "focus_poll_interval_ms": 1000,
        }


def save_config(config):
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def main():
    set_dpi_awareness()
    install_exception_logging()
    if not ensure_single_instance():
        return
    global overlay_instance
    overlay_instance = OverlayWindow()
    overlay_instance.create_window()
    overlay_instance.ocr = CSOCR()
    logger.info("Overlay OCR initialized")

    config = load_config()
    overlay_instance.x = config.get("x", overlay_instance.x)
    overlay_instance.y = config.get("y", overlay_instance.y)
    overlay_instance.custom_format = config.get(
        "custom_format", overlay_instance.custom_format
    )
    overlay_instance.font_size = config.get("font_size", overlay_instance.font_size)
    overlay_instance.update_interval_ms = config.get(
        "update_interval_ms", overlay_instance.update_interval_ms
    )
    overlay_instance.focus_poll_interval_ms = config.get(
        "focus_poll_interval_ms", overlay_instance.focus_poll_interval_ms
    )
    overlay_instance.update_interval_ms = max(
        MIN_TIMER_MS, min(MAX_TIMER_MS, overlay_instance.update_interval_ms)
    )
    overlay_instance.focus_poll_interval_ms = max(
        MIN_TIMER_MS, min(MAX_TIMER_MS, overlay_instance.focus_poll_interval_ms)
    )
    overlay_instance.update_position()
    overlay_instance.update_font()

    overlay_instance.create_tray()
    logger.info("Tray icon created")

    overlay_instance.apply_timers()
    logger.info(
        "Timers applied update_interval_ms=%s focus_poll_interval_ms=%s",
        overlay_instance.update_interval_ms,
        overlay_instance.focus_poll_interval_ms,
    )

    t = threading.Thread(target=detection_thread, daemon=True, name="focus-detection")
    t.start()
    logger.info("Focus detection thread started")

    check_league_focus()

    msg = wintypes.MSG()
    result = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
    while result > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
        result = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
    if result == -1:
        logger.error("Main loop GetMessageW failed last_error=%s", format_last_error())
    release_single_instance()

    config = {
        "x": overlay_instance.x,
        "y": overlay_instance.y,
        "custom_format": overlay_instance.custom_format,
        "font_size": overlay_instance.font_size,
        "update_interval_ms": overlay_instance.update_interval_ms,
        "focus_poll_interval_ms": overlay_instance.focus_poll_interval_ms,
    }
    save_config(config)


if __name__ == "__main__":
    main()
