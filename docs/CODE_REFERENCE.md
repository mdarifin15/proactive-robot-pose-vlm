# Code Reference -- Robot Arm GUI Integration

Complete API reference for all Python modules in the Symptom Recognition & Robot Assistant project.

---

## Table of Contents

1. [main.py](#mainpy)
2. [robot_gui.py](#robot_guipy)
3. [robot_action.py](#robot_actionpy)
4. [llm_analyzer.py](#llm_analyzerpy)
5. [tts_handler.py](#tts_handlerpy)
6. [openmanipulator_x_control.py](#openmanipulator_x_controlpy)
7. [arm_controller.py](#arm_controllerpy)
8. [gripper_controller.py](#gripper_controllerpy)
9. [dxl_sdk_interface.py](#dxl_sdk_interfacepy)
10. [teach_paths.py](#teach_pathspy)
11. [run_taught_path.py](#run_taught_pathpy)
12. [path_smoother.py](#path_smootherpy)

---

## main.py

**Overview:** Application entry point. Loads environment variables, configuration files, initializes the Gemini client, creates the PyQt6 application, and launches the GUI window.

### Dependencies

| Import | Source |
|--------|--------|
| `sys` | stdlib |
| `os` | stdlib |
| `yaml` | PyYAML |
| `load_dotenv` | python-dotenv |
| `QApplication` | PyQt6.QtWidgets |
| `genai` | google-genai SDK |
| `tts_handler` | local module |
| `robot_gui` | local module |

### Module-Level Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PROJECT_ROOT` | *(computed)* | Project root directory (parent of `src/`) |
| `CONFIG_DIR` | `PROJECT_ROOT/config` | Configuration directory |
| `CONFIG_ROBOT_PATH` | `CONFIG_DIR/robot_hardware_config.yaml` | Path to robot hardware configuration |
| `CONFIG_LLM_PATH` | `CONFIG_DIR/llm_config.yaml` | Path to LLM configuration |
| `CONFIG_TTS_PATH` | `CONFIG_DIR/tts_config.yaml` | Path to TTS configuration |

### Functions

#### `load_all_configurations()`

Loads all three YAML configuration files (robot, LLM, TTS).

| | Details |
|---|---|
| **Parameters** | None |
| **Returns** | `dict` or `None` -- Keys: `"robot"`, `"llm"`, `"tts"`, each containing the parsed YAML dict. Returns `None` on any failure. |

### Entry Point (`__main__`)

Execution sequence:
1. Calls `load_dotenv()` and reads `GEMINI_API_KEY` from environment.
2. Calls `load_all_configurations()`.
3. Initializes `genai.Client(api_key=...)`.
4. Creates `QApplication` and `RobotAppGUI` window.
5. Calls `app.exec()`.

### Configuration Keys Expected

**Environment variables:**
- `GEMINI_API_KEY` -- Google Gemini API key (required).

---

## robot_gui.py

**Overview:** Defines the main PyQt6 GUI window (`RobotAppGUI`). Handles image upload, displays analysis results, triggers robot action execution, and manages worker threads.

### Dependencies

| Import | Source |
|--------|--------|
| `sys`, `os`, `asyncio`, `traceback` | stdlib |
| `QApplication`, `QWidget`, `QVBoxLayout`, `QHBoxLayout`, `QPushButton`, `QLabel`, `QTextEdit`, `QFileDialog`, `QCheckBox`, `QMessageBox`, `QFrame` | PyQt6.QtWidgets |
| `QPixmap`, `QFont`, `QPalette`, `QColor` | PyQt6.QtGui |
| `Qt`, `pyqtSlot` | PyQt6.QtCore |
| `WorkerSignals`, `AnalysisWorker`, `RobotActionWorker` | robot_action (local) |
| `tts_handler` | local module |

### Class: `RobotAppGUI(QWidget)`

Main application window.

#### Constructor

```python
RobotAppGUI(config_robot, config_llm, config_tts, gemini_client, parent=None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_robot` | `dict` | Parsed `robot_hardware_config.yaml` |
| `config_llm` | `dict` | Parsed `llm_config.yaml` |
| `config_tts` | `dict` | Parsed `tts_config.yaml` |
| `gemini_client` | `genai.Client` | Initialized Gemini client |
| `parent` | `QWidget` or `None` | Optional parent widget |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `config_robot` | `dict` | Robot hardware configuration |
| `config_llm` | `dict` | LLM configuration |
| `config_tts` | `dict` | TTS configuration |
| `gemini_client` | `genai.Client` | Gemini API client |
| `pya_instance` | `pyaudio.PyAudio` or `None` | PyAudio instance for TTS |
| `current_image_path` | `str` or `None` | Path to currently loaded image |
| `current_qt_pixmap` | `QPixmap` or `None` | Scaled pixmap of the loaded image |
| `current_suggested_actions` | `list[str]` | Action labels from the last analysis |
| `symptom_description_for_speech` | `str` | Symptom description text for speech |
| `analysis_worker_thread` | `AnalysisWorker` or `None` | Reference to the running analysis thread |
| `action_worker_thread` | `RobotActionWorker` or `None` | Reference to the running action thread |

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `_init_ui()` | -- | `None` | Builds the complete GUI layout: image card, symptom description, insights, actions, speech area, buttons, status bar, and disclaimer. |
| `_create_card(title=None)` | `title`: `str` or `None` | `tuple[QFrame, QVBoxLayout]` | Helper that creates a styled card frame with optional title label. Returns the frame and its layout. |
| `_update_text_widget(widget, text_content)` | `widget`: `QTextEdit`, `text_content`: any | `None` | Sets plain text on a `QTextEdit`, converting `\\n` literals to newlines. |
| `_append_robot_speech(text_to_append)` | `text_to_append`: `str` | `None` | **Slot** (`pyqtSlot(str)`). Appends text to the robot speech area and scrolls to bottom. |
| `_update_status_label(text)` | `text`: `str` | `None` | **Slot** (`pyqtSlot(str)`). Sets the status bar label text. |
| `_clear_all_results()` | -- | `None` | Resets all display widgets, state variables, and disables the execute button. Blocked if workers are running. |
| `_show_about_dialog()` | -- | `None` | Shows an informational "About" message box. |
| `_select_and_analyze_image()` | -- | `None` | Opens a file dialog, loads the selected image, displays it, and starts an `AnalysisWorker` thread. |
| `_on_analysis_thread_finished()` | -- | `None` | **Slot** (`pyqtSlot()`). Re-enables the upload button and cleans up the analysis worker reference. |
| `_update_gui_with_analysis_results(analysis_results_dict)` | `analysis_results_dict`: `dict` | `None` | **Slot** (`pyqtSlot(dict)`). Populates description, insights, and action widgets from analysis results. Auto-executes if checkbox is checked. |
| `_trigger_robot_execution()` | -- | `None` | Creates and starts a `RobotActionWorker` thread with the current suggested actions. |
| `_on_actions_finished(message)` | `message`: `str` | `None` | **Slot** (`pyqtSlot(str)`). Re-enables buttons and cleans up the action worker reference. |
| `_handle_worker_error(error_message)` | `error_message`: `str` | `None` | **Slot** (`pyqtSlot(str)`). Displays error dialog, updates status, and cleans up the originating worker. |
| `_disconnect_worker_signals(worker_thread_ref, is_analysis_worker)` | `worker_thread_ref`: `QThread`, `is_analysis_worker`: `bool` | `None` | Safely disconnects all signals from the specified worker to prevent stale connections. |
| `closeEvent(event)` | `event`: `QCloseEvent` | `None` | Override. Prompts for confirmation, waits for active threads, terminates PyAudio, and closes the application. |

#### UI Widgets (created in `_init_ui`)

| Widget Attribute | Type | Purpose |
|-----------------|------|---------|
| `image_display_label` | `QLabel` | Displays uploaded image |
| `upload_button` | `QPushButton` | Triggers image upload |
| `symptom_desc_text` | `QTextEdit` (read-only) | Shows symptom description |
| `symptom_insights_text` | `QTextEdit` (read-only) | Shows symptom insights |
| `robot_actions_text` | `QTextEdit` (read-only) | Shows suggested action labels |
| `robot_speech_area` | `QTextEdit` (read-only) | Running log of robot speech |
| `auto_execute_checkbox` | `QCheckBox` | Toggle auto-execute after analysis |
| `execute_button` | `QPushButton` | Triggers robot action execution |
| `clear_button` | `QPushButton` | Clears all results |
| `about_button` | `QPushButton` | Shows about dialog |
| `status_label` | `QLabel` | Status bar text |
| `disclaimer_label` | `QLabel` | Disclaimer text at bottom |

---

## robot_action.py

**Overview:** Defines Qt worker threads for background processing: `AnalysisWorker` (image analysis via LLM) and `RobotActionWorker` (robot motion + TTS speech). Also defines the shared `WorkerSignals` class.

### Dependencies

| Import | Source |
|--------|--------|
| `os`, `yaml`, `asyncio`, `traceback` | stdlib |
| `QThread`, `pyqtSignal`, `QObject` | PyQt6.QtCore |
| `genai` | google-genai SDK |
| `OpenManipulatorXControl` | openmanipulator_x_control (local) |
| `tts_handler` | local module |
| `llm_analyzer` | local module |

### Module-Level Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PROJECT_ROOT` | *(computed)* | Project root directory (parent of `src/`) |
| `CONFIG_DIR` | `PROJECT_ROOT/config` | Configuration directory |
| `DATA_DIR` | `PROJECT_ROOT/data` | Data directory |
| `OMX_CONFIG_FILE` | `CONFIG_DIR/robot_hardware_config.yaml` | Robot hardware config path |
| `TEACH_CONFIG_FILE` | `CONFIG_DIR/teach_config.yaml` | Teach config path |

### Class: `WorkerSignals(QObject)`

Shared signal container for worker threads.

#### Signals

| Signal | Type | Description |
|--------|------|-------------|
| `analysis_complete` | `pyqtSignal(dict)` | Emitted when LLM image analysis finishes successfully. Payload is the analysis result dict. |
| `error_occurred` | `pyqtSignal(str)` | Emitted on any error. Payload is the error message string. |
| `action_speech_update` | `pyqtSignal(str)` | Emitted to append text to the robot speech area. |
| `action_status_update` | `pyqtSignal(str)` | Emitted to update the GUI status label. |
| `actions_finished` | `pyqtSignal(str)` | Emitted when all robot actions complete. Payload is a summary message. |

### Class: `AnalysisWorker(QThread)`

Runs LLM image analysis in a background thread.

#### Constructor

```python
AnalysisWorker(image_path, gemini_client, config_llm, config_robot, parent=None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `image_path` | `str` | Path to the image to analyze |
| `gemini_client` | `genai.Client` | Initialized Gemini client |
| `config_llm` | `dict` | LLM configuration dict |
| `config_robot` | `dict` | Robot configuration dict (legacy) |
| `parent` | `QObject` or `None` | Optional parent |

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `signals` | `WorkerSignals` | Class-level signal container |

#### Methods

| Method | Description |
|--------|-------------|
| `run()` | Calls `llm_analyzer.get_image_analysis_for_gui()` using `config_llm['available_robot_actions']`, `config_llm['vision_model_name']`, and `config_llm['llm_analyzer_gui_prompt_template']`. Emits `analysis_complete` or `error_occurred`. |

#### Configuration Keys Used (from `config_llm`)

- `available_robot_actions` -- `list[str]`
- `vision_model_name` -- `str`
- `llm_analyzer_gui_prompt_template` -- `str`

### Class: `RobotActionWorker(QThread)`

Runs the full robot action sequence (arm motion + TTS speech) in a background thread using asyncio.

#### Constructor

```python
RobotActionWorker(actions_to_perform, symptom_description, gemini_client, config_robot, config_llm, config_tts, pya_instance_ref, parent=None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `actions_to_perform` | `list[str]` | Action labels to execute |
| `symptom_description` | `str` | Text description of the symptom |
| `gemini_client` | `genai.Client` | Initialized Gemini client |
| `config_robot` | `dict` | Robot hardware configuration |
| `config_llm` | `dict` | LLM configuration |
| `config_tts` | `dict` | TTS configuration (contains `live_tts_model`, `live_tts_connect_config`, `robot_persona_prompt_tts`, `pyaudio_settings`) |
| `pya_instance_ref` | `pyaudio.PyAudio` or `None` | Shared PyAudio instance |
| `parent` | `QObject` or `None` | Optional parent |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `arm_controller` | `OpenManipulatorXControl` or `None` | Created during async execution |
| `taught_paths_data` | `dict` | Loaded from `taught_paths.yaml` |
| `run_settings` | `dict` | Loaded from `teach_config.yaml` `run_settings` section |
| `speaking_gesture_event` | `asyncio.Event` | Controls the speaking nod gesture loop |

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `_load_path_configs()` | -- | `None` | Loads `teach_config.yaml` and the taught paths YAML file. Populates `taught_paths_data` and `run_settings`. |
| `_speaking_gesture_loop()` | -- | `None` (async, runs forever) | Async coroutine that performs a nodding gesture while `speaking_gesture_event` is set. Alternates between the person pose and a raised pose. |
| `_execute_single_path_only(action_label)` | `action_label`: `str` | `bool` (async) | Executes a single motion path. Handles `"neutral"` (home), `"person"` (person pose), or named taught paths. |
| `_speak_with_gesture(core_intent, live_session, use_gesture=True)` | `core_intent`: `str`, `live_session`: Gemini live session, `use_gesture`: `bool` | `None` (async) | Calls TTS with optional concurrent arm gesture. Sets/clears `speaking_gesture_event`. |
| `_async_actions_and_speech_helper()` | -- | `None` (async) | Main async orchestration: initializes robot, opens Gemini live session, executes greeting/action/farewell sequence with speech. |
| `run()` | -- | `None` | Creates an asyncio event loop and runs `_async_actions_and_speech_helper()`. |

#### Configuration Keys Used (from `config_tts`)

- `live_tts_model` -- `str` -- Gemini model name for live TTS
- `live_tts_connect_config` -- `dict` -- Config dict passed to `gemini_client.aio.live.connect()`
- `robot_persona_prompt_tts` -- `str` -- (used indirectly via `tts_handler`)
- `pyaudio_settings` -- `dict` -- (used indirectly via `tts_handler`)

#### Configuration Keys Used (from `teach_config.yaml`)

- `run_settings.script_pacing_factor` -- `float` (default `0.6`)
- `run_settings.minimal_script_sleep_s` -- `float` (default `0.01`)

---

## llm_analyzer.py

**Overview:** Provides functions for analyzing images using the Google Gemini vision model. Extracts structured JSON (symptom description, insights, and action labels) from the LLM response.

### Dependencies

| Import | Source |
|--------|--------|
| `PIL.Image` | Pillow |
| `json`, `os`, `re`, `traceback` | stdlib |
| `genai` | google-genai SDK |

### Functions

#### `extract_json_from_llm_text(llm_text_response)`

Extracts a JSON object from an LLM text response.

| | Details |
|---|---|
| **Parameters** | `llm_text_response` (`str` or `None`): Raw text from LLM |
| **Returns** | `dict` or `None`: Parsed JSON object, or `None` if extraction/parsing fails |

Extraction strategy:
1. Searches for `` ```json { ... } ``` `` markdown code fence.
2. Falls back to direct `json.loads()` if the string starts with `{` and ends with `}`.

#### `get_image_analysis_for_gui(image_path, client_to_use, vision_model_name, prompt_template, available_actions_list)`

Sends an image to the Gemini vision model and parses the structured response.

| Parameter | Type | Description |
|-----------|------|-------------|
| `image_path` | `str` | Path to the image file |
| `client_to_use` | `genai.Client` | Initialized Gemini client |
| `vision_model_name` | `str` | Model name (e.g., `"gemini-2.0-flash"`) |
| `prompt_template` | `str` | Prompt string with `{action_list_placeholder}` placeholder |
| `available_actions_list` | `list[str]` | List of valid robot action labels |

| | Details |
|---|---|
| **Returns** | `dict` with keys: |

| Key | Type | Description |
|-----|------|-------------|
| `symptom_description` | `str` or `None` | Empathetic description of observed symptoms |
| `symptom_insights_text` | `str` or `None` | Bulleted list of symptom likelihoods |
| `action_labels` | `list[str]` | Validated action labels (filtered against `available_actions_list`) |
| `raw_llm_response` | `str` or `None` | Full text of the LLM response |
| `error` | `str` or `None` | Error message, or `None` on success |

---

## tts_handler.py

**Overview:** Manages text-to-speech via Google Gemini Live API and PyAudio. Provides PyAudio lifecycle management and an async function to stream generated speech audio with a jitter buffer.

### Dependencies

| Import | Source |
|--------|--------|
| `os`, `asyncio`, `traceback`, `io`, `time` | stdlib |
| `genai` | google-genai SDK |
| `pyaudio` | PyAudio |

### Module-Level Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PREBUFFER_DURATION_SECONDS` | `0.75` | Duration (seconds) of audio to buffer before playback begins |

### Module-Level State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `_pya_instance_tts` | `pyaudio.PyAudio` or `None` | Singleton PyAudio instance |
| `TTS_ENABLED_FLAG` | `bool` | Global flag indicating whether TTS is operational (default `True`) |

### Functions

#### `init_pyaudio_for_tts()`

Initializes the global PyAudio instance.

| | Details |
|---|---|
| **Parameters** | None |
| **Returns** | `pyaudio.PyAudio` or `None` -- The initialized instance, or `None` if TTS is disabled or initialization fails. |
| **Side Effects** | Sets `TTS_ENABLED_FLAG` to `False` on failure. |

#### `terminate_pyaudio_for_tts()`

Terminates the global PyAudio instance.

| | Details |
|---|---|
| **Parameters** | None |
| **Returns** | `None` |
| **Side Effects** | Sets `_pya_instance_tts` to `None`. |

Note: The function signature in the source accepts no arguments, but `robot_gui.py` calls it as `terminate_pyaudio_for_tts(self.pya_instance)`. The extra argument is silently ignored by the implementation since it only operates on the module-level `_pya_instance_tts`.

#### `set_tts_enabled_status(is_enabled)`

Sets the global TTS enabled flag.

| | Details |
|---|---|
| **Parameters** | `is_enabled` (`bool`): Whether to enable TTS |
| **Returns** | `None` |
| **Side Effects** | If disabling, also terminates the PyAudio instance. |

#### `speak_using_live_session(core_intent_for_robot_to_express, live_session, pya_instance_local, all_tts_configs, gui_speech_update_callback=None)` (async)

Streams speech audio from a Gemini Live session and plays it through PyAudio.

| Parameter | Type | Description |
|-----------|------|-------------|
| `core_intent_for_robot_to_express` | `str` | The core intent/instruction for the robot to express |
| `live_session` | Gemini live session object | Active live connection to Gemini |
| `pya_instance_local` | `pyaudio.PyAudio` | PyAudio instance for audio output |
| `all_tts_configs` | `dict` | TTS configuration dictionary |
| `gui_speech_update_callback` | `callable` or `None` | Optional callback `(str) -> None` to update the GUI speech area |

| | Details |
|---|---|
| **Returns** | `None` |

**Behavior:**
1. Prepends `robot_persona_prompt_tts` to the core intent.
2. Opens a PyAudio output stream using `pyaudio_settings`.
3. Sends the prompt to the live session.
4. Pre-buffers audio chunks until `PREBUFFER_DURATION_SECONDS` of audio is collected.
5. Plays all buffered and subsequent chunks through the stream.
6. Waits for the stream to drain (up to 10 seconds).
7. Sends a summary to the GUI callback.

### Configuration Keys Expected (from `all_tts_configs`)

| Key | Type | Description |
|-----|------|-------------|
| `robot_persona_prompt_tts` | `str` | Persona prompt prepended to all speech intents |
| `pyaudio_settings.format_int` | `int` | PyAudio format (default `pyaudio.paInt16` if value is `8`) |
| `pyaudio_settings.playback_rate` | `int` | Audio sample rate (Hz) |
| `pyaudio_settings.channels` | `int` | Number of audio channels |
| `pyaudio_settings.chunk_size` | `int` | PyAudio frames per buffer |

---

## openmanipulator_x_control.py

**Overview:** High-level orchestrator for the OpenMANIPULATOR-X robot arm. Composes `ArmController`, `GripperController`, and `DynamixelSDKInterface`. Provides connection management, initialization sequences, and taught-path playback.

### Dependencies

| Import | Source |
|--------|--------|
| `time`, `os` | stdlib |
| `yaml` | PyYAML |
| `PortHandler`, `PacketHandler`, `COMM_SUCCESS` | dynamixel_sdk |
| `DynamixelSDKInterface` | dxl_sdk_interface (local) |
| `ArmController` | arm_controller (local) |
| `GripperController` | gripper_controller (local) |

### Class: `OpenManipulatorXControl`

#### Constructor

```python
OpenManipulatorXControl(robot_hw_config_path="robot_hardware_config.yaml")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `robot_hw_config_path` | `str` | `"robot_hardware_config.yaml"` | Path to the robot hardware YAML config |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `is_initialized_properly` | `bool` | `True` if all components loaded from config without error |
| `is_connected` | `bool` | `True` if the serial port is open and communication established |
| `port_handler` | `PortHandler` or `None` | Dynamixel SDK port handler |
| `packet_handler` | `PacketHandler` or `None` | Dynamixel SDK packet handler |
| `dxl_io` | `DynamixelSDKInterface` or `None` | Low-level read/write interface |
| `arm` | `ArmController` or `None` | Arm joint controller |
| `gripper` | `GripperController` or `None` | Gripper motor controller |
| `hw_config` | `dict` or `None` | Full parsed hardware config |

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `connect()` | -- | `bool` | Opens the serial port and sets the baud rate. Returns `True` on success. |
| `disconnect()` | -- | `None` | Moves arm to rest pose, opens gripper, disables torque on all motors, and closes the serial port. |
| `initialize_robot(go_home=True, open_gripper_at_start=True)` | `go_home`: `bool`, `open_gripper_at_start`: `bool` | `bool` | Full initialization: connect, set default states, enable torque, optionally open gripper and go to home pose. |
| `go_to_home_pose(wait=True, segment_duration_s=1.5)` | `wait`: `bool`, `segment_duration_s`: `float` | `bool` | Delegates to `arm.go_to_home_pose()`. |
| `go_to_rest_pose(wait=True, segment_duration_s=2.0)` | `wait`: `bool`, `segment_duration_s`: `float` | `bool` | Delegates to `arm.go_to_rest_pose()`. |
| `go_to_person_pose(wait=True, segment_duration_s=1.5)` | `wait`: `bool`, `segment_duration_s`: `float` | `bool` | Delegates to `arm.go_to_person_pose()`. |
| `open_gripper(wait=True, desired_duration_s=None)` | `wait`: `bool`, `desired_duration_s`: `float` or `None` | `bool` | Delegates to `gripper.open()`. |
| `close_gripper(goal_current_limit=None, target_close_pos=None, wait_for_stop=True, desired_duration_s=None)` | See signature | `bool` | Delegates to `gripper.close()`. |
| `pick_object(goal_current_limit=None, grasp_wait_s=None, desired_duration_s=None)` | See signature | `bool` | Delegates to `gripper.pick_object()`. |
| `release_object(wait=True, desired_duration_s=None)` | `wait`: `bool`, `desired_duration_s`: `float` or `None` | `bool` | Delegates to `gripper.release_object()`. |
| `play_taught_path(path_waypoints_data, script_pacing_factor, minimal_script_sleep_s, path_name="<unnamed>")` | See below | `bool` | Plays a taught path: iterates waypoints, sets arm positions via GroupSyncWrite, sets gripper positions, paces with sleep. Returns `True` if all waypoints completed. |
| `get_arm_positions(use_cache=False)` | `use_cache`: `bool` | `list[int]` or `None` | Reads current arm joint positions. |
| `get_gripper_position(use_cache=False)` | `use_cache`: `bool` | `int` or `None` | Reads current gripper position. |
| `get_gripper_load_current()` | -- | `int` or `None` | Reads gripper present current (signed). |

**`play_taught_path` parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path_waypoints_data` | `list[dict]` | List of `{'timestamp': float, 'pose': [j1, j2, j3, j4, gripper]}` |
| `script_pacing_factor` | `float` | Multiplier for inter-waypoint sleep (e.g., `0.6`) |
| `minimal_script_sleep_s` | `float` | Minimum sleep between waypoints (e.g., `0.01`) |
| `path_name` | `str` | Display name for logging |

### Configuration Keys Expected (from `robot_hardware_config.yaml`)

| Section | Key(s) | Description |
|---------|--------|-------------|
| `connection_settings` | `device_name`, `baud_rate`, `protocol_version` | Serial port configuration |
| `dynamixel_common_constants` | Address/length constants for all register operations | Dynamixel control table constants |
| `arm_settings` | `joint_ids`, `home_pose`, `rest_pose`, `to_person_pose`, `default_profile_vel`, `default_profile_accel`, `default_operating_mode` | Arm motor configuration |
| `gripper_settings` | `id`, `open_pos`, `close_pos`, `default_grasp_current_limit`, `default_profile_vel`, `default_profile_accel`, `default_operating_mode` | Gripper motor configuration |
| `common_motion_parameters` | `default_joint_tolerance`, `default_wait_timeout_s`, `gripper_action_timeout_s`, `gripper_grasp_wait_s` | Shared motion parameters |

---

## arm_controller.py

**Overview:** Controls the four arm joints of the OpenMANIPULATOR-X. Manages operating mode, profile velocity/acceleration, torque, position reading, and synchronized multi-joint position commands via GroupSyncWrite.

### Dependencies

| Import | Source |
|--------|--------|
| `time` | stdlib |
| `GroupSyncWrite` | dynamixel_sdk |
| `DynamixelSDKInterface` | dxl_sdk_interface (local) |

### Class: `ArmController`

#### Class Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC` | `15.633` | Conversion factor from profile velocity register units to position units/sec |

#### Constructor

```python
ArmController(joint_ids_list, arm_config, common_motion_config, dxl_io, port_handler, packet_handler)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `joint_ids_list` | `list[int]` | Exactly 4 Dynamixel motor IDs for arm joints |
| `arm_config` | `dict` | `arm_settings` section from hardware config |
| `common_motion_config` | `dict` | `common_motion_parameters` section from hardware config |
| `dxl_io` | `DynamixelSDKInterface` | Low-level Dynamixel I/O interface |
| `port_handler` | `PortHandler` | Dynamixel SDK port handler |
| `packet_handler` | `PacketHandler` | Dynamixel SDK packet handler |

Raises `ValueError` if `joint_ids_list` length is not 4.

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `joint_ids` | `list[int]` | Motor IDs for the 4 arm joints |
| `config` | `dict` | Arm configuration |
| `common_cfg` | `dict` | Common motion parameters |
| `home_pose` | `list[int]` | Home position (4 values) |
| `rest_pose` | `list[int]` | Rest position (4 values) |
| `to_person_pose` | `list[int]` | Person-facing position (4 values, falls back to `home_pose`) |
| `default_profile_vel` | `int` | Default profile velocity register value |
| `default_profile_accel` | `int` | Default profile acceleration register value |
| `default_op_mode` | `int` | Default operating mode value |
| `default_tolerance` | `int` | Position tolerance for goal checking (default `30`) |
| `default_wait_timeout` | `float` | Timeout for wait operations (default `7.0` s) |
| `groupSyncWritePosition` | `GroupSyncWrite` | Sync writer for goal position |
| `current_torque_enabled_for_joints` | `list[bool]` | Torque state per joint |
| `current_positions_cache` | `list[int]` | Cached position values |

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `set_torque_all(enable, verbose=True)` | `enable`: `bool`, `verbose`: `bool` | `bool` | Enables or disables torque on all 4 joints. |
| `set_operating_mode_all(mode_val=None, force_torque_disable=True, verbose=True)` | `mode_val`: `int` or `None`, `force_torque_disable`: `bool`, `verbose`: `bool` | `bool` | Sets operating mode on all joints. Checks first joint to skip if already correct. Disables torque before changing mode. |
| `set_profile_velocity_all(velocity_val, verbose=False)` | `velocity_val`: `int`, `verbose`: `bool` | `bool` | Writes profile velocity to all joints. Clamps to minimum of 1. |
| `set_profile_acceleration_all(accel_val, verbose=False)` | `accel_val`: `int`, `verbose`: `bool` | `bool` | Writes profile acceleration to all joints. Clamps to minimum of 0. |
| `get_positions(use_cache=False, verbose_on_error=False)` | `use_cache`: `bool`, `verbose_on_error`: `bool` | `list[int]` or `None` | Reads present position from all joints. Updates cache. Returns `None` on any read failure. |
| `update_joint_positions_cache()` | -- | `bool` | Calls `get_positions(use_cache=False)`. Returns `True` if successful. |
| `_wait_for_goal_achievement(target_positions, tolerance=None, timeout_s=None)` | `target_positions`: `list[int]`, `tolerance`: `int` or `None`, `timeout_s`: `float` or `None` | `bool` | Polls joint positions until all are within tolerance of target, or timeout. |
| `move_to_pose(target_arm_joint_positions, desired_segment_duration_s=None, wait=False, timeout_s=None)` | See below | `bool` | Calculates per-joint profile velocities for the desired duration, commands positions via GroupSyncWrite, optionally waits for goal. |
| `go_to_home_pose(wait=True, segment_duration_s=1.5)` | `wait`: `bool`, `segment_duration_s`: `float` | `bool` | Moves to `home_pose`. |
| `go_to_rest_pose(wait=True, segment_duration_s=2.0)` | `wait`: `bool`, `segment_duration_s`: `float` | `bool` | Moves to `rest_pose`. |
| `go_to_person_pose(wait=True, segment_duration_s=2.0)` | `wait`: `bool`, `segment_duration_s`: `float` | `bool` | Moves to `to_person_pose`. |
| `setup_default_state(enable_torque_after=False, verbose=True)` | `enable_torque_after`: `bool`, `verbose`: `bool` | `bool` | Sets operating mode, profile acceleration, profile velocity to defaults. Optionally enables torque. |

**`move_to_pose` parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_arm_joint_positions` | `list[int]` | 4 target position values |
| `desired_segment_duration_s` | `float` or `None` | If provided, dynamically calculates per-joint profile velocity |
| `wait` | `bool` | Whether to block until target is reached |
| `timeout_s` | `float` or `None` | Wait timeout override |

---

## gripper_controller.py

**Overview:** Controls the single gripper motor of the OpenMANIPULATOR-X. Supports position control, current limiting, gentle grasp/release preparation, and object pick/release sequences.

### Dependencies

| Import | Source |
|--------|--------|
| `time` | stdlib |
| `DynamixelSDKInterface` | dxl_sdk_interface (local) |

### Class: `GripperController`

#### Class Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC` | `15.633` | Conversion factor from profile velocity register units to position units/sec |

#### Constructor

```python
GripperController(motor_id, gripper_config, common_motion_config, dxl_io)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `motor_id` | `int` | Dynamixel motor ID for the gripper |
| `gripper_config` | `dict` | `gripper_settings` section from hardware config |
| `common_motion_config` | `dict` | `common_motion_parameters` section from hardware config |
| `dxl_io` | `DynamixelSDKInterface` | Low-level Dynamixel I/O interface |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `motor_id` | `int` | Dynamixel motor ID |
| `config` | `dict` | Gripper configuration |
| `common_cfg` | `dict` | Common motion parameters |
| `open_pos` | `int` | Fully open position value |
| `close_pos` | `int` | Fully closed position value |
| `default_grasp_current` | `int` | Default current limit for grasping |
| `default_profile_vel` | `int` | Default profile velocity |
| `default_profile_accel` | `int` | Default profile acceleration |
| `default_op_mode` | `int` | Default operating mode |
| `action_timeout_s` | `float` | Timeout for gripper actions (default `3.0` s) |
| `grasp_wait_s` | `float` | Post-grasp hold delay (default `1.0` s) |
| `default_tolerance` | `int` | Position tolerance (default `30`) |
| `current_torque_enabled` | `bool` | Current torque state |
| `current_pos_cache` | `int` | Cached position value |

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `set_torque(enable, verbose=True)` | `enable`: `bool`, `verbose`: `bool` | `bool` | Enables or disables torque on the gripper motor. |
| `set_operating_mode(mode_val=None, force_torque_disable=True, verbose=True)` | `mode_val`: `int` or `None`, `force_torque_disable`: `bool`, `verbose`: `bool` | `bool` | Sets operating mode. Reads current mode first to skip if already set. Disables torque before changing. Verifies after write. |
| `set_goal_current(current_value, verbose=True)` | `current_value`: `int`, `verbose`: `bool` | `bool` | Writes the goal current register. Clamps to `[0, max_goal_current_val]`. |
| `_set_profile_velocity(velocity_val, verbose=False)` | `velocity_val`: `int`, `verbose`: `bool` | `bool` | Writes profile velocity. Clamps to `[1, max_profile_velocity_val]`. |
| `_set_profile_acceleration(accel_val, verbose=False)` | `accel_val`: `int`, `verbose`: `bool` | `bool` | Writes profile acceleration. Clamps to `[0, max_profile_acceleration_val]`. |
| `get_position(use_cache=False, verbose_on_error=False)` | `use_cache`: `bool`, `verbose_on_error`: `bool` | `int` or `None` | Reads the present position register. Updates cache on success. |
| `get_load_current(verbose_on_error=False)` | `verbose_on_error`: `bool` | `int` or `None` | Reads the present current register. Converts to signed 16-bit int. |
| `is_moving(verbose_on_error=False)` | `verbose_on_error`: `bool` | `bool` or `None` | Reads the moving status register. Returns `True` if moving, `None` on read error. |
| `set_target_position(target_pos, desired_duration_s=None, wait=True, timeout_s=None, current_limit_override=None)` | See below | `bool` | Sets goal position with optional duration-based velocity, current override, and blocking wait. |
| `open(wait=True, desired_duration_s=None)` | `wait`: `bool`, `desired_duration_s`: `float` or `None` | `bool` | Moves to `open_pos` with default grasp current. |
| `close(goal_current_limit=None, target_close_pos=None, wait_for_stop=True, desired_duration_s=None)` | See signature | `bool` | Moves to `close_pos` (or override) with specified current limit. |
| `pick_object(goal_current_limit=None, grasp_wait_s=None, desired_duration_s=None)` | See signature | `bool` | Closes gripper, waits for grasp hold delay, reads final load/position. |
| `release_object(wait=True, desired_duration_s=None)` | `wait`: `bool`, `desired_duration_s`: `float` or `None` | `bool` | Opens the gripper (delegates to `open()`). |
| `prepare_for_gentle_grasp(desired_duration_s=1.0, verbose=True)` | `desired_duration_s`: `float`, `verbose`: `bool` | `bool` | Sets reduced velocity, halved acceleration, and default current for a gentle grasp. |
| `prepare_for_gentle_release(desired_duration_s=1.5, verbose=True)` | `desired_duration_s`: `float`, `verbose`: `bool` | `bool` | Sets reduced velocity, halved acceleration, and default current for a gentle release. |
| `reset_to_default_profiles_and_current(verbose=True)` | `verbose`: `bool` | `bool` | Restores default profile velocity, acceleration, and goal current. |
| `setup_default_state(enable_torque_after=False, verbose=True)` | `enable_torque_after`: `bool`, `verbose`: `bool` | `bool` | Sets operating mode and resets profiles. Optionally enables torque. |

**`set_target_position` parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_pos` | `int` | Target position register value |
| `desired_duration_s` | `float` or `None` | If provided, calculates profile velocity dynamically |
| `wait` | `bool` | Block until motor stops or timeout |
| `timeout_s` | `float` or `None` | Wait timeout override |
| `current_limit_override` | `int` or `None` | If provided, sets goal current before moving |

---

## dxl_sdk_interface.py

**Overview:** Low-level abstraction over the Dynamixel SDK. Provides named-address read/write operations with automatic data length inference and communication error checking.

### Dependencies

| Import | Source |
|--------|--------|
| `time` | stdlib |
| `COMM_SUCCESS` | dynamixel_sdk |

### Class: `DynamixelSDKInterface`

#### Constructor

```python
DynamixelSDKInterface(port_handler, packet_handler, dxl_common_constants)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `port_handler` | `PortHandler` | Dynamixel SDK port handler instance |
| `packet_handler` | `PacketHandler` | Dynamixel SDK packet handler instance |
| `dxl_common_constants` | `dict` | Dictionary of address/length/constant mappings loaded from config |

#### Instance Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `port_handler` | `PortHandler` | Port handler reference |
| `packet_handler` | `PacketHandler` | Packet handler reference |
| `dxl_consts` | `dict` | Dynamixel constants dictionary |
| `COMM_SUCCESS_VAL` | `int` | Communication success value (from config or SDK default) |

#### Methods

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `_get_const(name, default=None)` | `name`: `str`, `default`: any | any | Retrieves a constant from `dxl_consts`. Prints a warning and returns `default` if not found. |
| `_check_comm_status(motor_id, comm_result, error_val, operation_name="Operation", verbose=True)` | `motor_id`: `int`, `comm_result`: `int`, `error_val`: `int`, `operation_name`: `str`, `verbose`: `bool` | `bool` | Validates communication result and Dynamixel packet error byte. Returns `True` only if both indicate success. |
| `read_data(motor_id, address_name, length_name=None, verbose_on_error=True)` | `motor_id`: `int`, `address_name`: `str`, `length_name`: `str` or `None`, `verbose_on_error`: `bool` | `int` or `None` | Reads 1, 2, or 4 bytes from the specified register address. Infers data length from naming conventions if `length_name` is not provided. Special case: returns `error_val` as data when reading `addr_hardware_error_status`. |
| `write_data(motor_id, address_name, value, length_name=None, verbose_on_error=True)` | `motor_id`: `int`, `address_name`: `str`, `value`: `int`, `length_name`: `str` or `None`, `verbose_on_error`: `bool` | `bool` | Writes 1, 2, or 4 bytes to the specified register address. Infers data length from naming conventions if `length_name` is not provided. |

#### Address Name Convention

The interface expects constants in `dxl_common_constants` following this pattern:
- `addr_<register_name>` -- Register address (e.g., `addr_goal_position`)
- `len_<register_name>` -- Data length in bytes (e.g., `len_goal_position`)
- `torque_enable_val`, `torque_disable_val` -- Enable/disable values
- `comm_success_val` -- Communication success code
- `max_profile_velocity_val`, `max_goal_current_val`, `max_profile_acceleration_val` -- Limit values

---

## teach_paths.py

**Overview:** Interactive script for recording robot arm motion paths by physically guiding the arm while torque is disabled. Supports gripper grasp/release sequences during recording. Uses the `keyboard` library for real-time key detection.

### Dependencies

| Import | Source |
|--------|--------|
| `time`, `os` | stdlib |
| `yaml` | PyYAML |
| `keyboard` | keyboard (third-party, requires sudo on Linux) |
| `OpenManipulatorXControl` | openmanipulator_x_control (local) |

### Module-Level Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PROJECT_ROOT` | *(computed)* | Project root directory (parent of `src/`) |
| `CONFIG_DIR` | `PROJECT_ROOT/config` | Configuration directory |
| `DATA_DIR` | `PROJECT_ROOT/data` | Data directory |
| `ROBOT_HW_CONFIG_FILE` | `CONFIG_DIR/robot_hardware_config.yaml` | Robot hardware config path |
| `TEACH_CONFIG_FILE` | `CONFIG_DIR/teach_config.yaml` | Teaching config path |
| `DEFAULT_TEACH_CONFIG_SETTINGS` | `dict` | Default teaching configuration (see below) |

**`DEFAULT_TEACH_CONFIG_SETTINGS` structure:**

```python
{
    'general_teaching': {
        'paths_output_file': "taught_paths.yaml",
        'recording_interval_s': 0.5,
        'arm_stabilize_duration_s': 0.2
    },
    'gripper_sequence_settings': {
        'grasp_prepare_duration_s': 0.8,
        'grasp_secure_delay_s': 1.0,
        'release_prepare_duration_s': 1.0,
        'release_max_wait_s': 3.0,
        'release_check_tolerance': 50,
        'release_complete_delay_s': 1.0
    }
}
```

### Functions

#### `load_teach_config()`

Loads teaching configuration from `teach_config.yaml`, merging with defaults.

| | Details |
|---|---|
| **Parameters** | None |
| **Returns** | `dict` -- Teaching configuration with `general_teaching` and `gripper_sequence_settings` sections. |
| **Side Effects** | Creates `teach_config.yaml` with defaults if it does not exist. |

#### `load_existing_paths(filepath)`

Loads previously taught paths from a YAML file.

| | Details |
|---|---|
| **Parameters** | `filepath` (`str`): Path to the YAML file |
| **Returns** | `dict` -- Dictionary of `{path_name: [waypoints]}`, or empty `{}` |

#### `save_paths(filepath, paths_dict)`

Saves taught paths to a YAML file.

| | Details |
|---|---|
| **Parameters** | `filepath` (`str`): Output path, `paths_dict` (`dict`): Paths to save |
| **Returns** | `None` |

#### `get_current_full_pose_with_timestamp(controller, path_start_time_monotonic)`

Reads the current full robot pose (4 arm joints + gripper) with a relative timestamp.

| Parameter | Type | Description |
|-----------|------|-------------|
| `controller` | `OpenManipulatorXControl` | Robot controller instance |
| `path_start_time_monotonic` | `float` | `time.monotonic()` value at path recording start |

| | Details |
|---|---|
| **Returns** | `dict` or `None` -- `{'timestamp': float, 'pose': [j1, j2, j3, j4, gripper]}` or `None` on read failure. |

#### `teach_single_path(controller, path_name, taught_paths_dict, config)`

Records a single motion path interactively.

| Parameter | Type | Description |
|-----------|------|-------------|
| `controller` | `OpenManipulatorXControl` | Connected robot controller |
| `path_name` | `str` | Name for the path |
| `taught_paths_dict` | `dict` | Dictionary to add the path to (mutated in place) |
| `config` | `dict` | Teaching configuration |

| | Details |
|---|---|
| **Returns** | `bool` -- `True` if recording completed successfully. |

**Key controls during recording:**
- **'p' key**: Initiates grasp or release (alternating)
- **'Enter' key**: Finishes recording

**Recording phases (state machine):**
- `idle` -- Normal recording, arm torque off
- `arm_stabilizing` -- Brief pause after 'p' press, arm torque re-enabled
- `gripper_commanding` -- Executing gentle grasp or release
- `waiting_gripper_move` -- Waiting for release to complete
- `post_action_delay` -- Holding after grasp/release before returning arm to limp

#### `main_teaching_interface()`

Interactive menu-driven interface for teaching multiple paths.

| | Details |
|---|---|
| **Parameters** | None |
| **Returns** | `None` |

**Menu options:**
- `t` -- Teach a new path
- `l` -- List existing paths
- `d` -- Delete a path
- `q` -- Quit

---

## run_taught_path.py

**Overview:** Standalone script for playing back previously taught motion paths. Loads paths from YAML, initializes the robot, and executes selected paths with configurable pacing.

### Dependencies

| Import | Source |
|--------|--------|
| `time`, `os` | stdlib |
| `yaml` | PyYAML |
| `OpenManipulatorXControl` | openmanipulator_x_control (local) |

### Module-Level Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PROJECT_ROOT` | *(computed)* | Project root directory (parent of `src/`) |
| `CONFIG_DIR` | `PROJECT_ROOT/config` | Configuration directory |
| `DATA_DIR` | `PROJECT_ROOT/data` | Data directory |
| `ROBOT_HW_CONFIG_FILE` | `CONFIG_DIR/robot_hardware_config.yaml` | Robot hardware config path |
| `TEACH_CONFIG_FILE` | `CONFIG_DIR/teach_config.yaml` | Teach config path |
| `DEFAULT_SCRIPT_PACING_FACTOR` | `0.5` | Default sleep multiplier between waypoints |
| `DEFAULT_MINIMAL_SCRIPT_SLEEP_S` | `0.01` | Default minimum sleep between waypoints |
| `DEFAULT_PATHS_OUTPUT_FILE` | `"taught_paths.yaml"` | Default taught paths filename (joined with `DATA_DIR`) |

### Functions

#### `load_run_configs()`

Loads run configuration from `teach_config.yaml`.

| | Details |
|---|---|
| **Parameters** | None |
| **Returns** | `dict` with keys `paths_output_file` (`str`), `script_pacing_factor` (`float`), `minimal_script_sleep_s` (`float`). |

#### `load_existing_paths(filepath)`

Loads taught paths from YAML.

| | Details |
|---|---|
| **Parameters** | `filepath` (`str`): Path to YAML file |
| **Returns** | `dict` or `None` -- Parsed paths dict, `None` if file not found, empty `{}` if empty. |

#### `execute_taught_path(controller, path_name, taught_paths_data, run_cfg)`

Executes a single taught path on the robot.

| Parameter | Type | Description |
|-----------|------|-------------|
| `controller` | `OpenManipulatorXControl` | Connected and initialized controller |
| `path_name` | `str` | Name of the path to execute |
| `taught_paths_data` | `dict` | Dictionary of all taught paths |
| `run_cfg` | `dict` | Run configuration (from `load_run_configs()`) |

| | Details |
|---|---|
| **Returns** | `bool` -- `True` if path executed successfully. |

**Execution sequence:**
1. Moves to home pose.
2. Waits 2 seconds.
3. Iterates through waypoints, commanding arm and gripper positions.
4. For non-final waypoints, sleeps for `segment_duration * script_pacing_factor` (minimum `minimal_script_sleep_s`).
5. For the final waypoint, waits for goal achievement.

### Entry Point (`__main__`)

Interactive loop that prompts for a path name and executes it. For each execution, creates a new `OpenManipulatorXControl` instance, initializes, runs the path, and disconnects.

---

## path_smoother.py

**Overview:** Offline utility for smoothing taught path data using a Savitzky-Golay filter. Reads raw waypoints, smooths the 4 arm joint trajectories, rescales timestamps, and writes the result to a new YAML file. Gripper values are preserved unmodified.

### Dependencies

| Import | Source |
|--------|--------|
| `os` | stdlib |
| `yaml` | PyYAML |
| `numpy` (`np`) | NumPy |
| `savgol_filter` | scipy.signal |

### Module-Level Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `PROJECT_ROOT` | *(computed)* | Project root directory (parent of `src/`) |
| `DATA_DIR` | `PROJECT_ROOT/data` | Data directory |
| `INPUT_FILE` | `DATA_DIR/taught_paths.yaml` | Input file with raw path data |
| `OUTPUT_FILE` | `DATA_DIR/smoothed_paths.yaml` | Output file for smoothed paths |
| `WINDOW_LENGTH` | `11` | Savitzky-Golay filter window length (must be odd) |
| `POLY_ORDER` | `3` | Savitzky-Golay polynomial order |
| `TIME_SCALING_FACTOR` | `1.2` | Multiplier applied to the total path duration |

### Functions

#### `smooth_path_data(path_data)`

Applies Savitzky-Golay smoothing to a single path's joint data.

| | Details |
|---|---|
| **Parameters** | `path_data` (`list[dict]`): List of waypoint dicts with `timestamp` and `pose` keys |
| **Returns** | `list[dict]` -- Smoothed path data with same structure. Returns input unchanged if path is shorter than `WINDOW_LENGTH`. |

**Processing:**
1. Extracts 4 arm joint columns and applies `savgol_filter` to each independently.
2. Preserves gripper values (index 4) as integers.
3. Rescales timestamps linearly to `original_duration * TIME_SCALING_FACTOR`.
4. Rounds timestamps to 4 decimal places and joint values to nearest integer.

#### `main()`

Main execution function. Loads all paths from `INPUT_FILE`, smooths each, and saves to `OUTPUT_FILE`.

| | Details |
|---|---|
| **Parameters** | None |
| **Returns** | `None` |

---

## Architecture Summary

```
main.py
  |-- loads configs (YAML) + env vars
  |-- creates genai.Client
  |-- creates QApplication + RobotAppGUI
        |
robot_gui.py (RobotAppGUI)
  |-- manages UI and user interaction
  |-- spawns AnalysisWorker / RobotActionWorker threads
        |
robot_action.py
  |-- AnalysisWorker --> llm_analyzer.py --> Gemini Vision API
  |-- RobotActionWorker --> openmanipulator_x_control.py (robot motion)
  |                     --> tts_handler.py (speech via Gemini Live API)
  |
openmanipulator_x_control.py (OpenManipulatorXControl)
  |-- arm_controller.py (ArmController) -- 4-joint arm control
  |-- gripper_controller.py (GripperController) -- gripper motor control
  |-- dxl_sdk_interface.py (DynamixelSDKInterface) -- low-level Dynamixel I/O
        |
        +-- dynamixel_sdk (PortHandler, PacketHandler, GroupSyncWrite)

Standalone utilities:
  teach_paths.py -- interactive path recording
  run_taught_path.py -- path playback
  path_smoother.py -- offline trajectory smoothing
```
