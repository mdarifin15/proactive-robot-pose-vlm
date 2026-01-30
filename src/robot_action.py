# robot_action.py (Corrected for ValueError and includes all features)

import os
import yaml
import asyncio
import traceback
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from google import genai

from openmanipulator_x_control import OpenManipulatorXControl
import tts_handler
import llm_analyzer

# --- Project root and config/data paths ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OMX_CONFIG_FILE = os.path.join(CONFIG_DIR, "robot_hardware_config.yaml")
TEACH_CONFIG_FILE = os.path.join(CONFIG_DIR, "teach_config.yaml")


class WorkerSignals(QObject):
    # This class is unchanged
    analysis_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    action_speech_update = pyqtSignal(str)
    action_status_update = pyqtSignal(str)
    actions_finished = pyqtSignal(str)

class AnalysisWorker(QThread):
    # This class is unchanged
    signals = WorkerSignals()
    def __init__(self, image_path, gemini_client, config_llm, config_robot, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.gemini_client = gemini_client
        self.config_llm = config_llm
        self.config_robot = config_robot # Keep this for legacy available_actions list
        self.setObjectName("AnalysisWorkerThread")

    def run(self):
        try:
            # The available_robot_actions are in the LLM config as per our last fix
            actions_list = self.config_llm['available_robot_actions']
            analysis_results = llm_analyzer.get_image_analysis_for_gui(
                image_path=self.image_path,
                client_to_use=self.gemini_client,
                vision_model_name=self.config_llm['vision_model_name'],
                prompt_template=self.config_llm['llm_analyzer_gui_prompt_template'],
                available_actions_list=actions_list
            )
            self.signals.analysis_complete.emit(analysis_results)
        except Exception as e:
            err_msg = f"LLM Analysis Thread Error: {type(e).__name__} - {e}"
            traceback.print_exc()
            self.signals.error_occurred.emit(err_msg)


class RobotActionWorker(QThread):
    signals = WorkerSignals()

    def __init__(self, actions_to_perform, symptom_description, gemini_client, config_robot, config_llm, config_tts, pya_instance_ref, parent=None):
        super().__init__(parent)
        self.actions_to_perform = actions_to_perform
        self.symptom_description = symptom_description
        self.gemini_client = gemini_client
        self.config_robot = config_robot
        self.config_llm = config_llm
        self.config_tts = config_tts # This dict now correctly contains ALL TTS settings
        self.pya_instance = pya_instance_ref
        self.setObjectName("RobotActionWorkerThread")

        self.arm_controller = None
        self.taught_paths_data = {}
        self.run_settings = {}
        self.speaking_gesture_event = asyncio.Event()

        self._load_path_configs()

    def _load_path_configs(self):
        # This helper method is unchanged.
        try:
            paths_file = os.path.join(DATA_DIR, "taught_paths.yaml")
            with open(TEACH_CONFIG_FILE, 'r') as f:
                teach_cfg = yaml.safe_load(f)
                raw_paths_file = teach_cfg.get('general_teaching', {}).get('paths_output_file', "taught_paths.yaml")
                paths_file = os.path.join(DATA_DIR, raw_paths_file)
                self.run_settings = teach_cfg.get('run_settings', {})
            with open(paths_file, 'r') as f:
                self.taught_paths_data = yaml.safe_load(f) or {}
            if not self.taught_paths_data:
                self.signals.error_occurred.emit(f"Paths file '{paths_file}' is empty.")
        except FileNotFoundError as e:
            self.signals.error_occurred.emit(f"Config/Path file not found: {e.filename}")
        except Exception as e:
            self.signals.error_occurred.emit(f"Error loading new configs: {e}")

    async def _speaking_gesture_loop(self):
        # This method for the speaking gesture is unchanged.
        while True:
            await self.speaking_gesture_event.wait()
            person_pose = self.arm_controller.arm.to_person_pose
            if not person_pose:
                await asyncio.sleep(0.5)
                continue
            nod_up_pose = person_pose.copy()
            nod_up_pose[3] = nod_up_pose[3] - 150
            while self.speaking_gesture_event.is_set():
                await asyncio.to_thread(self.arm_controller.arm.move_to_pose, nod_up_pose, desired_segment_duration_s=0.1)
                if not self.speaking_gesture_event.is_set(): break
                await asyncio.sleep(0.1)
                await asyncio.to_thread(self.arm_controller.arm.move_to_pose, person_pose, desired_segment_duration_s=0.1)
                if not self.speaking_gesture_event.is_set(): break
                await asyncio.sleep(0.2)
            await asyncio.to_thread(self.arm_controller.arm.move_to_pose, person_pose, desired_segment_duration_s=0.5)

    async def _execute_single_path_only(self, action_label):
        # This method with the neutral->home fix is unchanged.
        self.signals.action_status_update.emit(f"Executing: {action_label}...")
        if action_label == "neutral":
            self.signals.action_status_update.emit("Moving to Home Pose...")
            return await asyncio.to_thread(self.arm_controller.go_to_home_pose, wait=True)
        elif action_label == "person":
            self.signals.action_status_update.emit("Moving to Person Pose...")
            return await asyncio.to_thread(self.arm_controller.go_to_person_pose, wait=True)
        if action_label not in self.taught_paths_data:
            self.signals.error_occurred.emit(f"Motion path '{action_label}' not found.")
            return False
        success = await asyncio.to_thread(
            self.arm_controller.play_taught_path,
            path_waypoints_data=self.taught_paths_data[action_label],
            script_pacing_factor=self.run_settings.get('script_pacing_factor', 0.6),
            minimal_script_sleep_s=self.run_settings.get('minimal_script_sleep_s', 0.01),
            path_name=action_label
        )
        return success

    async def _speak_with_gesture(self, core_intent, live_session, use_gesture=True):
        """A wrapper function to handle speech and optional concurrent gestures."""
        # This function encapsulates the set/clear logic you mentioned.
        if use_gesture:
            self.speaking_gesture_event.set()

        try:
            # Call the main tts_handler
            await tts_handler.speak_using_live_session(
                core_intent,
                live_session,
                self.pya_instance,
                self.config_tts,
                self.signals.action_speech_update.emit
            )
        finally:
            # Ensure the gesture is always stopped, even if speech fails
            if use_gesture:
                self.speaking_gesture_event.clear()

    async def _async_actions_and_speech_helper(self):
        speaking_gesture_task = None
        try:
            self.arm_controller = OpenManipulatorXControl(robot_hw_config_path=OMX_CONFIG_FILE)
            if not self.arm_controller.is_initialized_properly:
                self.signals.error_occurred.emit("Arm controller failed to initialize."); return
            if not await asyncio.to_thread(self.arm_controller.initialize_robot):
                self.signals.error_occurred.emit("Failed to connect to robot hardware."); return

            speaking_gesture_task = asyncio.create_task(self._speaking_gesture_loop())

            # --- THIS IS THE CORRECTED SECTION ---
            # All TTS settings are now correctly pulled from the self.config_tts dictionary,
            # which was loaded from your tts_config.yaml file.
            live_tts_model = self.config_tts.get('live_tts_model')
            live_connect_cfg = self.config_tts.get('live_tts_connect_config', {})
            # --- END OF CORRECTION ---

            gui_update_callback_for_tts = self.signals.action_speech_update.emit

            # Check if the model name was successfully loaded before proceeding
            if not live_tts_model:
                self.signals.error_occurred.emit("TTS Error: 'live_tts_model' key not found in tts_config.yaml")
                return

            async with self.gemini_client.aio.live.connect(model=live_tts_model, config=live_connect_cfg) as live_session:
                self.signals.action_speech_update.emit("Robot: Live speech session active.")
                                
                # Using your original, detailed conversational flow
                await self._execute_single_path_only("neutral")
                await self._execute_single_path_only("person")
                await asyncio.sleep(0.5)

                await self._speak_with_gesture("Core Intent: Greet the user, introduce yourself as RobotCare, convey readiness to assist", live_session)
                await self._speak_with_gesture(f"Core Intent: Briefly summarize your understanding of the situation of the user based on'{self.symptom_description}'", live_session)
                await asyncio.sleep(0.5)

                if not self.actions_to_perform:
                    await self._speak_with_gesture("Core Intent: Inform user no specific actions identified, but I am available.", live_session)
                else:
                    await self._speak_with_gesture("Core Intent: Inform user you've assessed the situation and are about to perform action for the user", live_session)
                    await asyncio.sleep(0.5)

                    for i, action_label in enumerate(self.actions_to_perform):
                        delivery_intent_announce = f"Core Intent: Announce the next action for taking the {action_label} and ask the user to please wait"
                        if action_label == "emergency call":
                            delivery_intent_announce = "Core Intent: You are indicating 'emergency call'. Politely ask the user to confirm or if they want another option"
                        
                        await self._speak_with_gesture(delivery_intent_announce, live_session)
                        await asyncio.sleep(0.5)
                        await self._execute_single_path_only(action_label)
                        await asyncio.sleep(1.0)

                        delivery_intent_offer = f"Core Intent: You have taken the {action_label} and give it to the user. Hopefully the user are going to be better after take the {action_label}"                        
                        await self._execute_single_path_only("person")
                        await asyncio.sleep(0.5)
                        await self._speak_with_gesture(delivery_intent_offer, live_session)
                        await asyncio.sleep(0.5)
                        
                        if i < len(self.actions_to_perform) - 1:
                            await self._speak_with_gesture("Core Intent: Say a brief transitional phrase, and let me think what I should do to help you ", live_session)
                            await asyncio.sleep(0.5)
                        
                await self._speak_with_gesture("Core Intent: Inform user if they need something and I will stay for you.", live_session)
                await asyncio.sleep(0.5)
                await self._execute_single_path_only("neutral")
                await asyncio.sleep(0.5)
                
        except Exception as e:
            self.signals.error_occurred.emit(f"Robot Action Error: {type(e).__name__} - {e}")
            traceback.print_exc()
        finally:
            #if speaking_gesture_task and not speaking_gesture_task.done():
            #    self.speaking_gesture_event.set()
            #    speaking_gesture_task.cancel()
            if self.arm_controller and self.arm_controller.is_connected:
                await asyncio.to_thread(self.arm_controller.disconnect)
            self.signals.actions_finished.emit("Robot action sequence has finished.")

    def run(self):
        # This method is unchanged.
        loop = None
        try:
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_actions_and_speech_helper())
        except Exception as e:
            self.signals.error_occurred.emit(f"Robot Action Thread Loop Error: {type(e).__name__} - {e}")
            traceback.print_exc()
        finally:
            if loop: loop.close()