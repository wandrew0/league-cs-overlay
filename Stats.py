import ctypes
import ctypes.wintypes as wintypes
import json
import logging

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
WINHTTP_FLAG_SECURE = 0x00800000
WINHTTP_OPTION_SECURITY_FLAGS = 31

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

    def get_cs(self, debug=False) -> int:
        screen_width = user32.GetSystemMetrics(0)
        left = screen_width - 138
        top = 6
        right = screen_width - 108
        bottom = 25
        width = right - left
        height = bottom - top

        data = capture_grayscale(left, top, width, height)

        digits = []
        x = 0
        currdigit = self.most_similar_digit(
            self._extract_digit(
                data, width, x, digit_top=3, digit_width=10, digit_height=12
            )
        )
        while currdigit != "":
            digits.append(currdigit)
            if len(digits) == 1 and currdigit == "1":
                x += 9
            else:
                x += 10
            currdigit = self.most_similar_digit(
                self._extract_digit(
                    data, width, x, digit_top=3, digit_width=10, digit_height=12
                )
            )

        string = "".join(digits)
        number = int(string) if string else 0
        if debug:
            if number < self.prev or number > self.prev + 1:
                print(f"prev: {self.prev}, curr: {number}")
                print(data)
        self.prev = number
        return number

    def _extract_digit(self, data, width, x, digit_top, digit_width, digit_height):
        if x < 0 or x + digit_width > width:
            return []
        pixels = []
        for row in range(digit_height):
            offset = (digit_top + row) * width + x
            pixels.extend(data[offset : offset + digit_width])
        return pixels

    def most_similar_digit(self, digit_data) -> str:
        if not digit_data or len(digit_data) != len(self.target_digits[0]):
            return ""
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
        return str(min_index) if min_index != 10 else ""


def _ensure_winhttp_handles():
    global _winhttp_session, _winhttp_connection
    if not _winhttp_session:
        _winhttp_session = winhttp.WinHttpOpen(
            "CS Overlay/1.0",
            WINHTTP_ACCESS_TYPE_NO_PROXY,
            WINHTTP_NO_PROXY_NAME,
            WINHTTP_NO_PROXY_BYPASS,
            0,
        )
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


def gettime():
    """Returns the time in minutes since the start of the game"""
    if not _ensure_winhttp_handles():
        return 1

    request = None
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
            return 1

        security_flags = wintypes.DWORD(WINHTTP_SECURITY_FLAGS)
        winhttp.WinHttpSetOption(
            request,
            WINHTTP_OPTION_SECURITY_FLAGS,
            ctypes.byref(security_flags),
            ctypes.sizeof(security_flags),
        )

        if not winhttp.WinHttpSendRequest(request, None, 0, None, 0, 0, None):
            _close_winhttp_handles()
            return 1
        if not winhttp.WinHttpReceiveResponse(request, None):
            _close_winhttp_handles()
            return 1

        chunks = bytearray()
        available = wintypes.DWORD()
        bytes_read = wintypes.DWORD()
        while True:
            available.value = 0
            if not winhttp.WinHttpQueryDataAvailable(request, ctypes.byref(available)):
                _close_winhttp_handles()
                return 1
            if not available.value:
                break
            buffer = ctypes.create_string_buffer(available.value)
            bytes_read.value = 0
            if not winhttp.WinHttpReadData(
                request, buffer, available.value, ctypes.byref(bytes_read)
            ):
                _close_winhttp_handles()
                return 1
            chunks.extend(buffer.raw[: bytes_read.value])

        payload = json.loads(chunks.decode("utf-8"))
        return payload.get("gameTime", 0) / 60
    except Exception as exc:
        logger.debug("WinHTTP game time request failed: %s", exc)
        _close_winhttp_handles()
        return 1
    finally:
        if request:
            winhttp.WinHttpCloseHandle(request)
