# Attachment Calibrator — Installation Guide

## 0. Compatibility

This script was developed and tested on **Windows only**. It may work on macOS or Linux but this has not been tested and is not supported. The installation steps in this guide are written for Windows.
## 1. Python

Check if Python is installed by opening a terminal and running:
```
python --version
```
If you get a version number (3.10 or higher required), you're good. If not, download and install Python from https://www.python.org/downloads/. During installation, **make sure to check "Add Python to PATH"**.

---

## 2. Git

Check if Git is installed:
```
git --version
```
If not installed, download it from https://git-scm.com/downloads and install with default settings.

---

## 3. Clone the repository

Navigate to the folder where you want the project to live, then run:
```
git clone https://github.com/gfl2elo/attachment-calibrator
cd attachment-calibrator
```

---

## 4. Install Python dependencies
```
pip install -r requirements.txt
```

---

## 5. Tesseract OCR

### 5.1 Download the installer
Get the Tesseract installer from:
https://github.com/UB-Mannheim/tesseract/wiki

Download the latest Windows installer (e.g. `tesseract-ocr-w64-setup-5.x.x.exe`).

### 5.2 Install and save the path
Run the installer. On the "Choose Install Location" screen, note down the install path — by default it is:
```
C:\Program Files\Tesseract-OCR
```
Complete the installation.

### 5.3 Add Tesseract to PATH
1. Press `Windows + S` and search for **"Environment Variables"**, then click **"Edit the system environment variables"**
2. In the System Properties window, click **"Environment Variables..."**
3. Under **"System variables"**, find and select **"Path"**, then click **"Edit"**
4. Click **"New"** and paste your Tesseract install path, e.g.:
```
C:\Program Files\Tesseract-OCR
```
5. Click OK on all windows to save.

### 5.4 Verify the installation
Open a **new** terminal window and run:
```
tesseract --version
```
You should see a version number. If you get an error, double-check the PATH step above.

---

## 6. Legacy OCR data

For better accuracy with game fonts, you need the legacy `eng.traineddata` file.

1. Go to https://github.com/tesseract-ocr/tessdata
2. Find `eng.traineddata` in the file list and download it (click the file, then "Download raw file")
3. Place it in your Tesseract `tessdata` folder, replacing the existing file:
```
C:\Program Files\Tesseract-OCR\tessdata\eng.traineddata
```

---

You're now ready to use the script. Continue with the usage guide below.

---

---

# Attachment Calibrator — Usage Guide

## Running the scripts

You can run the scripts in two ways:

**Option A (recommended) — IDE:**
Open the project folder in an IDE of your choice (e.g. PyCharm, VS Code) and use the built-in run button to execute the scripts directly.

**Option B — Command line:**
Open a terminal, navigate to the project folder and activate the virtual environment, then run the script:
```
cd path\to\attachment-calibrator
.venv\Scripts\activate
python mover.py
```

## 1. Game settings

Before doing anything else, open the game settings, navigate to **Graphics**, and set the window mode to **Maximize**. Once set, **do not move the game window** — the coordinates are tied to its position on screen.

---

## 2. Navigate to the calibration screen

In-game, navigate to the calibration screen.

> 📷 *[IMAGE PLACEHOLDER: calibration screen navigation]*

---

## 3. Prepare the calibration screen

This step is important. Make sure you are using a **piece that has already been upgraded at least once**. Before proceeding, clear the **"Are you sure you want to restore..."** confirmation popup by checking **"Do not show again today"** and dismissing it. If you skip this, the script will break.

---

## 4. Collect coordinates

The script works by clicking specific positions on your screen, so you need to tell it where things are first.

Run the coordinate collector:
```
python get_coordinates.py
```

Follow the on-screen instructions. A few things to keep in mind:

- For **buttons** (Quick Selection, Calibrate, Confirm, Restore): hovering roughly over the middle of the button is fine.
- For **stat values** (the percentage numbers): precision matters. Align the **yellow box at the bottom of your cursor** to the **top-right corner of the grey stat box**, as shown below.

> 📷 *[IMAGE PLACEHOLDER: cursor alignment on stat box corner]*

When asked whether to save 3 or 4 stat coordinates, **4 is recommended** as it allows you to use both modes. You need 4 coordinates if you plan to calibrate muzzles.

The coordinates will be saved to `coordinates.json`. If you weren't confident about your placement, re-run `get_coordinates.py` and redo it — it will overwrite the previous file. If you only need to redo the stat positions, run `update_stat_cords.py` instead.

---

## 5. Run the calibrator

From the calibration main screen, run:
```
python mover.py
```

Follow the on-screen instructions:

1. **Select a mode:**
   - **Mode 1** — regular attachment (3 stats, works with 3 or 4 saved coordinates)
   - **Mode 2** — muzzle (4 stats, requires 4 saved coordinates)

   > **Note:** Mode 2 will not work if you only saved 3 stat coordinates during setup.

2. **Set your goal stat total:** After selecting a mode you will be asked to enter a desired stat total. This is the sum of all stat percentages added together — for example, 200% + 150% + 120% = **470** (enter the number without the % sign). The script will keep rerolling until this total is reached or exceeded.
   - Mode 1 default: **450** (range: 100–600)
   - Mode 2 default: **600** (range: 100–800)

The script will then count down and start automatically.

### Controls
| Key | Action |
|-----|--------|
| F9  | Pause / Resume |
| F10 | Stop the script |

---

## Important disclaimers

### OCR accuracy
The OCR reading is **not 100% accurate** and will make errors. The script has several built-in correction rules to catch common misreads, but it is not perfect. If you notice a consistent pattern — for example, 70% always being read as 710% — please report it on Discord (**elo_777**) so a correction rule can be added.

### Gold consumption
The script runs continuously until the desired stat total is reached. It does **not** detect when you run out of gold (yet) and will keep clicking regardless. At approximately **120,000 gold per minute**, make sure you have enough prepared before starting. Running out mid-session means the script will keep running but no calibrations will actually happen, wasting time.

### Vibe coded slop ahead
Everything is vibe coded. Please don't have unreasonable expectations.

---

## 6. Test run recommendations

For your first use, do **2-3 test runs** and pause after stat collection (F9) to inspect the debug images saved in the project folder (`debug_stat_1_masked.png`, etc.). The cropped boxes should show the percentage numbers clearly on a black background. If the numbers look cut off or misaligned, re-run `update_stat_cords.py` to redo just the stat coordinates.

---

## Troubleshooting

### Bad reads and retries
If the script gets a bad OCR read, it automatically restores the previous calibration and starts a new attempt. It does not give up on its own — if your coordinates are badly placed it can loop indefinitely. If you notice it cycling without ever succeeding, pause with F9, check the debug images, and re-run `update_stat_cords.py`.

### Coordinates are off
If the cropped debug images are landing in the wrong place, update just the stat coordinates with:
```
python update_stat_cords.py
```

If you're still stuck, reach out on Discord: **elo_777**