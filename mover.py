import sys
import pyautogui
import time
import json
import os
import re
import numpy as np
from PIL import Image
import pytesseract
import keyboard
import threading
import random

# READ THIS DISCLAIMER:
# WARNING VIBE CODED SLOP AHEAD!
# THERE ARE LITTLE TO NO COMMENTS AND NO STRUCTURE WHATSOEVER LOL
# DON'T ASK ME WHAT HALF OF THIS SHIT DOES BECAUSE FRANKLY I FORGOT 5MINS AFTER INCLUDING IT
# AND I ALSO DON'T CARE XD
# YOU'VE BEEN WARNED

with open("coordinates.json", "r") as f:
    coords = json.load(f)

required_keys_mode1 = [
    "quick_selection", "calibrate", "confirm", "restore",
    "stat_1", "stat_2", "stat_3"
]

required_keys_mode2 = required_keys_mode1 + ["stat_4"]

missing_mode1 = [k for k in required_keys_mode1 if k not in coords]
if missing_mode1:
    print(f"Error: coordinates.json is missing keys: {', '.join(missing_mode1)}")
    sys.exit(1)

x1 = coords["quick_selection"]["x"]
y1 = coords["quick_selection"]["y"]
x2 = coords["calibrate"]["x"]
y2 = coords["calibrate"]["y"]
x3 = coords["confirm"]["x"]
y3 = coords["confirm"]["y"]
x4 = coords["restore"]["x"]
y4 = coords["restore"]["y"]
x5 = coords["stat_1"]["x"]
y5 = coords["stat_1"]["y"]
x6 = coords["stat_2"]["x"]
y6 = coords["stat_2"]["y"]
x7 = coords["stat_3"]["x"]
y7 = coords["stat_3"]["y"]

pause_event = threading.Event()
exit_event = threading.Event()

def on_pause():
    if pause_event.is_set():
        pause_event.clear()
        print("Resumed.")
    else:
        pause_event.set()
        print("Paused. Press F9 to resume.")

def on_exit():
    exit_event.set()
    print("Exit requested, stopping after current action...")

keyboard.add_hotkey("F9", on_pause)
keyboard.add_hotkey("F10", on_exit)

def check_pause_exit():
    if exit_event.is_set():
        print("Exiting.")
        sys.exit(0)
    while pause_event.is_set():
        time.sleep(0.2)
        if exit_event.is_set():
            print("Exiting.")
            sys.exit(0)


BOX_HALF_W = 60
BOX_HALF_H = 17

def read_stat_percent(img, cx, cy, label="stat", fallback_top_half=False, top_half_first=False):
    box = (cx - 112, cy + 20, cx - 4, cy + 70)
    region = img.crop(box)
    arr = np.array(region)

    R = arr[:, :, 0].astype(int)
    G = arr[:, :, 1].astype(int)
    B = arr[:, :, 2].astype(int)

    red_mask   = (R > 160) & (G < 80)  & (B < 80)
    green_mask = (G > 130) & (R < 130) & (B < 130)
    white_mask = (R > 180) & (G > 180) & (B > 180)

    combined_mask = red_mask | green_mask | white_mask

    result = np.zeros_like(arr)
    result[combined_mask] = [255, 255, 255]

    clean = Image.fromarray(result.astype(np.uint8)).convert("L")

    w, h = clean.size
    clean = clean.crop((int(w * 0.20), 0, int(w * 0.90), h))
    clean = clean.resize((clean.width * 5, clean.height * 5), Image.LANCZOS)

    clean.save(f"debug_{label}_masked.png")

    if top_half_first:
        top_half = clean.crop((0, 0, clean.width, int(clean.height * 0.55)))
        top_half.save(f"debug_{label}_tophalf.png")
        text = pytesseract.image_to_string(top_half, config="--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789").strip()
        match = re.search(r"\d+", text)
        if not match:
            # fall back to full box
            text = pytesseract.image_to_string(clean, config="--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789").strip()
            match = re.search(r"\d+", text)
    else:
        text = pytesseract.image_to_string(clean, config="--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789").strip()
        match = re.search(r"\d+", text)

        if not match and fallback_top_half:
            top_half = clean.crop((0, 0, clean.width, int(clean.height * 0.55)))
            top_half.save(f"debug_{label}_tophalf.png")
            text = pytesseract.image_to_string(top_half, config="--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789").strip()
            match = re.search(r"\d+", text)

    if not match:
        return None

    value = match.group(0)

    # common ocr artifact cleanup
    if len(value) == 5:
        value = value[:3]
    if len(value) == 4:
        value = value[:3]
    elif len(value) == 3 and value[-1] != "0":
        value = value[:2]

    if len(value) == 1:
        value = value + "0"

    if value == "710":
        value = "70"

    if fallback_top_half and int(value) > 200:
        top_half = clean.crop((0, 0, clean.width, int(clean.height * 0.55)))
        top_half.save(f"debug_{label}_tophalf.png")
        text = pytesseract.image_to_string(top_half, config="--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789").strip()
        match = re.search(r"\d+", text)
        if match:
            value = match.group(0)
            if len(value) == 4:
                value = value[:3]
            elif len(value) == 3 and value[-1] != "0":
                value = value[:2]

    return value + "%"

def capture_and_read_values(four_stats=False):
    screenshot_path = "temp_calibration.png"
    pyautogui.screenshot(screenshot_path)
    img = Image.open(screenshot_path)

    stat_1 = read_stat_percent(img, x5, y5, "stat_1", fallback_top_half=four_stats)
    stat_2 = read_stat_percent(img, x6, y6, "stat_2", fallback_top_half=four_stats)
    stat_3 = read_stat_percent(img, x7, y7, "stat_3", fallback_top_half=four_stats, top_half_first=four_stats)
    stat_4 = read_stat_percent(img, x8, y8, "stat_4", fallback_top_half=True,  top_half_first=four_stats) if four_stats else None

    img.close()
    os.remove(screenshot_path)

    print(f"Stat 1: {stat_1}")
    print(f"Stat 2: {stat_2}")
    print(f"Stat 3: {stat_3}")
    if four_stats:
        print(f"Stat 4: {stat_4}")

    return stat_1, stat_2, stat_3, stat_4


def clean_percent(s):
    return int(s.replace("%", "")) if s else None


def ask_mode():
    while True:
        print("While the calibration is running you can pause by pressing F9 and exit by pressing F10.")
        choice = input("Choose mode: (1) regular attachment, (2) muzzle: ").strip()
        if choice in {"1", "2"}:
            return int(choice)
        print("Invalid input. Type 1 or 2.")

def ask_stat_requirement():
    while True:
        if mode == 1:
            try:
                raw = input("Desired stat total (100-600, recommended 450): ").strip()
                desired = int(raw) if raw else 450
                if 100 <= desired <= 600:
                    return desired
                print("Must be between 100 and 600.")
            except ValueError:
                print("Invalid input, enter a number.")
        elif mode == 2:
            try:
                raw = input("Desired stat total (100-800, recommended 600): ").strip()
                desired = int(raw) if raw else 600
                if 100 <= desired <= 800:
                    return desired
                print("Must be between 100 and 800.")
            except ValueError:
                print("Invalid input, enter a number.")


mode = ask_mode()

if mode == 2:
    missing_mode2 = [k for k in required_keys_mode2 if k not in coords]
    if missing_mode2:
        print(f"Error: mode 2 requires missing keys: {', '.join(missing_mode2)}")
        sys.exit(1)
    x8 = coords["stat_4"]["x"]
    y8 = coords["stat_4"]["y"]

desired_stat_total = ask_stat_requirement()

for i in range(3, -1, -1):
    print(f"Starting in {i} seconds...")
    time.sleep(1)

def jittered(x, y):
    return (
        x + random.randint(-15, 15),
        y + random.randint(-5, 5)
    )

def jittered_small(x, y):
    return (
        x + random.randint(-10, 10),
        y + random.randint(-3, 3)
    )

if mode == 1:
    print("Calibrating regular attachment...")
    success = False

    while not success:
        jx1, jy1 = jittered(x1, y1)
        pyautogui.moveTo(jx1, jy1)
        pyautogui.click()
        time.sleep(1)

        check_pause_exit()

        jx2, jy2 = jittered(x2, y2)
        pyautogui.moveTo(jx2, jy2)
        pyautogui.click()
        time.sleep(6)

        check_pause_exit()

        stat_1, stat_2, stat_3, _ = capture_and_read_values(four_stats=False)

        stat_1_val = clean_percent(stat_1)
        stat_2_val = clean_percent(stat_2)
        stat_3_val = clean_percent(stat_3)

        jx4, jy4 = jittered_small(x4, y4)

        if None in (stat_1_val, stat_2_val, stat_3_val):
            print("OCR failed to read one or more stats, retrying...")
            pyautogui.moveTo(jx4, jy4)
            pyautogui.click()
            time.sleep(2)
            continue

        if any(v > 200 for v in (stat_1_val, stat_2_val, stat_3_val)):
            print("OCR read an impossible value (>200%), retrying...")
            pyautogui.moveTo(jx4, jy4)
            pyautogui.click()
            time.sleep(3)
            continue

        stat_total = stat_1_val + stat_2_val + stat_3_val

        if not 100 <= stat_total <= 600:
            print(f"Hard error: invalid stat total ({stat_total}), retrying...")
            pyautogui.moveTo(jx4, jy4)
            pyautogui.click()
            time.sleep(3)
            continue

        if stat_total >= desired_stat_total:
            print(f"Success! Total: {stat_total}")
            success = True
        else:
            print(f"Stat total too low ({stat_total}), retrying...")
            pyautogui.moveTo(jx4, jy4)
            pyautogui.click()
            time.sleep(3)

    pyautogui.moveTo(x3, y3)
    pyautogui.click()

elif mode == 2:
    print("Calibrating muzzle...")
    success = False

    while not success:
        jx1, jy1 = jittered(x1, y1)
        pyautogui.moveTo(jx1, jy1)
        pyautogui.click()
        time.sleep(1)

        check_pause_exit()

        jx2, jy2 = jittered(x2, y2)
        pyautogui.moveTo(jx2, jy2)
        pyautogui.click()
        time.sleep(6)

        check_pause_exit()

        stat_1, stat_2, stat_3, stat_4 = capture_and_read_values(four_stats=True)

        stat_1_val = clean_percent(stat_1)
        stat_2_val = clean_percent(stat_2)
        stat_3_val = clean_percent(stat_3)
        stat_4_val = clean_percent(stat_4)

        jx4, jy4 = jittered_small(x4, y4)

        if None in (stat_1_val, stat_2_val, stat_3_val, stat_4_val):
            print("OCR failed to read one or more stats, retrying...")
            pyautogui.moveTo(jx4, jy4)
            pyautogui.click()
            time.sleep(2)
            continue

        if any(v > 200 for v in (stat_1_val, stat_2_val, stat_3_val, stat_4_val)):
            print("OCR read an impossible value (>200%), retrying...")
            pyautogui.moveTo(jx4, jy4)
            pyautogui.click()
            time.sleep(3)
            continue

        stat_total = stat_1_val + stat_2_val + stat_3_val + stat_4_val

        if not 100 <= stat_total <= 800:
            print(f"Hard error: invalid stat total ({stat_total}), retrying...")
            pyautogui.moveTo(jx4, jy4)
            pyautogui.click()
            time.sleep(3)
            continue

        if stat_total >= desired_stat_total:
            print(f"Success! Total: {stat_total}")
            success = True
        else:
            print(f"Stat total too low ({stat_total}), retrying...")
            pyautogui.moveTo(jx4, jy4)
            pyautogui.click()
            time.sleep(3)

    pyautogui.moveTo(x3, y3)
    pyautogui.click()