# teach_paths.py (Updated for new modular control structure)

import time
import yaml
import os
import keyboard # Ensure this library is installed: pip install keyboard
from openmanipulator_x_control import OpenManipulatorXControl # MODIFIED Import

# --- Project root and config/data paths ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
ROBOT_HW_CONFIG_FILE = os.path.join(CONFIG_DIR, "robot_hardware_config.yaml")
TEACH_CONFIG_FILE = os.path.join(CONFIG_DIR, "teach_config.yaml")

# Default values if teach_config.yaml is missing or incomplete
DEFAULT_TEACH_CONFIG_SETTINGS = {
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

# --- Helper Functions ---
def load_teach_config():
    config = {k: v.copy() for k, v in DEFAULT_TEACH_CONFIG_SETTINGS.items()} # Deep copy defaults
    if os.path.exists(TEACH_CONFIG_FILE):
        try:
            with open(TEACH_CONFIG_FILE, 'r') as f_cfg:
                loaded_config = yaml.safe_load(f_cfg)
                if loaded_config:
                    config['general_teaching'].update(loaded_config.get('general_teaching', {}))
                    config['gripper_sequence_settings'].update(loaded_config.get('gripper_sequence_settings', {}))
            print(f"INFO: Teaching configuration loaded from {TEACH_CONFIG_FILE}")
        except Exception as e:
            print(f"WARN: Could not load teaching config from {TEACH_CONFIG_FILE}, using defaults. Error: {e}")
    else:
        print(f"INFO: {TEACH_CONFIG_FILE} not found. Using default teaching configuration.")
        try:
            with open(TEACH_CONFIG_FILE, 'w') as f_default: # Save default config if not found
                yaml.dump(DEFAULT_TEACH_CONFIG_SETTINGS, f_default, sort_keys=False, default_flow_style=None)
            print(f"INFO: Saved default teaching configuration to {TEACH_CONFIG_FILE}")
        except Exception as e:
            print(f"WARN: Could not save default teaching configuration: {e}")
    return config

def load_existing_paths(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f: return yaml.safe_load(f) or {}
        except Exception as e: print(f"WARN: Could not load paths from {filepath}: {e}. Starting empty."); return {}
    return {}

def save_paths(filepath, paths_dict):
    try:
        with open(filepath, 'w') as f: yaml.dump(paths_dict, f, sort_keys=False, default_flow_style=None)
        print(f"INFO: Paths saved to {filepath}")
    except Exception as e: print(f"ERROR: Could not save paths to {filepath}: {e}")

def get_current_full_pose_with_timestamp(controller: OpenManipulatorXControl, path_start_time_monotonic):
    # MODIFIED: Use new controller methods
    arm_positions = controller.get_arm_positions(use_cache=False)
    gripper_position = controller.get_gripper_position(use_cache=False)
    
    current_monotonic_time = time.monotonic()
    relative_timestamp = round(current_monotonic_time - path_start_time_monotonic, 3)

    if arm_positions is not None and gripper_position is not None:
        return {'timestamp': relative_timestamp, 'pose': arm_positions + [gripper_position]}
    # print("WARN: get_current_full_pose_with_timestamp failed to read all positions.")
    return None

# --- Main Teaching Logic ---
def teach_single_path(controller: OpenManipulatorXControl, path_name, taught_paths_dict, config):
    gt_cfg = config['general_teaching']
    gs_cfg = config['gripper_sequence_settings']

    if not controller.is_connected: print("ERROR: Robot not connected."); return False

    print(f"\n--- Teaching Path: '{path_name}' ---")
    print("INFO: Moving to Home Position...")
    if not controller.go_to_home_pose(wait=True): print("ERROR: Failed to move to Home."); return False
    
    time.sleep(0.1)
    # MODIFIED: Update caches if necessary, or rely on use_cache=False in get_current_full_pose
    controller.arm.update_joint_positions_cache() # Arm controller has this
    controller.gripper.get_position(use_cache=False) # Gripper updates its cache on fresh read

    input(f"Press Enter to disable ARM torque and START recording path '{path_name}'...")
    
    print("INFO: Disabling ARM torque. Gripper torque remains ON. Recording starting...")
    # MODIFIED: Call arm controller directly for torque
    if not controller.arm.set_torque_all(enable=False, verbose=False):
        print("ERROR: Failed to disable arm torque.")
        controller.arm.set_torque_all(enable=True, verbose=False) # Try to re-enable arm torque
        return False
    
    current_path_waypoints = []
    is_recording = True
    is_grasping_next = True
    p_key_was_pressed_flag = False
    current_action_phase = "idle" 
    action_phase_start_time = 0
    
    path_start_time = time.monotonic()
    last_periodic_sample_time = path_start_time

    initial_waypoint = get_current_full_pose_with_timestamp(controller, path_start_time)
    if initial_waypoint:
        current_path_waypoints.append(initial_waypoint)
        print(f"  Recorded initial waypoint @ {initial_waypoint['timestamp']:.3f}s: {initial_waypoint['pose']}")
    else:
        print("ERROR: Could not get initial pose. Re-enabling arm torque.");
        controller.arm.set_torque_all(enable=True, verbose=False)
        return False

    print("INFO: ARM IS LIMP. GRIPPER HOLDING/READY. Move arm along desired path.")
    print(f"      Press 'p' to INITIATE {'GRASP' if is_grasping_next else 'RELEASE'} action.")
    print("      Press 'Enter' to FINISH recording this path.")

    while is_recording:
        time.sleep(0.01) 
        current_monotonic_time = time.monotonic()

        if current_action_phase == "idle" and keyboard.is_pressed('p'):
            if not p_key_was_pressed_flag:
                p_key_was_pressed_flag = True
                action_phase_start_time = current_monotonic_time 
                current_action_phase = "arm_stabilizing"
                print(f"\nINFO: 'p' key pressed. Next action: {'GRASP' if is_grasping_next else 'RELEASE'}. Stabilizing arm...")
                controller.arm.set_torque_all(enable=True, verbose=False) # MODIFIED
        elif not keyboard.is_pressed('p'):
            p_key_was_pressed_flag = False

        if current_action_phase == "arm_stabilizing":
            if current_monotonic_time - action_phase_start_time >= gt_cfg['arm_stabilize_duration_s']:
                print("  Arm stabilized. Recording pre-gripper command waypoint.")
                #waypoint_at_p_event = get_current_full_pose_with_timestamp(controller, path_start_time)
                #if waypoint_at_p_event: current_path_waypoints.append(waypoint_at_p_event)
                current_action_phase = "gripper_commanding"

        elif current_action_phase == "gripper_commanding":
            target_pos_val = 0
            if is_grasping_next:
                print(f"  Preparing and Initiating GENTLE GRASP (target: {controller.gripper.close_pos})...")
                controller.gripper.prepare_for_gentle_grasp(desired_duration_s=gs_cfg['grasp_prepare_duration_s'], verbose=True)
                target_pos_val = controller.gripper.close_pos
            else: # Releasing
                print(f"  Preparing and Initiating GENTLE RELEASE (target: {controller.gripper.open_pos})...")
                controller.gripper.prepare_for_gentle_release(desired_duration_s=gs_cfg['release_prepare_duration_s'], verbose=True)
                target_pos_val = controller.gripper.open_pos
            
            time.sleep(0.05) # Allow profiles to set
            # MODIFIED: Direct write using dxl_io for precise control after prepare_ methods
            controller.gripper.dxl_io.write_data(
                controller.gripper.motor_id, 
                "addr_goal_position", 
                target_pos_val, 
                length_name="len_goal_position", 
                verbose_on_error=True
            )
            
            if is_grasping_next: # This is for the action that was just initiated (grasp)
                print(f"  Grasp initiated. Arm STABLE. Recording continues during {gs_cfg['grasp_secure_delay_s']}s secure delay.")
                current_action_phase = "post_action_delay" 
            else: # This was a release action
                print(f"  Release initiated. Arm STABLE. Waiting for gripper to open (max {gs_cfg['release_max_wait_s']}s)...")
                current_action_phase = "waiting_gripper_move"
            
            action_phase_start_time = current_monotonic_time
            is_grasping_next = not is_grasping_next # Toggle for *next* 'p' press
            # DO NOT update last_periodic_sample_time here (based on previous fix)
        
        elif current_action_phase == "waiting_gripper_move": # Specific to release
            # MODIFIED: Use controller.gripper methods
            is_moving = controller.gripper.is_moving(verbose_on_error=False) 
            current_pos = controller.gripper.get_position(use_cache=False, verbose_on_error=False)
            opened_enough = current_pos is not None and \
                            abs(current_pos - controller.gripper.open_pos) <= gs_cfg['release_check_tolerance']

            if (is_moving is False and opened_enough) or \
               (is_moving is None and opened_enough and current_pos is not None): # if read error but pos is good
                print(f"  Gripper confirmed open at {current_pos}. Starting post-release delay.")
                current_action_phase = "post_action_delay"
                action_phase_start_time = current_monotonic_time 
            elif current_monotonic_time - action_phase_start_time > gs_cfg['release_max_wait_s']:
                print(f"  WARN: Timeout waiting for gripper to open (max {gs_cfg['release_max_wait_s']}s). Current pos: {current_pos}. Proceeding.")
                current_action_phase = "post_action_delay"
                action_phase_start_time = current_monotonic_time
        
        elif current_action_phase == "post_action_delay":
            # 'is_grasping_next' is already toggled, so 'not is_grasping_next' means previous action was grasp.
            delay_duration = gs_cfg['grasp_secure_delay_s'] if not is_grasping_next else gs_cfg['release_complete_delay_s']
            
            if current_monotonic_time - action_phase_start_time >= delay_duration:
                action_type_finished = "Grasp secure" if not is_grasping_next else "Release complete"
                print(f"  {action_type_finished} delay finished. Making ARM torque OFF.")
                controller.arm.set_torque_all(enable=False, verbose=False) # MODIFIED
                current_action_phase = "idle"
                print(f"      ARM IS LIMP. Continue guiding. Next action: {'GRASP' if is_grasping_next else 'RELEASE'}")
                # DO NOT update last_periodic_sample_time here
        
        if current_action_phase == "idle" and keyboard.is_pressed('enter'):
            print("\nINFO: 'Enter' key pressed. Finishing path recording...")
            is_recording = False
            start_debounce_time = time.monotonic()  # Statement 1: Assign on its own line
            # Statement 2: The while loop for debouncing
            while keyboard.is_pressed('enter') and \
                  (time.monotonic() - start_debounce_time < 0.5): # Condition part of the while
                time.sleep(0.01) # Body of the while loop, indented
            break

        if current_monotonic_time - last_periodic_sample_time >= gt_cfg['recording_interval_s']:
            waypoint_periodic = get_current_full_pose_with_timestamp(controller, path_start_time)
            if waypoint_periodic:
                current_path_waypoints.append(waypoint_periodic)
            last_periodic_sample_time = current_monotonic_time

    if current_action_phase != "idle":
        print(f"WARN: Recording ended while in action phase '{current_action_phase}'. Ensuring arm torque is OFF.")
        controller.arm.set_torque_all(enable=False, verbose=False) # MODIFIED

    final_waypoint = get_current_full_pose_with_timestamp(controller, path_start_time)
    if final_waypoint: current_path_waypoints.append(final_waypoint)

    print(f"INFO: Path '{path_name}' recording stopped. {len(current_path_waypoints)} waypoints captured.")
    print("INFO: Enabling torque for Arm and Gripper to hold final taught position.")
    # MODIFIED: Enable torque for both arm and gripper separately
    controller.arm.set_torque_all(enable=True, verbose=False)
    controller.gripper.set_torque(enable=True, verbose=False) 
    
    controller.gripper.reset_to_default_profiles_and_current(verbose=False) # MODIFIED

    taught_paths_dict[path_name] = current_path_waypoints
    return True

def main_teaching_interface():
    teach_cfg = load_teach_config()
    paths_output_file = os.path.join(DATA_DIR, teach_cfg['general_teaching']['paths_output_file'])

    print(f"--- OpenManipulator-X Path Teaching Script ---")
    print(f"INFO: Teaching config loaded from {TEACH_CONFIG_FILE if os.path.exists(TEACH_CONFIG_FILE) else 'Defaults'}.")
    print(f"INFO: Paths will be saved to/loaded from: {paths_output_file}")
    if os.name != 'nt': # Check if not Windows
        print("WARNING: This script uses 'keyboard'. On Linux/Mac, you might need to run with 'sudo'.")

    controller_instance = None # MODIFIED: Renamed for clarity
    try:
        # MODIFIED: Instantiation and config file name
        controller_instance = OpenManipulatorXControl(robot_hw_config_path=ROBOT_HW_CONFIG_FILE)
        if not controller_instance.is_initialized_properly:
            print("ERROR: Controller failed to initialize properly. Check robot_hardware_config.yaml and connections."); return
        
        if not controller_instance.initialize_robot():
            print("ERROR: Robot hardware initialization sequence failed."); return
        
        taught_paths = load_existing_paths(paths_output_file)
        if taught_paths: print("\nINFO: Existing paths:"); [print(f"  - {n} ({len(v)} wps)") for n,v in taught_paths.items()]
        else: print("\nINFO: No existing paths found or file is empty.")

        while True:
            print("\n------------------------------------------")
            print("Menu: 't'-teach new, 'l'-list, 'd'-delete, 'q'-quit")
            choice = input("Choice: ").strip().lower()

            if choice == 'q': break
            elif choice == 't':
                path_name = input("Enter new path name: ").strip()
                if not path_name: print("WARN: Path name cannot be empty."); continue
                if path_name in taught_paths:
                    overwrite = input(f"WARN: Path '{path_name}' already exists. Overwrite? (y/n): ").lower()
                    if overwrite != 'y': continue
                
                if teach_single_path(controller_instance, path_name, taught_paths, teach_cfg):
                    save_paths(paths_output_file, taught_paths)
            elif choice == 'l':
                if not taught_paths: print("INFO: No paths taught yet.")
                else: print("\nINFO: Available taught paths:"); [print(f"  - {p_name} ({len(p_data)} waypoints)") for p_name, p_data in taught_paths.items()]
            elif choice == 'd':
                if not taught_paths: print("INFO: No paths to delete."); continue
                del_name = input("Enter path name to delete: ").strip()
                if del_name in taught_paths:
                    confirm_del = input(f"Are you sure you want to delete path '{del_name}'? (y/n): ").lower()
                    if confirm_del == 'y':
                        del taught_paths[del_name]
                        print(f"INFO: Path '{del_name}' deleted.")
                        save_paths(paths_output_file, taught_paths)
                else: print(f"ERROR: Path '{del_name}' not found.")
            else: print("WARN: Invalid choice. Please try again.")
        
        print("INFO: Path teaching session finished.")

    except SystemExit as e: print(f"INFO: Exiting script ({e}).")
    except ImportError as e: print(f"IMPORT ERROR: {e}. Please ensure 'keyboard' and 'pyyaml' are installed, and controller modules are accessible.")
    except Exception as e:
        print(f"UNEXPECTED ERROR in teaching interface: {e}")
        import traceback; traceback.print_exc()
    finally:
        if controller_instance: # MODIFIED
            if hasattr(controller_instance, 'is_connected') and controller_instance.is_connected:
                print("INFO: Finalizing: Ensuring arm is at rest and disconnecting...")
                controller_instance.disconnect() 
            elif hasattr(controller_instance, 'is_initialized_properly') and not controller_instance.is_initialized_properly:
                 print("INFO: Controller was not properly initialized during the session.")
            # else: (No need for this else, covered by outer else)
        else: # Handles case where controller_instance might be None if __init__ failed badly
            print("INFO: Script finished or controller object was not created/connected.")

if __name__ == '__main__':
    main_teaching_interface()