import numpy as np
from PIL import Image
from mss import mss
import requests
import urllib3

class CSOCR:
    """ Class to convert image captured from the game to text """
    def __init__(self):
        # An array of size 11 (digits 0-9 and no digit) x 120 (10 x 12 pixels) target grayscale data of the digits
        # The array at i-th index corresponds to the grayscale values of digit i (eg: target_digits[3] are the grayscale values for 3)
        # except for 10th index where the grayscale value is for blank (no digit)
        self.target_digits = np.array([[25, 24, 51, 163, 217, 204, 140, 29, 23, 24, 24, 50, 212, 236, 192, 231, 238, 175, 23, 23, 25, 152, 238, 114, 0, 58, 235, 238, 75, 21, 35, 229, 238, 22, 13, 24, 184, 238, 165, 15, 68, 238, 230, 0, 22, 24, 134, 238, 201, 7, 93, 238, 220, 1, 25, 25, 115, 238, 228, 3, 104, 238, 233, 2, 22, 23, 101, 238, 218, 1, 80, 238, 238, 15, 23, 23, 111, 238, 192, 2, 51, 238, 238, 69, 22, 25, 137, 238, 147, 4, 24, 185, 238, 172, 18, 32, 206, 238, 51, 9, 25, 76, 229, 238, 200, 208, 238, 150, 0, 19, 25, 24, 65, 173, 222, 194, 119, 2, 9, 24], [21, 21, 21, 46, 213, 238, 81, 21, 21, 21, 21, 21, 39, 205, 238, 238, 66, 15, 21, 21, 22, 35, 198, 233, 238, 238, 66, 15, 21, 21, 22, 57, 222, 87, 238, 238, 66, 15, 21, 21, 22, 22, 35, 2, 238, 238, 66, 15, 21, 21, 22, 22, 22, 20, 238, 238, 66, 15, 21, 21, 22, 22, 22, 22, 238, 238, 66, 15, 21, 21, 22, 22, 22, 22, 238, 238, 66, 15, 21, 21, 22, 22, 22, 22, 238, 238, 66, 15, 21, 21, 22, 22, 22, 24, 238, 238, 69, 15, 21, 21, 22, 22, 22, 45, 238, 238, 92, 15, 21, 21, 22, 22, 22, 138, 238, 238, 188, 23, 21, 21], [22, 23, 106, 188, 222, 219, 170, 60, 21, 22, 22, 156, 238, 223, 172, 224, 238, 224, 48, 22, 63, 238, 221, 12, 2, 39, 230, 238, 126, 19, 96, 238, 218, 22, 21, 22, 192, 238, 157, 10, 45, 237, 238, 99, 20, 22, 214, 238, 114, 7, 24, 91, 118, 0, 13, 86, 238, 225, 19, 11, 23, 23, 15, 12, 34, 209, 238, 97, 1, 19, 23, 23, 23, 24, 167, 238, 155, 0, 13, 22, 23, 23, 24, 136, 238, 189, 8, 8, 23, 21, 25, 25, 111, 238, 210, 21, 6, 24, 55, 44, 25, 92, 235, 238, 211, 190, 194, 209, 238, 30, 74, 231, 238, 238, 238, 238, 238, 238, 215, 0], [20, 184, 238, 238, 238, 238, 238, 238, 148, 21, 21, 217, 209, 194, 193, 212, 238, 191, 7, 9, 27, 70, 2, 2, 9, 194, 224, 33, 4, 19, 21, 20, 16, 21, 140, 238, 79, 1, 17, 20, 22, 22, 21, 78, 237, 146, 0, 14, 20, 21, 22, 22, 38, 216, 238, 235, 181, 65, 20, 20, 21, 22, 45, 96, 134, 218, 238, 233, 57, 20, 21, 22, 21, 19, 14, 32, 217, 238, 149, 16, 21, 49, 78, 22, 22, 22, 167, 238, 168, 8, 84, 225, 213, 29, 22, 31, 222, 238, 119, 6, 74, 233, 238, 217, 172, 212, 238, 204, 13, 10, 22, 61, 163, 217, 229, 199, 131, 17, 3, 20], [22, 21, 21, 21, 160, 238, 238, 132, 21, 21, 22, 22, 21, 58, 236, 238, 238, 122, 10, 21, 23, 22, 21, 172, 233, 188, 238, 122, 10, 21, 23, 22, 69, 238, 139, 160, 238, 122, 10, 21, 23, 22, 183, 229, 22, 163, 238, 122, 10, 22, 23, 82, 238, 130, 1, 166, 238, 122, 10, 21, 22, 194, 226, 17, 10, 167, 238, 122, 10, 21, 93, 238, 213, 160, 166, 215, 238, 200, 163, 23, 188, 238, 238, 238, 238, 238, 238, 238, 238, 10, 23, 5, 0, 0, 0, 160, 238, 122, 0, 0, 23, 23, 23, 22, 22, 179, 238, 132, 10, 21, 22, 22, 22, 22, 38, 223, 238, 194, 16, 22], [22, 65, 238, 238, 238, 238, 238, 238, 69, 19, 21, 86, 238, 218, 189, 189, 189, 189, 17, 16, 23, 106, 238, 119, 2, 5, 4, 4, 4, 19, 22, 127, 238, 95, 10, 22, 22, 21, 21, 21, 23, 147, 238, 195, 154, 129, 51, 21, 21, 21, 23, 168, 238, 238, 238, 238, 235, 133, 21, 21, 22, 22, 8, 19, 60, 172, 238, 238, 83, 21, 22, 23, 22, 22, 20, 20, 202, 238, 147, 14, 22, 59, 79, 22, 22, 23, 170, 238, 159, 8, 93, 229, 202, 29, 22, 34, 226, 238, 109, 7, 78, 233, 238, 217, 172, 215, 238, 198, 9, 11, 22, 61, 163, 213, 229, 200, 126, 15, 4, 20], [22, 21, 21, 26, 143, 228, 208, 142, 37, 21, 21, 21, 29, 189, 238, 217, 74, 3, 10, 19, 23, 22, 155, 238, 203, 22, 2, 15, 21, 21, 22, 79, 238, 221, 27, 3, 19, 21, 21, 21, 23, 171, 238, 136, 176, 226, 195, 96, 21, 21, 32, 235, 238, 228, 188, 212, 238, 238, 88, 21, 62, 238, 238, 108, 1, 10, 166, 238, 194, 14, 85, 238, 237, 19, 12, 22, 67, 238, 234, 7, 64, 238, 238, 17, 21, 23, 59, 238, 220, 0, 30, 221, 238, 128, 21, 23, 134, 238, 156, 2, 22, 110, 238, 238, 189, 177, 237, 220, 31, 7, 22, 22, 85, 182, 224, 207, 155, 25, 2, 18], [56, 238, 238, 238, 238, 238, 238, 238, 238, 73, 83, 228, 184, 174, 174, 174, 210, 238, 189, 0, 81, 37, 1, 5, 6, 6, 197, 238, 82, 4, 22, 16, 19, 22, 22, 82, 238, 210, 4, 13, 23, 22, 21, 21, 21, 179, 238, 106, 2, 21, 23, 23, 22, 22, 58, 238, 230, 16, 11, 21, 22, 23, 22, 22, 150, 238, 152, 1, 19, 21, 22, 23, 22, 34, 228, 238, 60, 8, 21, 20, 22, 22, 22, 113, 238, 213, 1, 16, 21, 21, 23, 23, 22, 201, 238, 152, 2, 22, 21, 21, 23, 23, 67, 238, 238, 112, 8, 22, 21, 21, 22, 22, 147, 238, 238, 91, 12, 22, 21, 21], [21, 21, 81, 182, 224, 221, 173, 66, 20, 21, 21, 97, 237, 227, 158, 192, 238, 228, 53, 20, 23, 201, 238, 83, 1, 9, 208, 238, 119, 18, 22, 228, 238, 67, 14, 21, 162, 238, 117, 10, 23, 166, 238, 177, 37, 69, 220, 221, 27, 11, 23, 38, 178, 238, 238, 238, 220, 43, 2, 19, 22, 53, 172, 238, 215, 231, 238, 211, 54, 21, 36, 219, 238, 81, 0, 17, 178, 238, 191, 17, 103, 238, 220, 0, 15, 23, 86, 238, 237, 9, 89, 238, 237, 55, 23, 23, 137, 238, 199, 0, 33, 204, 238, 232, 177, 196, 238, 235, 74, 3, 22, 40, 135, 206, 230, 213, 164, 52, 0, 15], [21, 21, 88, 181, 223, 209, 161, 42, 20, 21, 21, 113, 238, 222, 172, 221, 238, 219, 37, 20, 38, 227, 238, 37, 2, 27, 209, 238, 135, 19, 86, 238, 194, 0, 19, 21, 122, 238, 191, 9, 103, 238, 199, 4, 21, 21, 119, 238, 218, 4, 66, 238, 238, 75, 22, 25, 192, 238, 193, 2, 22, 177, 238, 234, 180, 203, 232, 238, 158, 4, 22, 32, 142, 210, 216, 141, 191, 238, 77, 7, 22, 22, 21, 9, 2, 96, 238, 211, 4, 14, 23, 23, 22, 23, 89, 235, 236, 63, 2, 21, 23, 23, 29, 137, 235, 238, 108, 0, 16, 21, 22, 70, 179, 218, 219, 71, 0, 12, 21, 21], [23, 22, 23, 23, 22, 22, 22, 22, 22, 22, 23, 23, 22, 22, 22, 22, 22, 22, 21, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 22, 23, 23, 23, 22, 22, 22, 22, 22, 22, 23, 23, 23, 23, 23, 23, 23, 22, 22, 22, 23, 23, 24, 24, 24, 23, 23, 22, 22, 22, 23, 23, 24, 24, 24, 24, 24, 23, 22, 22, 24, 24, 24, 24, 24, 24, 24, 24, 23, 22, 24, 24, 24, 24, 24, 24, 24, 24, 24, 23, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24, 24]], dtype=np.float32)
        self.counter = 0
        self.prev = 0

    def get_cs(self, debug=False) -> int:
        digits = []
        bounds = (1920 - 138, 5, 1920 - 108, 25)
        with mss(with_cursor=False) as sct: # is better to just keep a self.mss instance but I don't want to 
            ss = sct.grab(bounds)
            ss = Image.frombytes("RGB", ss.size, ss.bgra, "raw", "BGRX").convert("L")
            # img_arr = np.array(ss)
            # if np.max(img_arr) == 0: # try again ?? if you try to screenshot too frequently theres a higher and higher chance of getting a blank image
            #     ss = sct.grab(bounds)
            #     ss = Image.frombytes("RGB", ss.size, ss.bgra, "raw", "BGRX").convert("L")

        # first 1 is shorter by 1
        # rest is not ?
        currimg = ss.crop((0, 3, 10, 15))
        currdigit = self.most_similar_digit(currimg)
        x = 0
        while currdigit != "":
            digits.append(currdigit)
            if len(digits) == 1 and currdigit == "1":
                x += 9
            else:
                x += 10
            currimg = ss.crop((x, 3, x + 10, 15))
            currdigit = self.most_similar_digit(currimg)
        

        string = "".join(digits)
        if string == "":
            number = 0
        else:
            number = int("".join(digits))
        if debug:
            if number < self.prev or number > self.prev + 1:
                print(f"prev: {self.prev}, curr: {number}")
                print(list(ss.getdata()))
        self.prev = number
        return number

    def most_similar_digit(self, digit: Image) -> str:
        """ Returns the most similar digit by finding a target digit with smallest MSE with the digit given """
        digit_data: np.ndarray = np.array(digit).ravel()

        computed_mse: float = np.mean((self.target_digits - digit_data) ** 2, axis=1)
        most_similar_digit: str = str(np.argmin(computed_mse))

        return most_similar_digit if most_similar_digit != '10' else ''

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
def gettime():
    """ Returns the time in seconds since the start of the game """
    try:
        mins = requests.get(
            "https://127.0.0.1:2999/liveclientdata/gamestats", verify=False
        ).json()["gameTime"] / 60
        return mins
    except Exception:
        return 1