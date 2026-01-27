import ctypes
import ctypes.wintypes as wintypes
import json
import ssl
import urllib.request

from digits import TARGET_DIGITS


user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0


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
        top = 5
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


def gettime():
    """Returns the time in seconds since the start of the game"""
    try:
        ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(
            "https://127.0.0.1:2999/liveclientdata/gamestats", context=ctx, timeout=0.2
        ) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("gameTime", 0) / 60
    except Exception:
        return 1
