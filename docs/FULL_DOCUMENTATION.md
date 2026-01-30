# Proactive Robot Assistance: Inferring User Needs via Pose Analysis with a Visual Language Model (VLM)

**First Two Month Project (FTMP)** | University of Tsukuba
**Author:** Muhammad Arifin (D1 | 202530195)
**Supervisor:** Prof. Fumihide Tanaka
**Department:** Intelligent and Mechanical Interaction Systems, Graduate School of Science and Technology

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Motivation and Research Gap](#2-motivation-and-research-gap)
3. [System Architecture](#3-system-architecture)
4. [Project Structure](#4-project-structure)
5. [Module Descriptions](#5-module-descriptions)
6. [Configuration Files](#6-configuration-files)
7. [Hardware Setup](#7-hardware-setup)
8. [Software Dependencies](#8-software-dependencies)
9. [Installation and Setup](#9-installation-and-setup)
10. [Usage Guide](#10-usage-guide)
11. [Experimental Results](#11-experimental-results)
12. [Future Work](#12-future-work)
13. [References](#13-references)

---

## 1. Project Overview

This project implements a **proactive robot assistance system** that uses an embodied Vision-Language Model (VLM) to infer a user's needs from visual perception and trigger a timely, **command-free**, physical assistive action.

Unlike conventional reactive robots that wait for explicit user commands (e.g., "Hey Robot, get me water"), this system observes the user's body language and pose through a camera, reasons about their unspoken needs using Google Gemini 2.0 Flash, and autonomously executes a physical assistive action using an OpenManipulator-X robot arm -- all without any verbal or typed command from the user.

### Key Contributions

1. **A Framework for Command-Free Proactive Assistance** -- The robot acts without waiting for explicit commands.
2. **A Method for Visually-Grounded Need Inference** -- A VLM analyzes user pose, body language, and scene context to infer needs.
3. **An Assistive Paradigm for Non-Command Scenarios** -- Addresses the critical gap where users communicate needs only through silent, real-time body language.

---

## 2. Motivation and Research Gap

Japan's aging population presents a growing need for assistive robotics. The percentage of the population aged 65 and over reached 29.1% in 2023 and is projected to reach 38.7% by 2070, while the working-age population supporting them continues to shrink.

Current assistive robots (e.g., Dry-AIREC, Google Everyday Robots, Hello Robot Stretch) are **fundamentally reactive** -- they are triggered by speech commands, typed input, or teleoperation. Existing proactive approaches focus on:

- **Routine-Based systems**: Learn long-term patterns of object use
- **Environment-Based systems**: Detect anomalies in the physical environment
- **Intent-Based systems**: Reason about user goals from a pre-defined list

**Critical Gap:** None of these systems are designed to handle **unforeseen, non-routine personal needs** that are communicated only through a user's silent, real-time body language.

---

## 3. System Architecture

The system operates as a **three-stage pipeline**:

```
Camera Image
     |
     v
+------------------------------+
| 1. PERCEPTUAL REASONING      |     Gemini 2.0 Flash (VLM)
|    - Pose Analysis (user)    |     Input: Image + Text prompt
|    - Scene Analysis (objects) |     Output: Structured JSON
+------------------------------+
     |
     v
+------------------------------+
| 2. EMBODIED ACTION           |     Gemini 2.0 Flash (LLM)
|    - Action Relevance        |     Input: Text (symptom description)
|      a* = argmax R(a, s)     |     Output: Ranked action list
|    - Task Decomposition      |
+------------------------------+
     |
     v
+------------------------------+
| 3. TASK EXECUTION            |
|    - Motion Generator        |     OpenManipulator-X (Dynamixel)
|      (kinesthetic teaching)  |     Taught path playback
|    - Dynamic Speech          |     Gemini Live API
|      Generation              |     Real-time audio synthesis
+------------------------------+
```

### Stage 1: Perceptual Reasoning

Analyzes a raw visual scene and translates it into a structured, textual description of the user's state and environment.

- **Model:** Gemini 2.0 Flash
- **Input:** Camera image + structured text prompt
- **Output:** JSON with `symptom_description`, `symptom_insights_text` (with confidence percentages), and `action_labels`
- **Pose Analysis:** Identifies body language, posture, and facial cues
- **Scene Analysis:** Identifies relevant objects and spatial relationships

### Stage 2: Embodied Action

Determines the most helpful physical action and decomposes it into executable sub-steps.

- **Action Relevance:** Evaluates each available action against the perceptual analysis using VLM-based relevance scoring
- **Available Actions:** `water`, `tissue`, `blanket`, `glasses`, `remote control AC`, `emergency call`
- **Task Decomposition:** Breaks the selected action into a sequence of robot motions (approach, pick, deliver, return)

### Stage 3: Task Execution

Executes the physical action and communicates with the user.

- **Motion Generator:** Plays back pre-recorded arm trajectories created via kinesthetic teaching
- **Dynamic Speech Generation:** Uses Gemini Live API with a "RobotCare" persona to generate natural, context-aware spoken sentences (not simple TTS)
- **Speaking Gesture:** The arm performs a nodding gesture while speaking for more natural interaction

---

## 4. Project Structure

```
proactive-robot-pose-vlm/
├── README.md                            # This file
├── requirements.txt                     # pip dependencies
├── .env.example                         # Template for API key
├── .gitignore
│
├── src/                                 # All Python source code
│   ├── main.py                          # Application entry point
│   ├── robot_gui.py                     # PyQt6 GUI (image upload, analysis display, action control)
│   ├── robot_action.py                  # QThread workers for analysis and robot action execution
│   ├── llm_analyzer.py                  # Gemini vision model image analysis
│   ├── tts_handler.py                   # Gemini Live API text-to-speech with jitter buffer
│   ├── openmanipulator_x_control.py     # High-level robot orchestrator
│   ├── arm_controller.py               # 4-joint arm control module
│   ├── gripper_controller.py            # Gripper control module (current-based position)
│   ├── dxl_sdk_interface.py             # Low-level Dynamixel SDK abstraction
│   ├── teach_paths.py                   # Interactive kinesthetic teaching script
│   ├── run_taught_path.py               # Taught path playback script
│   └── path_smoother.py                 # Savitzky-Golay filter for path smoothing
│
├── config/                              # All YAML configurations
│   ├── robot_hardware_config.yaml       # Robot hardware configuration
│   ├── llm_config.yaml                  # Gemini model names, prompts, available actions
│   ├── tts_config.yaml                  # TTS model, PyAudio, and persona settings
│   └── teach_config.yaml               # Teaching and recording parameters
│
├── data/                                # Taught motion paths
│   ├── taught_paths.yaml                # Raw recorded motion paths
│   └── smoothed_paths.yaml              # Filtered/smoothed motion paths
│
├── assets/                              # Presentation, images, videos
│   ├── presentation/
│   │   └── 2025_FTMP_0627_Arifin.pdf
│   ├── dataset_images/                  # 30 test images (6 scenarios × 5)
│   └── demo_videos/                     # Performance demo recordings
│
└── docs/                                # Documentation
    ├── CODE_REFERENCE.md
    ├── QUICKSTART.md
    ├── TECHNICAL_REPORT.md
    └── PROJECT_EVOLUTION.md
```

---

## 5. Module Descriptions

### 5.1 `main.py` -- Application Entry Point

Initializes the entire system in sequence:
1. Loads environment variables (`GEMINI_API_KEY` from `.env`)
2. Loads all three YAML configuration files (`robot_hardware_config.yaml`, `llm_config.yaml`, `tts_config.yaml`)
3. Initializes the Google Gemini API client
4. Launches the PyQt6 GUI window

### 5.2 `robot_gui.py` -- PyQt6 GUI

Provides the graphical interface for the system with the following panels:
- **Uploaded Image:** Displays the selected test image
- **Symptom Description:** Shows the VLM's natural language description of the user's condition
- **Symptom Insights:** Shows inferred conditions with confidence percentages (e.g., "Sore Throat: 85%")
- **Suggested Robot Actions:** Lists the VLM's recommended actions (e.g., "water, tissue")
- **Robot Speech:** Real-time log of the robot's spoken output
- **Controls:** "Upload Image" button, "Execute Actions" button, "Auto-execute Actions" checkbox, "Clear All" button

Uses PyQt6 `QThread` for non-blocking operation -- both LLM analysis and robot execution run in background threads with signal-based communication to the GUI.

### 5.3 `robot_action.py` -- Worker Threads

Contains two QThread-based worker classes:

**`AnalysisWorker`:**
- Runs `llm_analyzer.get_image_analysis_for_gui()` in a background thread
- Emits `analysis_complete` signal with structured results

**`RobotActionWorker`:**
- Orchestrates the full robot interaction sequence:
  1. Initialize hardware (OpenManipulatorXControl)
  2. Connect to Gemini Live API for speech
  3. Start speaking gesture loop (async task)
  4. Move to neutral, then face the person
  5. Greet user and describe observed situation
  6. For each suggested action: announce -> pick up item -> return to person -> offer item
  7. Offer continued assistance and return to neutral
- Uses `asyncio` for concurrent speech + gesture coordination

### 5.4 `llm_analyzer.py` -- VLM Image Analysis

Core analysis function `get_image_analysis_for_gui()`:
1. Loads the image via PIL
2. Formats the prompt template with the available actions list
3. Sends to Gemini 2.0 Flash vision model
4. Extracts JSON from the LLM response (handles markdown code blocks)
5. Validates that suggested action labels exist in the available actions list
6. Returns structured dictionary: `symptom_description`, `symptom_insights_text`, `action_labels`, `raw_llm_response`

### 5.5 `tts_handler.py` -- Dynamic Speech Generation

Uses the Gemini Live API (not simple TTS) to generate natural conversational speech:
- **Robot Persona:** "RobotCare" -- a friendly, helpful home assistant
- **Core Intent System:** Receives high-level intents (e.g., "Greet the user") and the LLM dynamically generates appropriate spoken sentences
- **Jitter Buffer:** Pre-buffers 0.75 seconds of audio before playback starts to ensure smooth delivery
- **Streaming:** Audio chunks are collected asynchronously and played via PyAudio at 24kHz

### 5.6 `openmanipulator_x_control.py` -- Robot Orchestrator

High-level controller that coordinates the arm and gripper:
- Initializes `ArmController` and `GripperController` via `DynamixelSDKInterface`
- Manages connection lifecycle (port open/close, torque enable)
- Provides named pose commands: `go_to_home_pose()`, `go_to_rest_pose()`, `go_to_person_pose()`
- Executes taught paths with `play_taught_path()` -- replays waypoints with timing synchronization
- Delegates gripper operations: `open_gripper()`, `close_gripper()`, `pick_object()`, `release_object()`

### 5.7 `arm_controller.py` -- Arm Joint Control

Controls the 4 arm joints (Dynamixel IDs 11, 12, 13, 14):
- Uses `GroupSyncWrite` for synchronized multi-joint position commands
- Configurable motion profiles (velocity, acceleration) for smooth movement
- Dynamic speed calculation in `move_to_pose()` based on the largest joint displacement
- Position tolerance checking with configurable timeout
- Stores three named poses loaded from config: `home_pose`, `rest_pose`, `to_person_pose`

### 5.8 `gripper_controller.py` -- Gripper Control

Controls the gripper motor (Dynamixel ID 15) using current-based position control:
- **Current limiting:** Configurable grasp force (default ~108mA for gentle grasping)
- **Position control:** Open position (1250) and close position (2620)
- **Grasp sequence:** Prepare profiles -> close with current limit -> wait for secure
- **Release sequence:** Open -> wait for completion with tolerance check
- Separate profile tuning for gentle grasp/release operations

### 5.9 `dxl_sdk_interface.py` -- Dynamixel SDK Wrapper

Low-level abstraction providing safe read/write operations:
- Automatic byte-length inference from address names (1-byte for enable/mode, 2-byte for current, 4-byte for position/velocity/acceleration)
- Built-in communication error checking with descriptive error messages
- Wraps `PortHandler` and `PacketHandler` from the Dynamixel SDK

### 5.10 `teach_paths.py` -- Kinesthetic Teaching

Interactive console script for recording arm motions:
1. Disables arm torque (user can physically move the arm)
2. Gripper remains powered (controlled via keyboard)
3. Records waypoints at configurable intervals (default 0.5s): 4 arm joint positions + gripper position + timestamp
4. Press `p` key to trigger gripper grasp/release with automatic stabilization sequence
5. Press `Enter` to finish and save the path to `taught_paths.yaml`
6. Provides a menu interface to teach, list, or delete paths

### 5.11 `run_taught_path.py` -- Path Playback

Replays recorded motion sequences:
- Moves to home pose first
- Iterates through waypoints with timing from the original recording
- Adjustable pacing factor (default 0.6x of original timing)
- Separates arm and gripper commands for independent control
- Waits for physical completion only on the final waypoint

### 5.12 `path_smoother.py` -- Motion Smoothing

Post-processing utility for cleaning noisy recorded paths:
- Applies **Savitzky-Golay filter** (from SciPy) to the 4 arm joint trajectories
- Preserves gripper values unchanged (discrete open/close)
- Optionally rescales timestamps (default 1.2x for smoother playback)
- Converts filtered float values back to integers for hardware

---

## 6. Configuration Files

### `robot_hardware_config.yaml`

| Section | Description |
|---------|-------------|
| `connection_settings` | Serial port, baud rate (1000000), protocol version (2.0) |
| `dynamixel_common_constants` | Control table addresses and data lengths for all register operations |
| `arm_settings` | Joint IDs [11,12,13,14], operating mode, profile defaults, named poses (home, rest, person) |
| `gripper_settings` | Gripper ID (15), operating mode (current-based position), open/close positions, current limit |
| `common_motion_parameters` | Joint tolerance (30), wait timeout (7.0s), gripper timing parameters |

### `llm_config.yaml`

| Key | Description |
|-----|-------------|
| `vision_model_name` | `gemini-2.0-flash` -- model used for image analysis |
| `available_robot_actions` | `[water, tissue, remote control AC, blanket, glasses, emergency call, person, neutral]` |
| `robot_persona_prompt` | System instruction for the "RobotCare" speech persona |
| `llm_analyzer_gui_prompt_template` | Structured prompt template requesting JSON output with symptom description, insights, and action labels |

### `tts_config.yaml`

| Key | Description |
|-----|-------------|
| `live_tts_model` | `models/gemini-2.0-flash-live-001` -- Gemini Live API model for speech |
| `live_tts_connect_config` | Response modality set to `AUDIO` |
| `default_tts_voice` | `Kore` |
| `pyaudio_settings` | Format: Int16, 1 channel, 24kHz playback rate, 1024 chunk size |
| `robot_persona_prompt_tts` | Detailed persona instructions for natural speech generation |

### `teach_config.yaml`

| Section | Key Parameters |
|---------|---------------|
| `general_teaching` | Output file: `taught_paths.yaml`, recording interval: 0.5s, arm stabilize: 0.2s |
| `gripper_sequence_settings` | Grasp prepare: 0.8s, grasp secure delay: 1.0s, release prepare: 1.0s, release max wait: 3.0s |

---

## 7. Hardware Setup

### Robot

- **Model:** ROBOTIS OpenManipulator-X
- **Degrees of Freedom:** 4 (arm) + 1 (gripper)
- **Reachability:** 380mm
- **Payload:** 0.5 kg
- **Motors:** Dynamixel X-series (Protocol 2.0)
  - Arm joints: IDs 11, 12, 13, 14 (Position Control Mode)
  - Gripper: ID 15 (Current-Based Position Control Mode)
- **Communication:** USB serial at 1,000,000 baud

### Environment Setup

Objects placed within the robot's reach on a table:

| # | Object | Action Label | Scenario |
|---|--------|-------------|----------|
| 1 | Mug (with water) | `water` | Thirst / Dehydration |
| 2 | Tissue box | `tissue` | Cold / Allergies |
| 3 | Blanket | `blanket` | Feeling Cold |
| 4 | Glasses | `glasses` | Difficulty Seeing |
| 5 | AC Remote Control | `remote control AC` | Feeling Hot |
| 6 | Phone | `emergency call` | Fall / Physical Emergency |

### System Interface

- **Framework:** PyQt6 with QThread for multi-threaded operation
- **Panels:** Image upload, symptom description, symptom insights, suggested actions, robot speech log
- **Controls:** Upload Image, Execute Actions, Auto-execute checkbox, Clear All

---

## 8. Software Dependencies

| Package | Purpose |
|---------|---------|
| `google-genai` | Google Gemini API client (vision analysis + Live API for TTS) |
| `PyQt6` | Desktop GUI framework |
| `pyaudio` | Audio I/O for speech playback |
| `Pillow` (PIL) | Image loading and processing |
| `dynamixel-sdk` | ROBOTIS Dynamixel motor communication |
| `pyyaml` | YAML configuration file parsing |
| `python-dotenv` | Environment variable management (.env file) |
| `scipy` | Savitzky-Golay filter for path smoothing |
| `numpy` | Numerical operations for path processing |
| `keyboard` | Keyboard input detection for teaching mode |
| `asyncio` | Asynchronous programming (built-in) |

---

## 9. Installation and Setup

### Prerequisites

- Python 3.10+
- ROBOTIS OpenManipulator-X connected via USB
- Google Gemini API key

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mdarifin15/proactive-robot-pose-vlm.git
   cd proactive-robot-pose-vlm
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Linux/Mac
   # .venv\Scripts\activate         # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add your Gemini API key
   ```

5. **Configure the serial port:**
   Edit `config/robot_hardware_config.yaml` and set `device_name` to your robot's serial port:
   ```yaml
   connection_settings:
     device_name: "/dev/ttyUSB0"    # Linux
     # device_name: "COM5"          # Windows
   ```

6. **Teach robot motions (first time only):**
   ```bash
   sudo .venv/bin/python src/teach_paths.py   # sudo required on Linux for keyboard module
   ```
   Follow the interactive prompts to record a motion path for each action label (water, tissue, blanket, glasses, remote control AC, emergency call).

7. **Optionally smooth the recorded paths:**
   ```bash
   python src/path_smoother.py
   ```

8. **Run the application:**
   ```bash
   python src/main.py
   ```

---

## 10. Usage Guide

### Main GUI Workflow

1. **Launch:** Run `python src/main.py`. The GUI window "Symptom Recognition & Robot Assistant" will appear.
2. **Upload Image:** Click "Upload Image" and select a test image showing a person's pose/condition.
3. **Automatic Analysis:** The system sends the image to Gemini 2.0 Flash, which returns:
   - A natural language symptom description
   - Condition likelihoods with confidence percentages
   - A ranked list of 2-3 suggested robot actions
4. **Execute Actions:** Click "Execute Actions" (or enable "Auto-execute Actions" for automatic execution after analysis).
5. **Robot Behavior:** The robot will:
   - Move to neutral position, then face the person
   - Greet the user and describe the observed situation (via Gemini Live speech)
   - For each suggested action: announce it, pick up the corresponding item, deliver it to the user, and offer it with spoken context
   - Offer continued assistance and return to neutral

### Teaching New Motions

```bash
sudo .venv/bin/python src/teach_paths.py
```

1. The arm moves to home position, then torque is disabled
2. Physically guide the arm to the desired positions
3. Press `p` to trigger gripper grasp/release
4. Press `Enter` to save the recorded path
5. Name the path to match an action label (e.g., "water", "tissue")

### Playing Back Motions

```bash
python src/run_taught_path.py
```

Select a previously recorded path from the menu for playback.

---

## 11. Experimental Results

### Dataset

- **30 images** across **6 scenarios** (5 images per category)
- Each image processed **3 times** = **90 total trials**

| Category | Ideal Action | Accuracy |
|----------|-------------|----------|
| Thirst / Dehydration | Water | 89.33% |
| Cold / Allergies | Tissue | 90.67% |
| Feeling Hot | AC Remote Control | 87.27% |
| Feeling Cold | Blanket | 78.18% |
| Difficulty Seeing | Glasses | 96.67% |
| Fall / Physical Emergency | Emergency Call | 100.00% |

### Summary Metrics

| Metric | Value |
|--------|-------|
| **Average VLM Inference Accuracy** | **90.35%** |
| **Robot Task Execution Success** | **96.66%** |

### Key Findings

- **Strongest performance:** Fall/Emergency (100%) and Difficulty Seeing (96.67%) -- these have the most distinct visual poses.
- **Weakest performance:** Feeling Cold (78.18%) -- due to visual ambiguity (poses overlap with chest pain, illness) and model inconsistency across repeated trials of the same ambiguous image.
- **Misclassifications** occur primarily between logically similar categories (e.g., "Feeling Cold" confused with "Cold/Allergies").
- **Robot execution failures** (3.34%) were caused by hardware issues (kinematic limits, gripper slip), not VLM errors.

---

## 12. Future Work

### Enhancing Perception
- **Live Video:** Move from static images to real-time video streams for temporal context analysis
- **Multimodal Input:** Add auditory cues and other sensory modalities for more robust understanding

### Improving Intelligence
- **Adaptive Task Planning:** Dynamically decide actions based on available objects in the environment
- **Double-Check Framework:** Robot moves closer to verify the user's real need before acting
- **Learning from Feedback:** Personalize assistance by learning from user acceptance/rejection of offered help

### Real-World Evaluation
- Conduct formal Human-Robot Interaction (HRI) studies
- Measure user-centric metrics (trust, satisfaction, perceived usefulness)
- Formal Inter-rater Reliability (IRR) study for scoring rubric validation

---

## 13. References

1. Cabinet Office of Japan, "Annual Report on the Ageing Society [Summary] FY2024"
2. T. Tsukakoshi et al., "Close-Fitting Dressing Assistance Based on State Estimation of Feet and Garments with Semantic-based Visual Attention," arXiv, May 2025
3. D. Driess et al., "PaLM-E: An Embodied Multimodal Language Model," ICML, July 2023, pp. 8469-8488
4. A. Padmanabha et al., "Independence in the Home: A Wearable Interface for a Person with Quadriplegia to Teleoperate a Mobile Manipulator," HRI, March 2024
5. M. Patel, S. Chernova, "Proactive Robot Assistance via Spatio-Temporal Object Modeling," CoRL, pp. 881-891, 2022
6. Z. Song et al., "Hazards in Daily Life? Enabling Robots to Proactively Detect and Resolve Anomalies," NAACL-HLT, pp. 7399-7415, 2025

---

## License

This project was developed as part of the First Two Month Project (FTMP) at the University of Tsukuba.

---

*This documentation was generated based on the project presentation (June 27, 2025) and complete source code analysis.*
