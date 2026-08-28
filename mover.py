import json
import random
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import keyboard
import numpy as np
import pyautogui
import pytesseract
from PIL import Image


BASE_DIR = Path(__file__).resolve().parent
COORDINATES_PATH = BASE_DIR / "coordinates.json"
SETTINGS_PATH = BASE_DIR / "settings.json"
GOLD_HISTORY_PATH = BASE_DIR / "gold_history.json"

CALIBRATION_COST = 20_000
DEFAULT_GOLD_LIMIT = 700_000
DECREASE_EVERY_GOLD = 250_000
DECREASE_AMOUNT = 10
DEFAULT_MAX_DECREASE = 30

VALUABLE_PARTIAL_TOTAL = 270
PROMISING_PRECEDING_TOTAL = 250
VALUABLE_EXTRA_SCANS = 4
RESCAN_CROP_OFFSETS = [(-4, 0), (4, 0), (0, -3), (0, 3)]

pause_event = threading.Event()
exit_event = threading.Event()


def is_valid_stat_value(value):
    return type(value) is int and 10 <= value <= 200 and value % 10 == 0


def is_suspicious_low_value(value):
    return value in {10, 20}


def on_pause():
    if pause_event.is_set():
        pause_event.clear()
        print("Resumed.")
    else:
        pause_event.set()
        print("Paused. Press F9 to resume.")


def on_exit():
    exit_event.set()
    print("Exit requested, stopping after the current action...")


def check_pause_exit():
    if exit_event.is_set():
        print("Exiting.")
        sys.exit(0)
    while pause_event.is_set():
        time.sleep(0.2)
        if exit_event.is_set():
            print("Exiting.")
            sys.exit(0)


def load_coordinates():
    try:
        with COORDINATES_PATH.open("r", encoding="utf-8") as f:
            coords = json.load(f)
    except FileNotFoundError:
        print("Error: coordinates.json was not found. Run get_coordinates.py first.")
        sys.exit(1)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: could not read coordinates.json: {exc}")
        sys.exit(1)

    required = [
        "quick_selection",
        "calibrate",
        "confirm",
        "restore",
        "stat_1",
        "stat_2",
        "stat_3",
    ]
    missing = [key for key in required if key not in coords]
    if missing:
        print(f"Error: coordinates.json is missing keys: {', '.join(missing)}")
        sys.exit(1)
    return coords


def read_stat_percent(
    img,
    cx,
    cy,
    label="stat",
    fallback_top_half=False,
    top_half_first=False,
    crop_offset=(0, 0),
):
    offset_x, offset_y = crop_offset
    box = (
        cx - 112 + offset_x,
        cy + 20 + offset_y,
        cx - 4 + offset_x,
        cy + 70 + offset_y,
    )
    region = img.crop(box)
    arr = np.array(region)

    red = arr[:, :, 0].astype(int)
    green = arr[:, :, 1].astype(int)
    blue = arr[:, :, 2].astype(int)

    red_mask = (red > 160) & (green < 80) & (blue < 80)
    green_mask = (green > 130) & (red < 130) & (blue < 130)
    white_mask = (red > 180) & (green > 180) & (blue > 180)
    combined_mask = red_mask | green_mask | white_mask

    result = np.zeros_like(arr)
    result[combined_mask] = [255, 255, 255]

    clean = Image.fromarray(result.astype(np.uint8)).convert("L")
    width, height = clean.size
    clean = clean.crop((int(width * 0.20), 0, int(width * 0.90), height))
    clean = clean.resize((clean.width * 5, clean.height * 5), Image.LANCZOS)
    clean.save(BASE_DIR / f"debug_{label}_masked.png")

    def ocr_value(image):
        text = pytesseract.image_to_string(
            image,
            config="--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789",
        ).strip()
        match = re.search(r"\d+", text)
        return match.group(0) if match else None

    def normalize(value):
        if value is None:
            return None
        if len(value) == 5:
            value = value[:3]
        if len(value) == 4:
            value = value[:3]
        elif len(value) == 3 and value[-1] != "0":
            value = value[:2]
        if len(value) == 1:
            value += "0"
        return value

    def fixup(value):
        if value is None:
            return None
        known = {
            "710": "70",
            "00": None,
        }
        return known.get(value, value)

    def looks_bad(value):
        if value is None:
            return True
        try:
            return not is_valid_stat_value(int(value))
        except ValueError:
            return True

    top_half = clean.crop((0, 0, clean.width, int(clean.height * 0.55)))
    top_half.save(BASE_DIR / f"debug_{label}_tophalf.png")

    if top_half_first:
        value = fixup(normalize(ocr_value(top_half)))
        if looks_bad(value):
            value = fixup(normalize(ocr_value(clean)))
    else:
        value = fixup(normalize(ocr_value(clean)))
        if fallback_top_half and looks_bad(value):
            value = fixup(normalize(ocr_value(top_half)))

    if not value or looks_bad(value):
        return None
    return int(value)


def capture_and_read_values(
    stat_positions,
    indexes=None,
    crop_offset=(0, 0),
    announce=True,
):
    selected_indexes = set(range(len(stat_positions))) if indexes is None else set(indexes)
    screenshot = pyautogui.screenshot()
    values = [None] * len(stat_positions)
    four_stats = len(stat_positions) == 4

    try:
        for index, (cx, cy) in enumerate(stat_positions):
            if index not in selected_indexes:
                continue
            values[index] = read_stat_percent(
                screenshot,
                cx,
                cy,
                f"stat_{index + 1}",
                fallback_top_half=True,
                top_half_first=four_stats and index >= 2,
                crop_offset=crop_offset,
            )
    finally:
        screenshot.close()

    if announce:
        for index in sorted(selected_indexes):
            value = values[index]
            print(f"Stat {index + 1}: {f'{value}%' if value is not None else None}")
    return values


def should_rescan_valuable_partial(values):
    valid_values = [value for value in values if value is not None]
    return (
        len(valid_values) >= 2
        and len(valid_values) < len(values)
        and sum(valid_values) >= VALUABLE_PARTIAL_TOTAL
    )


def should_verify_final_stat(values, target_total):
    return (
        all(value is not None for value in values)
        and sum(values[:-1]) >= PROMISING_PRECEDING_TOTAL
        and (sum(values) < target_total or values[-1] < 100)
    )


def select_best_case_stat_value(samples, fallback):
    valid_samples = [value for value in samples if is_valid_stat_value(value)]
    if not valid_samples:
        return fallback
    return max(valid_samples)


def capture_with_valuable_rescans(stat_positions, target_total):
    values = capture_and_read_values(stat_positions)
    final_index = len(values) - 1
    samples = [([value] if value is not None else []) for value in values]
    fully_rescanned_indexes = set()

    def perform_rescans(indexes_to_scan, reason, crop_offsets, announce=True):
        indexes_to_scan = list(indexes_to_scan)
        for scan_number, crop_offset in enumerate(crop_offsets, start=1):
            if announce:
                print(
                    f"{reason} ({scan_number}/{len(crop_offsets)}; "
                    f"crop offset x={crop_offset[0]:+d}, y={crop_offset[1]:+d})..."
                )
            check_pause_exit()
            time.sleep(0.35)
            capture_kwargs = {
                "indexes": indexes_to_scan,
                "crop_offset": crop_offset,
            }
            if not announce:
                capture_kwargs["announce"] = False
            rescanned = capture_and_read_values(stat_positions, **capture_kwargs)
            for index in indexes_to_scan:
                if rescanned[index] is not None:
                    samples[index].append(rescanned[index])

        for index in indexes_to_scan:
            original_value = values[index]
            values[index] = select_best_case_stat_value(samples[index], original_value)
            if announce and samples[index]:
                readings = ", ".join(f"{value}%" for value in samples[index])
                print(
                    f"Stat {index + 1} verification readings: [{readings}] "
                    f"-> using best-case {values[index]}%."
                )
        if len(crop_offsets) >= VALUABLE_EXTRA_SCANS:
            fully_rescanned_indexes.update(indexes_to_scan)

    if should_rescan_valuable_partial(values):
        missing_indexes = [index for index, value in enumerate(values) if value is None]
        partial_total = sum(value for value in values if value is not None)
        perform_rescans(
            missing_indexes,
            (
                f"Valuable partial read ({partial_total}% across "
                f"{len(values) - len(missing_indexes)} stats). "
                "Rescanning missing stats"
            ),
            RESCAN_CROP_OFFSETS,
        )

    suspicious_low_indexes = [
        index
        for index, value in enumerate(values)
        if is_suspicious_low_value(value) and index not in fully_rescanned_indexes
    ]
    if suspicious_low_indexes:
        stat_labels = ", ".join(str(index + 1) for index in suspicious_low_indexes)
        perform_rescans(
            suspicious_low_indexes,
            f"10%/20% reading in stat(s) {stat_labels}. Verifying that it's not a +100% or 200% misread...",
            RESCAN_CROP_OFFSETS,
        )

    silent_120_indexes = [
        index
        for index, value in enumerate(values)
        if value == 120 and index not in fully_rescanned_indexes
    ]
    if silent_120_indexes:
        perform_rescans(
            silent_120_indexes,
            reason="",
            crop_offsets=RESCAN_CROP_OFFSETS[:2],
            announce=False,
        )

    if (
        should_verify_final_stat(values, target_total)
        and final_index not in fully_rescanned_indexes
    ):
        perform_rescans(
            [final_index],
            (
                f"Promising attachment ({sum(values[:-1])}% before the final stat; "
                f"current total {sum(values)}%; goal {target_total}%). "
                f"Verifying stat {final_index + 1}"
            ),
            RESCAN_CROP_OFFSETS,
        )

    return values


def ask_yes_no(prompt, default=True):
    suffix = "Y/n" if default else "y/N"
    while True:
        choice = input(f"{prompt} ({suffix}): ").strip().lower()
        if not choice:
            return default
        if choice in {"y", "yes"}:
            return True
        if choice in {"n", "no"}:
            return False
        print("Invalid input. Type y or n.")


def ask_mode(coords):
    while True:
        choice = input("Choose mode: (1) regular attachment, (2) muzzle: ").strip()
        if choice not in {"1", "2"}:
            print("Invalid input. Type 1 or 2.")
            continue
        mode = int(choice)
        if mode == 2 and "stat_4" not in coords:
            print("Mode 2 requires stat_4 in coordinates.json. Re-run get_coordinates.py with 4 stats.")
            continue
        return mode


def ask_stat_requirement(mode):
    maximum = 600 if mode == 1 else 800
    recommended = 450 if mode == 1 else 600
    while True:
        raw = input(
            f"Desired starting stat total (100-{maximum}, recommended {recommended}): "
        ).strip()
        try:
            desired = int(raw) if raw else recommended
        except ValueError:
            print("Invalid input, enter a number.")
            continue
        if 100 <= desired <= maximum:
            return desired
        print(f"Must be between 100 and {maximum}.")


def ask_gold_limit():
    while True:
        raw = input(
            "Gold limit (600,000-800,000 suggested, default 700,000): "
        ).strip()
        try:
            gold_limit = int(raw.replace(",", "").replace("_", "")) if raw else DEFAULT_GOLD_LIMIT
        except ValueError:
            print("Invalid input, enter a number.")
            continue
        if gold_limit >= CALIBRATION_COST:
            return gold_limit
        print(f"Gold limit must be at least {CALIBRATION_COST:,}.")


def ask_minimum_stat_total(starting_total):
    recommended = max(100, starting_total - DEFAULT_MAX_DECREASE)
    while True:
        raw = input(
            f"Lowest acceptable total after gradual decreases "
            f"(100-{starting_total}, default {recommended}): "
        ).strip()
        try:
            minimum = int(raw) if raw else recommended
        except ValueError:
            print("Invalid input, enter a number.")
            continue
        if 100 <= minimum <= starting_total:
            return minimum
        print(f"Must be between 100 and {starting_total}.")


def settings_are_valid(settings, coords):
    required = {
        "mode",
        "desired_stat_total",
        "gold_limit",
        "gradual_decrease",
        "minimum_stat_total",
        "decrease_every_gold",
        "decrease_amount",
    }
    if not isinstance(settings, dict) or not required.issubset(settings):
        return False

    integer_keys = required - {"gradual_decrease"}
    if any(type(settings[key]) is not int for key in integer_keys):
        return False
    if type(settings["gradual_decrease"]) is not bool:
        return False

    mode = settings["mode"]
    maximum = 600 if mode == 1 else 800
    return (
        mode in {1, 2}
        and (mode != 2 or "stat_4" in coords)
        and 100 <= settings["desired_stat_total"] <= maximum
        and CALIBRATION_COST <= settings["gold_limit"]
        and 100 <= settings["minimum_stat_total"] <= settings["desired_stat_total"]
        and settings["decrease_every_gold"] > 0
        and settings["decrease_amount"] > 0
    )


def load_saved_settings(coords):
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as f:
            settings = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Could not load settings.json ({exc}). New settings will be collected.")
        return None

    if not settings_are_valid(settings, coords):
        print("Saved settings are incomplete or incompatible. New settings will be collected.")
        return None
    return settings


def save_settings(settings):
    temporary_path = SETTINGS_PATH.with_suffix(".json.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        temporary_path.replace(SETTINGS_PATH)
        print("Settings saved to settings.json.")
    except OSError as exc:
        print(f"Warning: settings could not be saved: {exc}")


def goal_band_for(target_total):
    upper_bound = ((target_total + 9) // 10) * 10
    lower_bound = max(10, upper_bound - 20)
    return f"{lower_bound}-{upper_bound}%"


def build_gold_averages(runs):
    averages = {}
    for run in runs:
        try:
            mode = int(run["mode"])
            goal_band = str(run["goal_band"])
            gold_used = int(run["gold_used"])
        except (KeyError, TypeError, ValueError):
            continue
        if mode not in {1, 2} or gold_used < 0:
            continue

        mode_key = f"mode_{mode}"
        bucket = averages.setdefault(mode_key, {}).setdefault(
            goal_band,
            {
                "completed_runs": 0,
                "total_gold": 0,
                "average_gold": 0,
            },
        )
        bucket["completed_runs"] += 1
        bucket["total_gold"] += gold_used

    for mode_bands in averages.values():
        for bucket in mode_bands.values():
            bucket["average_gold"] = round(
                bucket["total_gold"] / bucket["completed_runs"]
            )
    return averages


def load_gold_history():
    try:
        with GOLD_HISTORY_PATH.open("r", encoding="utf-8") as f:
            history = json.load(f)
    except FileNotFoundError:
        return {"version": 1, "runs": []}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: could not read gold_history.json: {exc}")
        return {"version": 1, "runs": []}

    if not isinstance(history, dict) or not isinstance(history.get("runs"), list):
        print("Warning: gold_history.json has an invalid format; starting a new history.")
        return {"version": 1, "runs": []}
    return history


def save_gold_history(history):
    temporary_path = GOLD_HISTORY_PATH.with_suffix(".json.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
            f.write("\n")
        temporary_path.replace(GOLD_HISTORY_PATH)
        return True
    except OSError as exc:
        print(f"Warning: gold history could not be saved: {exc}")
        return False


def record_completed_run(settings, completed_goal, achieved_total, gold_used, attempts):
    history = load_gold_history()
    goal_band = goal_band_for(completed_goal)
    history["version"] = 1
    history["runs"].append(
        {
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "mode": settings["mode"],
            "starting_goal": settings["desired_stat_total"],
            "completed_goal": completed_goal,
            "achieved_total": achieved_total,
            "goal_band": goal_band,
            "gold_used": gold_used,
            "attempts": attempts,
        }
    )
    history["averages_by_mode_and_goal_band"] = build_gold_averages(history["runs"])

    if save_gold_history(history):
        bucket = history["averages_by_mode_and_goal_band"][f"mode_{settings['mode']}"][goal_band]
        print(
            f"Gold history saved. Mode {settings['mode']} {goal_band} average: "
            f"{bucket['average_gold']:,} gold across "
            f"{bucket['completed_runs']} completed run(s)."
        )


def format_settings(settings):
    mode_name = "regular attachment" if settings["mode"] == 1 else "muzzle"
    if settings["gradual_decrease"]:
        gradual = (
            f"goal -{settings['decrease_amount']} every "
            f"{settings['decrease_every_gold']:,} gold to a minimum of "
            f"{settings['minimum_stat_total']}%"
        )
    else:
        gradual = "fixed goal"
    return (
        f"Mode {settings['mode']} {mode_name}; starting goal "
        f"{settings['desired_stat_total']}%; gold limit {settings['gold_limit']:,}; {gradual}"
    )


def collect_or_reload_settings(coords):
    saved = load_saved_settings(coords)
    if saved is not None:
        details = format_settings(saved)
        if ask_yes_no(f"Reload last settings? [{details}]", default=True):
            print(f"Loaded settings: [{details}]")
            return saved

    mode = ask_mode(coords)
    desired_total = ask_stat_requirement(mode)
    gold_limit = ask_gold_limit()
    gradual = ask_yes_no(
        f"Gradually lower the goal by {DECREASE_AMOUNT} every "
        f"{DECREASE_EVERY_GOLD:,} gold spent?",
        default=True,
    )
    minimum_total = ask_minimum_stat_total(desired_total) if gradual else desired_total

    settings = {
        "version": 1,
        "mode": mode,
        "desired_stat_total": desired_total,
        "gold_limit": gold_limit,
        "gradual_decrease": gradual,
        "minimum_stat_total": minimum_total,
        "decrease_every_gold": DECREASE_EVERY_GOLD,
        "decrease_amount": DECREASE_AMOUNT,
    }
    save_settings(settings)
    print(f"Using settings: [{format_settings(settings)}]")
    return settings


def target_for_gold(settings, gold_spent):
    if not settings["gradual_decrease"]:
        return settings["desired_stat_total"]
    decrease_steps = gold_spent // settings["decrease_every_gold"]
    reduced_target = settings["desired_stat_total"] - (
        decrease_steps * settings["decrease_amount"]
    )
    return max(settings["minimum_stat_total"], reduced_target)


def can_start_attempt(gold_spent, gold_limit):
    return gold_spent + CALIBRATION_COST <= gold_limit


def jittered(x, y):
    return x + random.randint(-15, 15), y + random.randint(-5, 5)


def jittered_small(x, y):
    return x + random.randint(-10, 10), y + random.randint(-3, 3)


def click_at(position, small_jitter=False):
    jitter_function = jittered_small if small_jitter else jittered
    x, y = jitter_function(position["x"], position["y"])
    pyautogui.moveTo(x, y)
    pyautogui.click()


def restore_calibration(coords, mode):
    click_at(coords["restore"], small_jitter=True)
    extra_wait = random.uniform(-0.3, 0.5) if mode == 2 else 0
    time.sleep(2.0 + extra_wait)


def run_calibration(coords, settings):
    mode = settings["mode"]
    stat_count = 3 if mode == 1 else 4
    stat_positions = [
        (coords[f"stat_{index}"]["x"], coords[f"stat_{index}"]["y"])
        for index in range(1, stat_count + 1)
    ]

    attempts = 0
    current_target = target_for_gold(settings, 0)
    mode_name = "regular attachment" if mode == 1 else "muzzle"
    print(f"Calibrating {mode_name} with a current goal of {current_target}%...")

    while True:
        check_pause_exit()
        gold_spent = attempts * CALIBRATION_COST
        if not can_start_attempt(gold_spent, settings["gold_limit"]):
            print(
                f"Gold limit reached. Spent {gold_spent:,} of "
                f"{settings['gold_limit']:,} gold across {attempts} attempts. "
                f"No further {CALIBRATION_COST:,}-gold attempt will be started."
            )
            return False

        click_at(coords["quick_selection"])
        quick_wait = 1.0 if mode == 1 else 0.6
        time.sleep(quick_wait + random.uniform(-0.2, 0.4))
        check_pause_exit()

        click_at(coords["calibrate"])
        attempts += 1
        gold_spent = attempts * CALIBRATION_COST
        calibration_wait = 6.0 if mode == 1 else 2.0
        time.sleep(calibration_wait + random.uniform(-0.5, 0.8))
        check_pause_exit()

        updated_target = target_for_gold(settings, gold_spent)
        if updated_target < current_target:
            print(
                f"Gradual goal decrease: {current_target}% -> {updated_target}% "
                f"after spending {gold_spent:,} gold."
            )
            current_target = updated_target

        values = capture_with_valuable_rescans(stat_positions, current_target)
        if any(value is None for value in values):
            print("OCR failed to read one or more stats after available scans, retrying...")
            restore_calibration(coords, mode)
            continue

        if any(not is_valid_stat_value(value) for value in values):
            print("OCR read an invalid stat (must be 10-200 in steps of 10), retrying...")
            restore_calibration(coords, mode)
            continue

        stat_total = sum(values)
        maximum_total = 600 if mode == 1 else 800
        if not 100 <= stat_total <= maximum_total:
            print(f"Hard error: invalid stat total ({stat_total}), retrying...")
            restore_calibration(coords, mode)
            continue

        if stat_total >= current_target and all(value >= 100 for value in values):
            print(f"Success! Total: {stat_total}% (goal: {current_target}%)")
            print(f"Gold used: {gold_spent:,} across {attempts} attempts")
            pyautogui.moveTo(coords["confirm"]["x"], coords["confirm"]["y"])
            pyautogui.click()
            record_completed_run(
                settings,
                completed_goal=current_target,
                achieved_total=stat_total,
                gold_used=gold_spent,
                attempts=attempts,
            )
            return True

        if stat_total >= current_target:
            print(
                f"Total meets the goal ({stat_total}% >= {current_target}%) "
                "but a stat was below 100%, retrying..."
            )
        else:
            print(f"Stat total too low ({stat_total}% < {current_target}%), retrying...")
        restore_calibration(coords, mode)


def main():
    coords = load_coordinates()
    print("While calibration is running, press F9 to pause/resume or F10 to stop.")
    settings = collect_or_reload_settings(coords)

    keyboard.add_hotkey("F9", on_pause)
    keyboard.add_hotkey("F10", on_exit)

    for seconds in range(3, -1, -1):
        print(f"Starting in {seconds} seconds...")
        time.sleep(1)

    run_calibration(coords, settings)


if __name__ == "__main__":
    main()
