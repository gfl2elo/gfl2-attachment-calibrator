import pyautogui
import time
import json

# WARNING VIBE CODED SLOP AHEAD!

with open("coordinates.json", "r") as f:
    coords = json.load(f)

while True:
    choice = input("Update 3 stats or 4 stats? (3/4) [4 recommended]: ").strip()
    if choice in {"3", "4"}:
        four_stats = choice == "4"
        break
    print("Invalid input. Type 3 or 4.")

print("Get ready...")
time.sleep(5)

print("Hover stat 1!")
for i in range(5):
    print(i)
    time.sleep(1)
x5, y5 = pyautogui.position()
print("Stat 1:", x5, y5)

time.sleep(5)

print("Hover stat 2!")
for i in range(5):
    print(i)
    time.sleep(1)
x6, y6 = pyautogui.position()
print("Stat 2:", x6, y6)

time.sleep(5)

print("Hover stat 3!")
for i in range(5):
    print(i)
    time.sleep(1)
x7, y7 = pyautogui.position()
print("Stat 3:", x7, y7)

if four_stats:
    time.sleep(5)
    print("Hover stat 4!")
    for i in range(5):
        print(i)
        time.sleep(1)
    x8, y8 = pyautogui.position()
    print("Stat 4:", x8, y8)

coords["stat_1"] = {"x": x5, "y": y5}
coords["stat_2"] = {"x": x6, "y": y6}
coords["stat_3"] = {"x": x7, "y": y7}

if four_stats:
    coords["stat_4"] = {"x": x8, "y": y8}

with open("coordinates.json", "w") as f:
    json.dump(coords, f, indent=2)

print("Done. Updated stat coordinates:")
print(f"  stat_1: {coords['stat_1']}")
print(f"  stat_2: {coords['stat_2']}")
print(f"  stat_3: {coords['stat_3']}")
if four_stats:
    print(f"  stat_4: {coords['stat_4']}")