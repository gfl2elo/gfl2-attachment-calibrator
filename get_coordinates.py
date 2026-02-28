import pyautogui
import time
import json

# WARNING VIBE CODED SLOP AHEAD!

while True:
    choice = input("Save coordinates for 3 stats or 4 stats? (input 3 or 4) [4 recommended]: ").strip()
    if choice in {"3", "4"}:
        four_stats = choice == "4"
        break
    print("Invalid input. Type 3 or 4.")

print("Get ready to hover the Quick Selection button...")
for i in range(7):
    print(i)
    time.sleep(1)

print("Now hover Quick Selection please!")
for i in range(5):
    print(i)
    time.sleep(1)
x1, y1 = pyautogui.position()
print("Quick Selection button at:", x1, y1)

print("Please click Quick Selection and get ready to hover the Calibrate button")
for i in range(7):
    print(i)
    time.sleep(1)

print("Now hover Calibrate please!")
for i in range(5):
    print(i)
    time.sleep(1)
x2, y2 = pyautogui.position()
print("Calibrate:", x2, y2)

print("Please click Calibrate and get ready to hover the Confirm button")
for i in range(10):
    print(i)
    time.sleep(1)

print("Now hover Confirm please!")
for i in range(5):
    print(i)
    time.sleep(1)
x3, y3 = pyautogui.position()
print("Confirm:", x3, y3)

print("Get ready to hover the Restore button")
for i in range(5):
    print(i)
    time.sleep(1)

print("Now hover Restore please!")
for i in range(5):
    print(i)
    time.sleep(1)
x4, y4 = pyautogui.position()
print("Restore:", x4, y4)

print("For the next step, hover the TOP RIGHT OF THE GREY BOX (top right of the arrows), WITH THE YELLOW SQUARE AT THE BOTTOM OF YOUR CURSOR")
print(f"We'll do this for stat 1–{'4' if four_stats else '3'}.")
time.sleep(7)

print("Now hover stat 1 number please!")
for i in range(5):
    print(i)
    time.sleep(1)
x5, y5 = pyautogui.position()
print("Stat 1:", x5, y5)

time.sleep(5)

print("Now hover stat 2 number please!")
for i in range(5):
    print(i)
    time.sleep(1)
x6, y6 = pyautogui.position()
print("Stat 2:", x6, y6)

time.sleep(5)

print("Now hover stat 3 number please!")
for i in range(5):
    print(i)
    time.sleep(1)
x7, y7 = pyautogui.position()
print("Stat 3:", x7, y7)

if four_stats:
    time.sleep(5)
    print("Now hover stat 4 number please!")
    for i in range(5):
        print(i)
        time.sleep(1)
    x8, y8 = pyautogui.position()
    print("Stat 4:", x8, y8)

coords = {
    "quick_selection": {"x": x1, "y": y1},
    "calibrate":       {"x": x2, "y": y2},
    "confirm":         {"x": x3, "y": y3},
    "restore":         {"x": x4, "y": y4},
    "stat_1":          {"x": x5, "y": y5},
    "stat_2":          {"x": x6, "y": y6},
    "stat_3":          {"x": x7, "y": y7},
}

if four_stats:
    coords["stat_4"] = {"x": x8, "y": y8}

with open("coordinates.json", "w") as f:
    json.dump(coords, f, indent=2)

print("Coordinates saved to coordinates.json")
print(json.dumps(coords, indent=2))
print("Finished collecting coordinates. Click Restore or Confirm to get back to the Calibration menu")