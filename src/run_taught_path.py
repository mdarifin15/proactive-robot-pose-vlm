# run_taught_path.py (Corrected for new modular controllers, loop in script)

import time
import yaml
import os
from openmanipulator_x_control import OpenManipulatorXControl # MODIFIED Import

# --- Project root and config/data paths ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
ROBOT_HW_CONFIG_FILE = os.path.join(CONFIG_DIR, "robot_hardware_config.yaml")
TEACH_CONFIG_FILE = os.path.join(CONFIG_DIR, "teach_config.yaml")

DEFAULT_SCRIPT_PACING_FACTOR = 0.5
DEFAULT_MINIMAL_SCRIPT_SLEEP_S = 0.01
DEFAULT_PATHS_OUTPUT_FILE = "taught_paths.yaml"

# --- Helper Functions ---
def load_run_configs():
    config = {
        'paths_output_file': os.path.join(DATA_DIR, DEFAULT_PATHS_OUTPUT_FILE),
        'script_pacing_factor': DEFAULT_SCRIPT_PACING_FACTOR,
        'minimal_script_sleep_s': DEFAULT_MINIMAL_SCRIPT_SLEEP_S
    }
    if os.path.exists(TEACH_CONFIG_FILE):
        try:
            with open(TEACH_CONFIG_FILE, 'r') as f_cfg:
                teach_cfg_loaded = yaml.safe_load(f_cfg)
                if teach_cfg_loaded:
                    general_cfg = teach_cfg_loaded.get('general_teaching', {})
                    config['paths_output_file'] = os.path.join(DATA_DIR, general_cfg.get('paths_output_file', DEFAULT_PATHS_OUTPUT_FILE))
                    
                    run_settings_cfg = teach_cfg_loaded.get('run_settings', {})
                    config['script_pacing_factor'] = run_settings_cfg.get('script_pacing_factor', DEFAULT_SCRIPT_PACING_FACTOR)
                    config['minimal_script_sleep_s'] = run_settings_cfg.get('minimal_script_sleep_s', DEFAULT_MINIMAL_SCRIPT_SLEEP_S)
            print(f"INFO: Run configurations loaded from {TEACH_CONFIG_FILE}") # Corrected print
        except Exception as e:
            print(f"WARN: Could not load run configs from {TEACH_CONFIG_FILE}, using defaults. Error: {e}")
    else:
        print(f"INFO: {TEACH_CONFIG_FILE} not found. Using default run configurations.")
    return config

def load_existing_paths(filepath):
    if not os.path.exists(filepath):
        print(f"ERROR: Paths file '{filepath}' not found. Teach paths first."); return None
    try:
        with open(filepath, 'r') as f:
            paths_data = yaml.safe_load(f)
            if not paths_data: print(f"INFO: Paths file '{filepath}' is empty."); return {}
            return paths_data
    except Exception as e: print(f"ERROR: Could not load paths from {filepath}: {e}"); return None

# --- Path Execution Logic ---
def execute_taught_path(controller: OpenManipulatorXControl, path_name, taught_paths_data, run_cfg):
    script_pacing_factor = run_cfg['script_pacing_factor']
    minimal_script_sleep_s = run_cfg['minimal_script_sleep_s']

    if not controller.is_connected: print("ERROR: Robot not connected."); return False
    if path_name not in taught_paths_data: print(f"ERROR: Path '{path_name}' not found."); return False
    
    path_waypoints_data = taught_paths_data[path_name]
    if not path_waypoints_data or not isinstance(path_waypoints_data, list) or \
       not all(isinstance(wp, dict) and 'timestamp' in wp and 'pose' in wp and len(wp['pose']) == 5 for wp in path_waypoints_data):
        print(f"ERROR: Path '{path_name}' is empty or malformed (expected 5 values in pose)."); return False

    print(f"\n--- Executing Path: '{path_name}' (Pacing Factor: {script_pacing_factor}) ---")
    print("INFO: Moving to Home Position first...")
    if not controller.go_to_home_pose(wait=True, segment_duration_s=1.5): 
        print("ERROR: Failed to move to Home."); return False
    print("INFO: At Home. Holding for 2 seconds...")
    time.sleep(2.0)

    # Verify arm operating mode
    if controller.arm: # Check if arm object exists
        first_arm_joint_id = controller.arm.joint_ids[0]
        # ArmController's setup_default_state should have set the mode. We can check it here.
        # Note: ArmController itself doesn't store active_operating_modes dict in my generated code.
        # The check is more effectively done by ensuring setup_default_state was successful in initialize_robot.
        # For simplicity, we assume initialize_robot set it correctly.
        # If a hard check is needed here, ArmController would need to store/expose its current mode.
        # Let's rely on OpenManipulatorXControl.play_taught_path's internal mode re-assertion logic
        # or assume initialize_robot was sufficient.
        print(f"INFO: Arm operating mode should be {controller.arm.default_op_mode} (Position Control).")
    else:
        print("ERROR: Arm controller not available."); return False


    # Update current positions before starting path
    if controller.arm: controller.arm.update_joint_positions_cache()
    if controller.gripper: initial_gripper_pos_read = controller.gripper.get_position(use_cache=False)
    else: print("ERROR: Gripper controller not available."); return False
    
    last_commanded_gripper_pos = initial_gripper_pos_read
    if last_commanded_gripper_pos is None:
        last_commanded_gripper_pos = controller.gripper.open_pos # Assume open if read failed
        print("WARN: Could not read initial gripper pos, assuming open state.")

    print(f"INFO: Starting path execution ({len(path_waypoints_data)} waypoints).")
    
    previous_waypoint_taught_timestamp = 0.0
    total_taught_duration = path_waypoints_data[-1]['timestamp'] if path_waypoints_data else 0
    playback_actual_start_time = time.monotonic()

    for i, waypoint_entry in enumerate(path_waypoints_data):
        target_full_pose = waypoint_entry['pose']
        current_waypoint_taught_timestamp = waypoint_entry['timestamp']
        
        target_arm_pose = target_full_pose[0:4]
        target_gripper_pos = int(target_full_pose[4]) # Ensure int for gripper
        
        segment_duration_s = current_waypoint_taught_timestamp - previous_waypoint_taught_timestamp
        segment_duration_s = max(0.02, segment_duration_s)
        
        is_last_waypoint = (i == len(path_waypoints_data) - 1)
        wait_for_this_segment_physically = is_last_waypoint
        
        # --- Command Arm ---
        arm_timeout = (segment_duration_s + 1.0) if is_last_waypoint else (segment_duration_s + 0.5)
        arm_timeout = max(arm_timeout, 0.7)

        # MODIFIED: Call controller.arm method
        arm_success = controller.arm.move_to_pose(
            target_arm_pose,
            desired_segment_duration_s=segment_duration_s,
            wait=wait_for_this_segment_physically,
            timeout_s=arm_timeout if is_last_waypoint else None
        )
        if not arm_success:
            print(f"ERROR: Failed to command or reach ARM waypoint {i+1}. Aborting path.")
            controller.go_to_rest_pose(wait=True); return False # Use orchestrator's method

        # --- Command Gripper ---
        gripper_desired_duration = max(0.1, segment_duration_s * 0.5)
        gripper_desired_duration = min(gripper_desired_duration, 1.0) # Cap gripper move time

        if target_gripper_pos != last_commanded_gripper_pos or is_last_waypoint:
            gripper_timeout = (gripper_desired_duration + 0.7) if is_last_waypoint else (gripper_desired_duration + 0.5)
            gripper_timeout = max(gripper_timeout, 0.5)

            # MODIFIED: Call controller.gripper method
            gripper_success = controller.gripper.set_target_position(
                target_gripper_pos,
                desired_duration_s=gripper_desired_duration,
                wait=wait_for_this_segment_physically,
                timeout_s=gripper_timeout if is_last_waypoint else None
            )
            if not gripper_success:
                print(f"WARN: Failed to command or reach GRIPPER state for waypoint {i+1}.")
                if is_last_waypoint: pass
        
        if not wait_for_this_segment_physically:
            script_sleep_duration = segment_duration_s * script_pacing_factor
            script_sleep_duration = max(script_sleep_duration, minimal_script_sleep_s)
            time.sleep(script_sleep_duration)
            
        previous_waypoint_taught_timestamp = current_waypoint_taught_timestamp
        last_commanded_gripper_pos = target_gripper_pos

    playback_actual_duration = time.monotonic() - playback_actual_start_time
    print(f"INFO: Path '{path_name}' command sequence complete.")
    print(f"      Taught path duration: ~{total_taught_duration:.2f}s")
    print(f"      Actual playback command loop duration: ~{playback_actual_duration:.2f}s") 
    
    print(f"INFO: Holding final position.")
    return True

# --- Main Script Logic ---
if __name__ == '__main__':
    run_cfg_params = load_run_configs()
    paths_file_to_load = run_cfg_params['paths_output_file']

    print(f"--- OpenManipulator-X Path Execution Script (Direct Loop) ---") # Updated title
    print(f"INFO: Loading paths from: {paths_file_to_load}")
    print(f"INFO: Script pacing factor for segment sleep: {run_cfg_params['script_pacing_factor']}")

    taught_paths_loaded = load_existing_paths(paths_file_to_load)
    if taught_paths_loaded is None or not taught_paths_loaded:
        print("INFO: No paths available or file empty. Exiting."); exit()

    print("\nAvailable taught paths:")
    for name, wps_list in taught_paths_loaded.items(): print(f"  - {name} ({len(wps_list)} waypoints)")
    
    while True:
        path_to_run_name = input("\nEnter path name to execute (or 'q' to quit): ").strip()
        if path_to_run_name.lower() == 'q': break
        if path_to_run_name in taught_paths_loaded:
            robot_controller_instance = None
            try:
                # MODIFIED: Instantiation and config file name
                robot_controller_instance = OpenManipulatorXControl(robot_hw_config_path=ROBOT_HW_CONFIG_FILE) 
                if not robot_controller_instance.is_initialized_properly:
                    print("ERROR: Controller failed to initialize properly."); continue
                
                if not robot_controller_instance.initialize_robot():
                    print("ERROR: Robot hardware initialization sequence failed."); continue
                
                # Call the local execute_taught_path function
                execute_taught_path(robot_controller_instance, path_to_run_name, taught_paths_loaded, run_cfg_params)

            except SystemExit: print("Exiting due to SystemExit."); break
            except ImportError as e: print(f"IMPORT ERROR: {e}."); break
            except Exception as e:
                print(f"UNEXPECTED ERROR during path execution: {e}")
                import traceback; traceback.print_exc()
            finally:
                if robot_controller_instance and hasattr(robot_controller_instance, 'is_connected') and robot_controller_instance.is_connected:
                    print("INFO: Task/Error finished. Disconnecting...") # Simplified message
                    robot_controller_instance.disconnect()
                elif robot_controller_instance and hasattr(robot_controller_instance, 'is_initialized_properly') and not robot_controller_instance.is_initialized_properly:
                     print("INFO: Controller object existed but was not properly initialized.")
                print("-" * 40)
        else:
            print(f"ERROR: Path '{path_to_run_name}' not found.")
    print("INFO: Path execution script finished.")