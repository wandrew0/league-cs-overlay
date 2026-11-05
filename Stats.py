import ctypes
import ctypes.wintypes as wintypes
import json
import logging
import math
import threading
import time

from digits import TARGET_DIGITS


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
winhttp = ctypes.windll.winhttp

logger = logging.getLogger("cs_overlay")

SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0

WINHTTP_ACCESS_TYPE_NO_PROXY = 1
WINHTTP_NO_PROXY_NAME = None
WINHTTP_NO_PROXY_BYPASS = None
WINHTTP_NO_REFERER = None
WINHTTP_DEFAULT_ACCEPT_TYPES = ctypes.POINTER(wintypes.LPCWSTR)()
WINHTTP_FLAG_ASYNC = 0x10000000
WINHTTP_FLAG_SECURE = 0x00800000
WINHTTP_OPTION_CONTEXT_VALUE = 45
WINHTTP_OPTION_SECURITY_FLAGS = 31
HTTP_TIMEOUT_MS = 500
HTTP_BUDGET_SECONDS = 2.0
HTTP_MAX_RESPONSE_BYTES = 64 * 1024
WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING = 0x00000800
WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE = 0x00020000
WINHTTP_CALLBACK_STATUS_READ_COMPLETE = 0x00080000
WINHTTP_CALLBACK_STATUS_REQUEST_ERROR = 0x00200000
WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE = 0x00400000
HTTP_CALLBACK_FLAGS = (
    WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING
    | WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE
    | WINHTTP_CALLBACK_STATUS_READ_COMPLETE
    | WINHTTP_CALLBACK_STATUS_REQUEST_ERROR
    | WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE
)
WINHTTP_STATUS_CALLBACK = ctypes.WINFUNCTYPE(
    None, wintypes.HANDLE, ctypes.c_size_t, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD,
)

SECURITY_FLAG_IGNORE_UNKNOWN_CA = 0x00000100
SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE = 0x00000200
SECURITY_FLAG_IGNORE_CERT_CN_INVALID = 0x00001000
SECURITY_FLAG_IGNORE_CERT_DATE_INVALID = 0x00002000

WINHTTP_SECURITY_FLAGS = (
    SECURITY_FLAG_IGNORE_UNKNOWN_CA
    | SECURITY_FLAG_IGNORE_CERT_WRONG_USAGE
    | SECURITY_FLAG_IGNORE_CERT_CN_INVALID
    | SECURITY_FLAG_IGNORE_CERT_DATE_INVALID
)

logger = logging.getLogger("cs_overlay")

_winhttp_session = None
_winhttp_connection = None
# Keep async read buffers alive until WinHTTP's final HANDLE_CLOSING callback.
_http_requests = {}

BASE_SCREEN_HEIGHT = 1080
BASE_CAPTURE_LEFT_OFFSET = 138
BASE_CAPTURE_RIGHT_OFFSET = 108
BASE_CAPTURE_TOP = 6
BASE_CAPTURE_BOTTOM = 25
BASE_DIGIT_TOP = 3
BASE_DIGIT_WIDTH = 10
BASE_DIGIT_HEIGHT = 12
BASE_FIRST_DIGIT_SPACING = 9
BASE_DIGIT_SPACING = 10
SCALED_NON_LEADING_OFFSETS = (1, 2)


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
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
gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    wintypes.HBITMAP,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
]
gdi32.GetDIBits.restype = ctypes.c_int
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

winhttp.WinHttpOpen.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
]
winhttp.WinHttpOpen.restype = wintypes.HANDLE
winhttp.WinHttpSetTimeouts.argtypes = [wintypes.HANDLE] + [ctypes.c_int] * 4
winhttp.WinHttpSetTimeouts.restype = wintypes.BOOL
winhttp.WinHttpSetStatusCallback.argtypes = [
    wintypes.HANDLE, WINHTTP_STATUS_CALLBACK, wintypes.DWORD, ctypes.c_size_t,
]
winhttp.WinHttpSetStatusCallback.restype = ctypes.c_void_p
winhttp.WinHttpConnect.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCWSTR,
    wintypes.WORD,
    wintypes.DWORD,
]
winhttp.WinHttpConnect.restype = wintypes.HANDLE
winhttp.WinHttpOpenRequest.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    ctypes.POINTER(wintypes.LPCWSTR),
    wintypes.DWORD,
]
winhttp.WinHttpOpenRequest.restype = wintypes.HANDLE
winhttp.WinHttpSetOption.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
]
winhttp.WinHttpSetOption.restype = wintypes.BOOL
winhttp.WinHttpSendRequest.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_void_p,
]
winhttp.WinHttpSendRequest.restype = wintypes.BOOL
winhttp.WinHttpReceiveResponse.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
winhttp.WinHttpReceiveResponse.restype = wintypes.BOOL
winhttp.WinHttpQueryDataAvailable.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.DWORD),
]
winhttp.WinHttpQueryDataAvailable.restype = wintypes.BOOL
winhttp.WinHttpReadData.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]
winhttp.WinHttpReadData.restype = wintypes.BOOL
winhttp.WinHttpCloseHandle.argtypes = [wintypes.HANDLE]
winhttp.WinHttpCloseHandle.restype = wintypes.BOOL


def capture_grayscale(left, top, width, height):
    hdc_screen = user32.GetDC(None)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
    old_obj = gdi32.SelectObject(hdc_mem, hbmp)
    buf_len = width * height * 4
    buffer = (ctypes.c_ubyte * buf_len)()
    try:
        gdi32.BitBlt(hdc_mem, 0, 0, width, height, hdc_screen, left, top, SRCCOPY)

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        gdi32.GetDIBits(
            hdc_mem, hbmp, 0, height, buffer, ctypes.byref(bmi), DIB_RGB_COLORS
        )
    finally:
        gdi32.SelectObject(hdc_mem, old_obj)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(None, hdc_screen)

    grayscale = []
    for i in range(0, buf_len, 4):
        b = buffer[i]
        g = buffer[i + 1]
        r = buffer[i + 2]
        gray = (r * 299 + g * 587 + b * 114) // 1000
        grayscale.append(gray)
    return grayscale


class CSOCR:
    """Class to convert image captured from the game to text"""

    def __init__(self):
        self.target_digits = TARGET_DIGITS
        self.counter = 0
        self.prev = 0
        self.last_capture_signature = None

    def get_cs(self, debug=False) -> int:
        geometry = self._capture_geometry()
        left = geometry["left"]
        top = geometry["top"]
        right = geometry["right"]
        bottom = geometry["bottom"]
        width = right - left
        height = bottom - top
        capture_width = width
        if geometry["scale"] > 1.0:
            capture_width += max(SCALED_NON_LEADING_OFFSETS)

        self._log_capture_geometry(geometry)
        data = capture_grayscale(left, top, capture_width, height)

        result = self._read_digits(data, capture_width, geometry, offset_x=0)
        first_digit = result["digits"][:1]
        if geometry["scale"] > 1.0 and first_digit not in ("", "1"):
            candidates = [
                self._read_digits(data, capture_width, geometry, offset_x=offset)
                for offset in SCALED_NON_LEADING_OFFSETS
            ]
            valid_candidates = [candidate for candidate in candidates if candidate["digits"]]
            if valid_candidates:
                result = min(
                    valid_candidates,
                    key=lambda candidate: candidate["average_mse"],
                )

        string = result["digits"]
        number = int(string) if string else 0
        if debug:
            if number < self.prev or number > self.prev + 1:
                print(f"prev: {self.prev}, curr: {number}")
                print(data)
        self.prev = number
        return number

    def _capture_geometry(self):
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        scale = screen_height / BASE_SCREEN_HEIGHT if screen_height else 1.0

        def scaled(value):
            return max(1, int(round(value * scale)))

        left_offset = scaled(BASE_CAPTURE_LEFT_OFFSET)
        right_offset = scaled(BASE_CAPTURE_RIGHT_OFFSET)
        top = scaled(BASE_CAPTURE_TOP)
        bottom = scaled(BASE_CAPTURE_BOTTOM)
        digit_width = scaled(BASE_DIGIT_WIDTH)
        digit_height = scaled(BASE_DIGIT_HEIGHT)
        left_padding = 1 if scale > 1.0 else 0

        return {
            "screen_width": screen_width,
            "screen_height": screen_height,
            "scale": scale,
            "left": screen_width - left_offset - left_padding,
            "top": top,
            "right": screen_width - right_offset,
            "bottom": bottom,
            "left_padding": left_padding,
            "digit_top": scaled(BASE_DIGIT_TOP),
            "digit_width": digit_width,
            "digit_height": digit_height,
            "first_digit_spacing": scaled(BASE_FIRST_DIGIT_SPACING),
            "digit_spacing": scaled(BASE_DIGIT_SPACING),
        }

    def _log_capture_geometry(self, geometry):
        signature = (
            geometry["screen_width"],
            geometry["screen_height"],
            geometry["left"],
            geometry["top"],
            geometry["right"],
            geometry["bottom"],
            geometry["left_padding"],
            geometry["digit_top"],
            geometry["digit_width"],
            geometry["digit_height"],
        )
        if signature == self.last_capture_signature:
            return
        self.last_capture_signature = signature
        logger.info(
            "OCR capture geometry screen=%sx%s scale=%.3f bounds=%s,%s,%s,%s left_padding=%s digit_top=%s digit_size=%sx%s spacing=%s/%s",
            geometry["screen_width"],
            geometry["screen_height"],
            geometry["scale"],
            geometry["left"],
            geometry["top"],
            geometry["right"],
            geometry["bottom"],
            geometry["left_padding"],
            geometry["digit_top"],
            geometry["digit_width"],
            geometry["digit_height"],
            geometry["first_digit_spacing"],
            geometry["digit_spacing"],
        )

    def _extract_digit(self, data, width, x, digit_top, digit_width, digit_height):
        if x < 0 or x + digit_width > width:
            return []
        pixels = []
        for row in range(digit_height):
            offset = (digit_top + row) * width + x
            pixels.extend(data[offset : offset + digit_width])
        if digit_width != BASE_DIGIT_WIDTH or digit_height != BASE_DIGIT_HEIGHT:
            return self._resize_digit(
                pixels,
                digit_width,
                digit_height,
                BASE_DIGIT_WIDTH,
                BASE_DIGIT_HEIGHT,
            )
        return pixels

    def _read_digits(self, data, width, geometry, offset_x=0):
        digits = []
        matches = []
        x = offset_x
        currdigit, mse = self._most_similar_digit_with_mse(
            self._extract_digit(
                data,
                width,
                x,
                digit_top=geometry["digit_top"],
                digit_width=geometry["digit_width"],
                digit_height=geometry["digit_height"],
            )
        )
        while currdigit != "":
            digits.append(currdigit)
            matches.append(mse)
            if len(digits) == 1 and currdigit == "1":
                x += geometry["first_digit_spacing"]
            else:
                x += geometry["digit_spacing"]
            currdigit, mse = self._most_similar_digit_with_mse(
                self._extract_digit(
                    data,
                    width,
                    x,
                    digit_top=geometry["digit_top"],
                    digit_width=geometry["digit_width"],
                    digit_height=geometry["digit_height"],
                )
            )

        return {
            "digits": "".join(digits),
            "offset_x": offset_x,
            "average_mse": sum(matches) / len(matches) if matches else float("inf"),
        }

    def _resize_digit(self, pixels, source_width, source_height, target_width, target_height):
        resized = []
        for target_y in range(target_height):
            y0 = int(target_y * source_height / target_height)
            y1 = int((target_y + 1) * source_height / target_height)
            y1 = max(y0 + 1, y1)
            for target_x in range(target_width):
                x0 = int(target_x * source_width / target_width)
                x1 = int((target_x + 1) * source_width / target_width)
                x1 = max(x0 + 1, x1)
                total = 0
                count = 0
                for source_y in range(y0, min(y1, source_height)):
                    offset = source_y * source_width
                    for source_x in range(x0, min(x1, source_width)):
                        total += pixels[offset + source_x]
                        count += 1
                resized.append(total // count if count else 0)
        return resized

    def most_similar_digit(self, digit_data) -> str:
        digit, _mse = self._most_similar_digit_with_mse(digit_data)
        return digit

    def _most_similar_digit_with_mse(self, digit_data):
        if not digit_data or len(digit_data) != len(self.target_digits[0]):
            return "", float("inf")
        min_mse = None
        min_index = 0
        for index, target in enumerate(self.target_digits):
            mse = 0
            for a, b in zip(target, digit_data):
                diff = a - b
                mse += diff * diff
            mse /= len(target)
            if min_mse is None or mse < min_mse:
                min_mse = mse
                min_index = index
        digit = str(min_index) if min_index != 10 else ""
        return digit, min_mse


def _ensure_winhttp_handles():
    global _winhttp_session, _winhttp_connection
    if not _winhttp_session:
        _winhttp_session = winhttp.WinHttpOpen(
            "CS Overlay/1.0",
            WINHTTP_ACCESS_TYPE_NO_PROXY,
            WINHTTP_NO_PROXY_NAME,
            WINHTTP_NO_PROXY_BYPASS,
            WINHTTP_FLAG_ASYNC,
        )
        if _winhttp_session and not winhttp.WinHttpSetTimeouts(
            _winhttp_session, HTTP_TIMEOUT_MS, HTTP_TIMEOUT_MS,
            HTTP_TIMEOUT_MS, HTTP_TIMEOUT_MS,
        ):
            _close_winhttp_handles()
            return False
    if _winhttp_session and not _winhttp_connection:
        _winhttp_connection = winhttp.WinHttpConnect(
            _winhttp_session, "127.0.0.1", 2999, 0
        )
    return _winhttp_session and _winhttp_connection


def _close_winhttp_handles():
    global _winhttp_session, _winhttp_connection
    if _winhttp_connection:
        winhttp.WinHttpCloseHandle(_winhttp_connection)
        _winhttp_connection = None
    if _winhttp_session:
        winhttp.WinHttpCloseHandle(_winhttp_session)
        _winhttp_session = None


@WINHTTP_STATUS_CALLBACK
def _http_status_callback(handle, context, status, info, length):
    if status == WINHTTP_CALLBACK_STATUS_HANDLE_CLOSING:
        _http_requests.pop(context, None)
        return
    state = _http_requests.get(context)
    if state is not None:
        state["status"] = status
        state["length"] = length
        state["ready"].set()


def gettime():
    """Worker-only blocking interface, with a deadline including the TLS handshake."""
    if not _ensure_winhttp_handles():
        return None

    request = None
    failed = True
    deadline = time.monotonic() + HTTP_BUDGET_SECONDS
    state = {"ready": threading.Event(), "buffer": ctypes.create_string_buffer(8192)}
    context = id(state)

    def complete(function, expected_status, *args):
        state["ready"].clear()
        if time.monotonic() >= deadline:
            raise TimeoutError("Game time request exceeded its time budget")
        if not function(request, *args):
            raise OSError("WinHTTP operation failed")
        if not state["ready"].wait(max(0, deadline - time.monotonic())):
            raise TimeoutError("Game time request exceeded its time budget")
        if state["status"] != expected_status:
            raise OSError("WinHTTP request failed")
        return state["length"]

    try:
        request = winhttp.WinHttpOpenRequest(
            _winhttp_connection,
            "GET",
            "/liveclientdata/gamestats",
            None,
            WINHTTP_NO_REFERER,
            WINHTTP_DEFAULT_ACCEPT_TYPES,
            WINHTTP_FLAG_SECURE,
        )
        if not request:
            return None

        security_flags = wintypes.DWORD(WINHTTP_SECURITY_FLAGS)
        context_value = ctypes.c_size_t(context)
        for option, value in (
            (WINHTTP_OPTION_SECURITY_FLAGS, security_flags),
            (WINHTTP_OPTION_CONTEXT_VALUE, context_value),
        ):
            if not winhttp.WinHttpSetOption(request, option, ctypes.byref(value), ctypes.sizeof(value)):
                raise OSError("Could not configure WinHTTP request")
        _http_requests[context] = state
        previous = winhttp.WinHttpSetStatusCallback(request, _http_status_callback, HTTP_CALLBACK_FLAGS, 0)
        if previous == ctypes.c_void_p(-1).value:
            _http_requests.pop(context, None)
            raise OSError("Could not register WinHTTP callback")

        # Async WinHTTP permits safe cancellation after a bounded worker wait.
        # Closing a handle from another thread during a synchronous call is unsafe.
        complete(winhttp.WinHttpSendRequest, WINHTTP_CALLBACK_STATUS_SENDREQUEST_COMPLETE,
                 None, 0, None, 0, 0, context)
        complete(winhttp.WinHttpReceiveResponse, WINHTTP_CALLBACK_STATUS_HEADERS_AVAILABLE, None)
        chunks = bytearray()
        while True:
            count = complete(winhttp.WinHttpReadData, WINHTTP_CALLBACK_STATUS_READ_COMPLETE,
                             state["buffer"], len(state["buffer"]), None)
            if not count:
                break
            if len(chunks) + count > HTTP_MAX_RESPONSE_BYTES:
                raise ValueError("Game time response is too large")
            chunks.extend(state["buffer"].raw[:count])

        minutes = float(json.loads(chunks.decode("utf-8"))["gameTime"]) / 60
        if not math.isfinite(minutes) or minutes < 0:
            raise ValueError("Invalid game time")
        failed = False
        return minutes
    except Exception as exc:
        logger.debug("WinHTTP game time request failed: %s", exc)
        return None
    finally:
        if request:
            winhttp.WinHttpCloseHandle(request)
        if failed:
            _close_winhttp_handles()
