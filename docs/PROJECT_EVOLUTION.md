# FTMP Project Evolution Log

This document chronicles the evolution of the FTMP (Full-Task Medical Platform) project from early backend experiments to the final integrated robotic assistant system. The project was developed iteratively across multiple phases, with each phase building on lessons from the previous one. This repository contains the final integrated version (Phase 9).

---

## Summary Timeline

| Phase | Folder | Key Milestone |
|-------|--------|---------------|
| 1 | `Simple_Test/` | Backend-only: Dynamixel motor + Gemini API + audio I/O |
| 2 | `GUI symptom recognition/` | First UI experiments (Tkinter + Gradio), vision analysis only |
| 3 | `Simple test with GUI/` | First GUI + single motor integration (Tkinter) |
| 4 | `Simple test with GUI PyQt 1/` | Migration from Tkinter to PyQt6 |
| 4b | `Simple test with GUI PyQt 2/` | Refined PyQt6 with TTS jitter buffer |
| 5 | `Live API/` | Standalone Gemini Live API reference (bidirectional audio/video) |
| 6 | `Robot Arm Teaching Mode  2/` | First full 4-DOF arm + gripper (monolithic controller) |
| 7 | `Robot Arm Teaching Mode 2.1/` | Refactored controller, continuous path teaching |
| 8 | `Robot Arm Teaching Mode 2.2/` | Modular architecture (arm, gripper, SDK split) |
| 9 | `Robot Arm - GUI Integration/` | Final integrated system with all features combined |

Supporting folders: `Dataset images/`, `Dataset images old/`, `Data Visualization/`, `Video Performance/`, `Dynamixel/`

---

## Feature Comparison Across Versions

| Feature | Phase 1 | Phase 3 | Phase 4 | Phase 6 | Phase 7 | Phase 8 | Phase 9 |
|---------|---------|---------|---------|---------|---------|---------|---------|
| **GUI** | None | Tkinter | PyQt6 | None | None | None | PyQt6 |
| **Robot hardware** | Single motor | Single motor | Single motor | 4-DOF arm + gripper | 4-DOF arm + gripper | 4-DOF arm + gripper | 4-DOF arm + gripper |
| **Controller architecture** | `dynamixel_control.py` | `dynamixel_control.py` | `dynamixel_control.py` | Monolithic `robot_control.py` (40KB) | Refactored `omx_control.py` (49KB) | 3 modules: arm, gripper, SDK | 3 modules + integration |
| **Teaching mode** | None | None | None | Discrete poses | Continuous paths + timestamps | Continuous paths | Paths + Savitzky-Golay smoothing |
| **TTS** | None | Basic Gemini | Gemini + jitter buffer | None | None | None | Live API + jitter buffer + speaking gestures |
| **Config format** | Hardcoded | Single YAML | Single YAML | None | `omx_config.yaml` | Split: robot, LLM, TTS | 3 YAML files |
| **Action set** | N/A | Call Doctor, Take Tools, Drug, Person, Tissue, Water, Cool Compress | Same | Same | water, tissue, blanket, glasses, AC remote, emergency call | Same | Same |

---

## Phase 1: Backend Experiments

**Folder:** `Simple_Test/` (7 Python files, no GUI)

This phase established the foundational backend components in isolation, with no user interface or integrated workflow.

### What was built

- **dynamixel_control.py** (13KB) -- Standalone single-motor controller for the Dynamixel XC330-T288T servo, with error handling for communication failures.
- **llm_analyzer.py** (10KB) -- Basic LLM integration with a hardcoded actions list and simple JSON parsing of Gemini responses.
- **main_live.py** (60KB) -- Tests the Gemini Live API for real-time audio streaming without any GUI.
- **main_speech_llm.py** (60KB) -- Tests speech synthesis via Gemini (standard API, not the Live API).
- **label_pointer_test.py** (13KB) -- Verifies motor pointing to labeled angles, confirming the servo-to-action mapping concept.
- **main_fix_audio.py** (12KB) and **llm_analyzer_fix_audio.py** (11KB) -- Iterative fixes for audio streaming reliability.

### Why it matters

Every subsequent version relies on the patterns established here: Dynamixel SDK communication, Gemini API calling conventions, and audio pipeline design. Building each piece in isolation made it possible to debug hardware and API issues independently before combining them.

---

## Phase 2: Early UI Experiments

**Folder:** `GUI symptom recognition/` (5 files)

The first attempt at a user-facing interface, focused exclusively on vision-based symptom analysis with no robot control.

### What was built

- **symptom_gui.py** (4KB) -- A Tkinter desktop GUI supporting multi-image upload. Each image triggers 3 separate Gemini API calls for analysis.
- **symptom_recognition.py** (3KB) -- An alternative Gradio web interface producing HTML table output.

### Key decisions

Two UI frameworks were prototyped side by side (Tkinter for desktop, Gradio for web). This exploration informed the later decision to move to PyQt6, which offered richer widget capabilities than Tkinter without requiring a browser like Gradio.

---

## Phase 3: First GUI + Single Motor Integration

**Folder:** `Simple test with GUI/` (6 .py files, 3 .yaml configs)

The first version combining a graphical interface with robot control.

### What was built

- **main.py** (133 lines) -- Tkinter launcher with asyncio compatibility for Windows.
- **robot_gui.py** (32.8KB) -- Card-based Tkinter GUI with image upload, LLM analysis, and speech output.
- **symptom_gui.py** (4.9KB) -- Specialized symptom display panel.
- **dynamixel_control.py** -- Single Dynamixel servo control (XC330-T288T).
- **robot_config.yaml** -- Defined the first action set and label-to-degree mapping:
  - Actions: Neutral, Call Doctor, Take Tools, Drug, Person, Tissue, Water, Cool Compress
  - Each action mapped to a specific servo angle for pointing.

### What changed from Phase 1

- Added a GUI layer on top of the existing backend.
- Introduced YAML configuration instead of hardcoded values.
- Combined image analysis, LLM response, TTS output, and motor pointing into a single workflow.

---

## Phase 4: PyQt Migration

### Phase 4a

**Folder:** `Simple test with GUI PyQt 1/` (11 files)

- Switched the entire GUI from Tkinter to **PyQt6** for better widget support and modern look.
- **robot_gui.py** grew to 37KB with the extended PyQt interface.
- **main_cli.py** (11KB) -- CLI version for testing the Live API async/await pattern without the GUI.
- Still single motor, no arm or gripper.

### Phase 4b

**Folder:** `Simple test with GUI PyQt 2/` (9 .py, 2 .yaml, 2 videos, 1 audio)

- Refined the PyQt6 GUI further.
- **tts_test.py** (236 lines) -- Standalone test harness for TTS jitter buffer tuning.
- **tts_handler.py** -- Added a 0.75-second prebuffer (jitter buffer) to eliminate audio gaps during speech output.
- **speech_generation.py** (1.5KB) -- Minimal speech wrapper for cleaner API calls.
- Test videos dated 29.05.2025 captured early demos.

### Why PyQt

Tkinter lacked the layout flexibility and styling needed for a card-based medical interface. PyQt6 provided better support for responsive layouts, styled widgets, and integration with asyncio event loops.

---

## Phase 5: Standalone Gemini Live API Reference

**Folder:** `Live API/` (2 files, 14KB total)

A standalone reference implementation of the Gemini 2.0 Flash Live API, not integrated with the robot.

### What was built

- **Get_started_LiveAPI.py** -- Full async bidirectional pipeline: microphone input (16kHz), camera capture (JPEG 1024x1024), screen capture, and audio playback (24kHz).
- **Multimodal_Interaction.py** -- Minor variation of the same pipeline.

### Purpose

This folder served as a clean reference for the Live API integration pattern. The bidirectional streaming approach tested here was later incorporated into the final GUI integration, enabling real-time conversational interaction with the robot.

---

## Phase 6: Full Robot Arm (Monolithic)

**Folder:** `Robot Arm Teaching Mode  2/` (18 files)

The first version with a complete OpenManipulator-X robot arm (4 joints + gripper), replacing the single pointing motor.

### What was built

- **robot_control.py** (40KB) -- A monolithic controller combining arm movement, gripper operation, and orchestration logic in a single file.
- **robot_control old.py** (40KB) -- Earlier backup of the same file, preserved during development.
- **teach_poses.py** (9KB) -- Discrete pose teaching: manually move the arm to a position and save it.
- **taught_poses.yaml** -- Simple storage of named poses (position snapshots).

### The monolithic problem

Putting all hardware control into one 40KB file made the code difficult to maintain, test, and extend. Arm logic, gripper logic, and high-level orchestration were tangled together. This directly motivated the refactoring in Phase 7.

---

## Phase 7: Refactored Controller + Continuous Paths

**Folder:** `Robot Arm Teaching Mode 2.1/` (15 files, 5.8MB including demo video)

A significant improvement in both code quality and teaching capability.

### What changed

- **omx_control.py** (49.4KB) -- Refactored from the monolithic `robot_control.py`. Still a single file but with cleaner internal structure and OpenManipulator-X-specific naming.
- **teach_paths.py** -- Upgraded from discrete pose teaching to **continuous path recording**, capturing waypoints with timestamps as the arm is physically guided.
- **run_taught_path.py** -- Plays back recorded paths with proper timing.
- **taught_paths.yaml** -- Stores waypoint-based trajectories with timestamps (not just static positions).
- **teach_config.yaml** -- Configurable recording parameters (sampling rate, etc.).
- **omx_config.yaml** -- Hardware-specific configuration for the OpenManipulator-X.

### Action set update

The action set was revised to match the presentation scenario:
- **Old:** Call Doctor, Take Tools, Drug, Person, Tissue, Water, Cool Compress
- **New:** water, tissue, blanket, glasses, AC remote, emergency call

### Evidence

- Demo video: `Direct Teaching & Playback Motion.mp4`

---

## Phase 8: Modular Architecture

**Folder:** `Robot Arm Teaching Mode 2.2/` (19 files)

The cleanest code architecture in the project, splitting the monolithic controller into proper modules.

### The split

The single `omx_control.py` (49KB) was decomposed into three focused modules:

| Module | Size | Responsibility |
|--------|------|----------------|
| `arm_controller.py` | 13KB | Arm joint control (4 DOF) |
| `gripper_controller.py` | 17KB | Gripper open/close/force control |
| `dxl_sdk_interface.py` | 8KB | Low-level Dynamixel SDK wrapper |

### Configuration changes

- **robot_hardware_config.yaml** -- New comprehensive unified hardware config, replacing `omx_config.yaml`.
- **tts_config.yaml** -- Separated from `llm_config.yaml` for independent tuning of speech parameters.

### Why this matters

The modular split made it possible to develop and test arm control, gripper control, and SDK communication independently. This clean separation was essential for the final integration phase, where these modules were combined with the GUI, LLM, and TTS systems.

---

## Phase 9: Final Integration

**Folder:** `Robot Arm - GUI Integration/` (24 files)

The culmination of all previous work: a fully integrated system combining the PyQt6 GUI, modular robot control, path teaching and playback, LLM analysis, TTS with speaking gestures, and the Gemini Live API.

### What was combined

- **PyQt6 GUI** from Phase 4
- **Modular robot control** (arm, gripper, SDK) from Phase 8
- **Continuous path teaching and playback** from Phase 7
- **Gemini Live API** bidirectional streaming from Phase 5
- **TTS with jitter buffer** from Phase 4b

### What was added new

- **path_smoother.py** -- Savitzky-Golay filter for smoothing recorded teaching paths, producing `smoothed_paths.yaml` from raw recordings.
- **Speaking gestures** -- The robot performs a subtle nodding motion during TTS playback, giving a more natural conversational feel.
- **main.py** -- Marked "Final Corrected Version", handles the full application lifecycle.
- **robot_action.py** -- Marked "Corrected for ValueError and includes all features", orchestrates the action execution pipeline.

### Configuration architecture

Three separate YAML files, each independently tunable:

1. **robot_hardware_config.yaml** -- Joint IDs, angle limits, speed profiles, home positions
2. **llm_config.yaml** -- Gemini model selection, prompt templates, action mappings
3. **tts_config.yaml** -- Voice parameters, jitter buffer size, audio format settings

### Final action set

water, tissue, remote control AC, blanket, glasses, emergency call

---

## Supporting Folders

### Dataset images/
30 JPEG test images labeled 1A through 6E (6 scenarios, 5 images each). Used for evaluating the symptom recognition accuracy of the LLM pipeline.

### Dataset images old/
20 older test images from an earlier dataset version, retained for comparison.

### Data Visualization/
- **plot_matrix.py** -- Generates confusion matrix heatmaps for evaluating recognition performance.
- **CM_RelevanceScore_GUI.csv** -- Raw evaluation data.
- **Figure_1.png** -- Generated confusion matrix visualization.

### Video Performance/
10 MP4 recordings documenting the robot performing various tasks, used for presentation and evaluation purposes.

### Dynamixel/
Contains the DynamixelSDK-3.8.3 third-party library, the low-level driver used by all robot control code throughout the project.

---

## Key Technical Evolution Paths

### GUI Framework
```
None --> Gradio (web) --> Tkinter (desktop) --> PyQt6 (desktop, final)
```

### Robot Hardware
```
None --> Single Dynamixel motor (pointing) --> Full 4-DOF arm + gripper (OpenManipulator-X)
```

### Controller Architecture
```
None --> dynamixel_control.py (single motor, 13KB)
     --> robot_control.py (monolithic, 40KB)
     --> omx_control.py (refactored, 49KB)
     --> arm_controller.py + gripper_controller.py + dxl_sdk_interface.py (modular, 38KB total)
```

### Teaching System
```
None --> Discrete pose snapshots --> Continuous path recording with timestamps --> Paths + Savitzky-Golay smoothing
```

### Text-to-Speech
```
None --> Basic Gemini TTS --> Gemini Live API --> Live API + 0.75s jitter buffer --> Jitter buffer + speaking gestures (nodding)
```

### Configuration Management
```
Hardcoded values --> Single robot_config.yaml --> omx_config.yaml --> 3 split files (robot_hardware, llm, tts)
```

### Action Set
```
Neutral, Call Doctor, Take Tools, Drug, Person, Tissue, Water, Cool Compress
    -->
water, tissue, blanket, glasses, remote control AC, emergency call
```

---

*This document was generated on 2026-01-30 as a retrospective analysis of the full FTMP project development history.*
