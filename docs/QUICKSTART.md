# Quickstart Guide

Proactive Robot Assistance System: Google Gemini VLM + OpenManipulator-X + PyQt6 GUI.

---

## 1. Prerequisites

| Requirement | Details |
|---|---|
| Python | 3.10+ |
| OS | Linux (Ubuntu recommended) or macOS. Windows partial support. |
| Hardware | ROBOTIS OpenManipulator-X (Dynamixel IDs 11-14 arm, 15 gripper) |
| USB Adapter | U2D2 or equivalent FTDI USB-to-serial for Dynamixel bus |
| API Key | Google Gemini API key (obtain from Google AI Studio) |
| Webcam/Images | At least one test image of a person for VLM analysis |

---

## 2. Quick Install

```bash
# 1. Clone the repository
git clone https://github.com/mdarifin15/proactive-robot-pose-vlm.git
cd proactive-robot-pose-vlm

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file with your Gemini API key
cp .env.example .env
# Edit .env and replace the placeholder with your actual key
```

> **Note:** `keyboard` requires root on Linux (`sudo`) for the teach script. `pyaudio` requires `portaudio` system library (`sudo apt install portaudio19-dev` on Ubuntu).

---

## 3. Hardware Connection

Edit `config/robot_hardware_config.yaml`, section `connection_settings`:

```yaml
connection_settings:
  device_name: "/dev/ttyUSB0"   # Linux typical
  # device_name: "/dev/tty.usbserial-XXXX"  # macOS
  # device_name: "COM5"  # Windows
  baud_rate: 1000000
  protocol_version: 2.0
```

**Find your port:**
```bash
# Linux
ls /dev/ttyUSB*

# macOS
ls /dev/tty.usbserial-*
```

Ensure your user has serial port access:
```bash
sudo usermod -aG dialout $USER   # Linux, then log out/in
```

---

## 4. First Run (Without Robot)

This lets you test VLM image analysis without any robot hardware connected.

1. Activate your venv: `source .venv/bin/activate`
2. Run the GUI:
   ```bash
   python src/main.py
   ```
3. Click **"Upload Image"** and select a photo of a person.
4. The GUI sends the image to Gemini and displays:
   - **Symptom Description** -- a short paragraph about the observed condition
   - **Symptom Insights** -- bulleted list with confidence percentages
   - **Suggested Robot Actions** -- ranked list (e.g., `water`, `tissue`, `blanket`)
5. The **"Execute Actions"** button will appear enabled, but without a robot connected it will fail. Leave **"Auto-execute Actions"** unchecked.

> The TTS (text-to-speech) feature will attempt to speak the description aloud via PyAudio. If PyAudio is not configured, a warning appears in the Robot Speech panel and the system continues without audio.

---

## 5. First Run (With Robot)

### Step A: Teach Motion Paths

Before the robot can act, you must teach it paths for each action (e.g., `water`, `tissue`, `blanket`).

1. Connect the OpenManipulator-X via USB.
2. Run the teaching script (requires `sudo` on Linux for keyboard input):
   ```bash
   sudo .venv/bin/python src/teach_paths.py
   ```
3. The interactive menu appears:
   ```
   Menu: 't'-teach new, 'l'-list, 'd'-delete, 'q'-quit
   ```
4. Press **`t`** to teach a new path. Enter the action name exactly as listed in `config/llm_config.yaml` (e.g., `water`).
5. The robot moves to its **home pose**, then prompts you:
   ```
   Press Enter to disable ARM torque and START recording...
   ```
6. Press **Enter**. The arm goes limp -- physically guide it along the desired path.
7. Keyboard controls during recording:
   | Key | Action |
   |---|---|
   | **p** | Toggle gripper GRASP / RELEASE (alternates each press) |
   | **Enter** | Stop recording and save the path |
8. Waypoints are recorded automatically every 0.5s.
9. Repeat for each action (`tissue`, `blanket`, `glasses`, etc.).
10. Paths are saved to `data/taught_paths.yaml`.

### Step B: Run the Full System

```bash
python src/main.py
```

1. Upload an image.
2. Review the suggested actions.
3. Check **"Auto-execute Actions"** to let the robot act immediately, or click **"Execute Actions"** manually.
4. The robot will play back the taught path for the top-ranked action, with TTS narration.

---

## 6. GUI Walkthrough

The window is titled **"Symptom Recognition & Robot Assistant"** (850x700 default).

```
+------------------------------+------------------------------------------+
|                              |  [Symptom Description]                   |
|   [Uploaded Image]           |  Paragraph from Gemini about the person  |
|                              |------------------------------------------|
|   Displays selected photo    |  [Symptom Insights]                      |
|                              |  - Common Cold: 80%                      |
|   [Upload Image] button      |  - Fatigue: 65%                          |
|                              |------------------------------------------|
|                              |  [Suggested Robot Actions]               |
|                              |  1. tissue  2. water  3. blanket         |
+------------------------------+------------------------------------------+
|  [Robot Speech]                                                         |
|  Shows TTS status and spoken text log                                   |
+-------------------------------------------------------------------------+
| [ ] Auto-execute Actions    [Execute Actions] [Clear All] [About]       |
+-------------------------------------------------------------------------+
```

| Element | Description |
|---|---|
| **Upload Image** | Opens file dialog; triggers Gemini analysis on selection |
| **Symptom Description** | Read-only text area with Gemini's description |
| **Symptom Insights** | Bulleted conditions with confidence % |
| **Suggested Robot Actions** | Ranked action list from Gemini |
| **Robot Speech** | Log of TTS output and system messages |
| **Auto-execute Actions** | Checkbox; if checked, robot executes immediately after analysis |
| **Execute Actions** | Manual trigger for robot to perform suggested actions |
| **Clear All** | Resets all fields and image |
| **About** | Shows application info dialog |

---

## 7. Common Issues

### Serial Port Not Found
```
FATAL ERROR: Could not open port /dev/ttyUSB0
```
- Check cable connection and run `ls /dev/ttyUSB*`.
- Update `device_name` in `config/robot_hardware_config.yaml`.
- Add user to `dialout` group: `sudo usermod -aG dialout $USER` (re-login required).

### Gemini API Key Error
```
CRITICAL ERROR: GEMINI_API_KEY not set. Exiting.
```
- Ensure `.env` file exists in the project root with `GEMINI_API_KEY=your_key`.
- Verify the key is valid at Google AI Studio.

### PyAudio / TTS Failure
```
System: TTS is disabled (PyAudio or SDK init failed).
```
- Install system dependency: `sudo apt install portaudio19-dev` (Ubuntu/Debian).
- Reinstall: `pip install pyaudio`.
- TTS failure is non-fatal; the GUI continues to work without audio.

### Dynamixel Communication Errors
```
ERROR: Failed to move to Home / Robot not connected
```
- Confirm `baud_rate: 1000000` matches your U2D2 settings.
- Ensure motor IDs match config: arm joints `[11, 12, 13, 14]`, gripper `15`.
- Check for hardware error status (overheating, overload). Power cycle the robot.
- Verify `protocol_version: 2.0` (X-series Dynamixels use Protocol 2.0).

### Keyboard Module Permission (Linux)
```
ImportError: You must be root to use this library on linux.
```
- Run `teach_paths.py` with `sudo`: `sudo .venv/bin/python src/teach_paths.py`.

---

## 8. Quick Config Reference

### config/robot_hardware_config.yaml

| Key | Default | What to Change |
|---|---|---|
| `connection_settings.device_name` | `/dev/tty.usbserial-FTA2U31G` | Your serial port path |
| `connection_settings.baud_rate` | `1000000` | Must match Dynamixel bus baudrate |
| `arm_settings.joint_ids` | `[11, 12, 13, 14]` | Your motor IDs |
| `arm_settings.home_pose` | `[2048, 1640, 2630, 1840]` | Arm home position (raw Dynamixel values) |
| `arm_settings.rest_pose` | `[2048, 1024, 3040, 2300]` | Arm rest/stow position |
| `arm_settings.default_profile_vel` | `500` | Movement speed (0.229 rpm/unit) |
| `gripper_settings.id` | `15` | Gripper motor ID |
| `gripper_settings.open_pos` | `1250` | Gripper open position |
| `gripper_settings.close_pos` | `2620` | Gripper close position |
| `gripper_settings.default_grasp_current_limit` | `40` | Grasp force (~107 mA) |

### config/llm_config.yaml

| Key | Default | What to Change |
|---|---|---|
| `vision_model_name` | `gemini-2.0-flash` | Gemini model to use |
| `available_robot_actions` | `[water, tissue, remote control AC, blanket, glasses, emergency call, person, neutral]` | Add/remove actions the robot can perform |

### config/tts_config.yaml

| Key | Default | What to Change |
|---|---|---|
| `live_tts_model` | `models/gemini-2.0-flash-live-001` | TTS model |
| `default_tts_voice` | `Kore` | Voice name |
| `pyaudio_settings.playback_rate` | `24000` | Audio sample rate |

### config/teach_config.yaml

| Key | Default | What to Change |
|---|---|---|
| `general_teaching.paths_output_file` | `taught_paths.yaml` | Output file for recorded paths |
| `general_teaching.recording_interval_s` | `0.5` | Waypoint capture rate (seconds) |
| `gripper_sequence_settings.grasp_secure_delay_s` | `1.0` | Wait time after grasp |
| `gripper_sequence_settings.release_max_wait_s` | `3.0` | Max wait for gripper to open |
