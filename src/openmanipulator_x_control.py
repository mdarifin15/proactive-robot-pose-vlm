# openmanipulator_x_control.py

import time
import yaml
import os
from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
from dxl_sdk_interface import DynamixelSDKInterface
from arm_controller import ArmController
from gripper_controller import GripperController

class OpenManipulatorXControl:
    def __init__(self, robot_hw_config_path="robot_hardware_config.yaml"):
        self.is_initialized_properly = False
        self.is_connected = False
        self.port_handler = None
        self.packet_handler = None
        self.dxl_io = None
        self.arm = None
        self.gripper = None
        self.hw_config = None # Store loaded hw_config

        try:
            if not os.path.exists(robot_hw_config_path):
                raise FileNotFoundError(f"Robot hardware config file not found: {robot_hw_config_path}")
            with open(robot_hw_config_path, 'r') as f:
                self.hw_config = yaml.safe_load(f)

            conn_cfg = self.hw_config.get('connection_settings')
            dxl_common_consts = self.hw_config.get('dynamixel_common_constants')
            arm_cfg = self.hw_config.get('arm_settings')
            gripper_cfg = self.hw_config.get('gripper_settings')
            common_motion_cfg = self.hw_config.get('common_motion_parameters')

            if not all([conn_cfg, dxl_common_consts, arm_cfg, gripper_cfg, common_motion_cfg]):
                raise ValueError("One or more key configuration sections are missing in robot_hardware_config.yaml")

            self.port_handler = PortHandler(conn_cfg['device_name'])
            self.packet_handler = PacketHandler(float(conn_cfg.get('protocol_version', 2.0)))

            self.dxl_io = DynamixelSDKInterface(self.port_handler, self.packet_handler, dxl_common_consts)

            self.arm = ArmController(
                joint_ids_list=arm_cfg['joint_ids'],
                arm_config=arm_cfg,
                common_motion_config=common_motion_cfg,
                dxl_io=self.dxl_io,
                port_handler=self.port_handler,
                packet_handler=self.packet_handler
            )

            self.gripper = GripperController(
                motor_id=gripper_cfg['id'],
                gripper_config=gripper_cfg,
                common_motion_config=common_motion_cfg,
                dxl_io=self.dxl_io
            )
            self.is_initialized_properly = True
            print("INFO (OpenManipulatorXControl): Successfully initialized components from config.")

        except Exception as e:
            print(f"ERROR (OpenManipulatorXControl __init__): Failed to initialize - {e}")
            import traceback; traceback.print_exc()
            self.is_initialized_properly = False

    def connect(self):
        if not self.is_initialized_properly:
            print("ERROR (OMXC connect): Controller not properly initialized from config."); return False
        if self.is_connected:
            print("INFO (OMXC connect): Already connected."); return True
        
        if not self.port_handler.openPort():
            print(f"ERROR (OMXC connect): Failed to open port {self.port_handler.port_name}"); return False
        # print(f"INFO (OMXC connect): Port opened successfully: {self.port_handler.port_name}") # Less verbose

        baud_rate = int(self.hw_config['connection_settings']['baud_rate'])
        if not self.port_handler.setBaudRate(baud_rate):
            print(f"ERROR (OMXC connect): Failed to set baud rate to {baud_rate}");
            self.port_handler.closePort(); return False
        # print(f"INFO (OMXC connect): Baud rate set to {baud_rate}.")
        
        self.is_connected = True
        return True

    def disconnect(self):
        if not self.is_connected:
            if self.is_initialized_properly: # Check if port_handler might exist
                 print("INFO (OMXC disconnect): Not connected, but was initialized. Ensuring port is closed if open.")
                 if self.port_handler and self.port_handler.is_open:
                     self.port_handler.closePort()
            else:
                print("INFO (OMXC disconnect): Not connected and not properly initialized.")
            return

        print("INFO (OMXC disconnect): Disconnecting robot...")
        if self.arm and any(getattr(self.arm, 'current_torque_enabled_for_joints', [False])):
            print("INFO (OMXC disconnect): Arm torque may be ON, moving to Rest Pose...")
            self.arm.go_to_rest_pose(wait=True, segment_duration_s=1.5) 
        
        if self.gripper and getattr(self.gripper, 'current_torque_enabled', False):
             print("INFO (OMXC disconnect): Gripper torque may be ON, attempting to open gripper...")
             self.gripper.open(wait=True, desired_duration_s=0.5)

        if self.arm: self.arm.set_torque_all(False, verbose=False)
        if self.gripper: self.gripper.set_torque(False, verbose=False)
        
        if self.port_handler and self.port_handler.is_open:
            self.port_handler.closePort()
            print("INFO (OMXC disconnect): Port closed.")
        else:
            print("INFO (OMXC disconnect): Port was already closed or not opened.")
            
        self.is_connected = False
        print("INFO (OMXC disconnect): Robot disconnected sequence complete.")

    def initialize_robot(self, go_home=True, open_gripper_at_start=True):
        if not self.is_initialized_properly:
            print("ERROR (OMXC initialize_robot): Controller not initialized from config."); return False
        if not self.connect():
            print("ERROR (OMXC initialize_robot): Failed to connect to robot."); return False

        print("INFO (OMXC initialize_robot): Setting up default state for Arm...")
        if not self.arm.setup_default_state(enable_torque_after=True, verbose=True):
            print("ERROR (OMXC initialize_robot): Failed to setup Arm default state."); self.disconnect(); return False
        
        print("INFO (OMXC initialize_robot): Setting up default state for Gripper...")
        if not self.gripper.setup_default_state(enable_torque_after=True, verbose=True):
            print("ERROR (OMXC initialize_robot): Failed to setup Gripper default state."); self.disconnect(); return False
        
        time.sleep(0.2) 

        if open_gripper_at_start:
            print("INFO (OMXC initialize_robot): Opening gripper...")
            if not self.gripper.open(wait=True, desired_duration_s=1.0):
                print("WARN (OMXC initialize_robot): Gripper failed to open to initial position.");
        
        if go_home:
            print("INFO (OMXC initialize_robot): Moving arm to Home Pose...")
            if not self.arm.go_to_home_pose(wait=True, segment_duration_s=2.0):
                print("ERROR (OMXC initialize_robot): Failed to reach Home Pose with arm.");
                print("INFO (OMXC initialize_robot): Attempting to move to Rest Pose instead...");
                self.arm.go_to_rest_pose(wait=False, segment_duration_s=1.0) 
                self.disconnect(); return False 
        
        self.arm.update_joint_positions_cache()
        self.gripper.get_position(use_cache=False) 

        print("INFO (OMXC initialize_robot): Robot initialized successfully.")
        return True

    def go_to_home_pose(self, wait=True, segment_duration_s=1.5):
        if not self.is_connected or not self.arm: 
            print("ERROR (go_to_home_pose): Not connected or arm not initialized."); return False
        return self.arm.go_to_home_pose(wait, segment_duration_s)

    def go_to_rest_pose(self, wait=True, segment_duration_s=2.0):
        if not self.is_connected or not self.arm: 
            print("ERROR (go_to_rest_pose): Not connected or arm not initialized."); return False
        return self.arm.go_to_rest_pose(wait, segment_duration_s)
    
    def go_to_person_pose(self, wait=True, segment_duration_s=1.5):
        if not self.is_connected or not self.arm:
            print("ERROR (go_to_person_pose): Not connected or arm not initialized."); return False
        return self.arm.go_to_person_pose(wait, segment_duration_s)

    def open_gripper(self, wait=True, desired_duration_s=None):
        if not self.is_connected or not self.gripper: 
            print("ERROR (open_gripper): Not connected or gripper not initialized."); return False
        return self.gripper.open(wait, desired_duration_s)

    def close_gripper(self, goal_current_limit=None, target_close_pos=None, wait_for_stop=True, desired_duration_s=None):
        if not self.is_connected or not self.gripper: 
            print("ERROR (close_gripper): Not connected or gripper not initialized."); return False
        return self.gripper.close(goal_current_limit, target_close_pos, wait_for_stop, desired_duration_s)

    def pick_object(self, goal_current_limit=None, grasp_wait_s=None, desired_duration_s=None):
        if not self.is_connected or not self.gripper: 
            print("ERROR (pick_object): Not connected or gripper not initialized."); return False
        return self.gripper.pick_object(goal_current_limit, grasp_wait_s, desired_duration_s)

    def release_object(self, wait=True, desired_duration_s=None):
        if not self.is_connected or not self.gripper: 
            print("ERROR (release_object): Not connected or gripper not initialized."); return False
        return self.gripper.release_object(wait, desired_duration_s)

    def play_taught_path(self, path_waypoints_data, script_pacing_factor, minimal_script_sleep_s, path_name="<unnamed>"):
        if not self.is_connected or not self.arm or not self.gripper:
            print(f"ERROR (play_taught_path): Robot not connected for path '{path_name}'.")
            return False
        if not path_waypoints_data or not isinstance(path_waypoints_data, list) or \
           not all(isinstance(wp, dict) and 'timestamp' in wp and 'pose' in wp and len(wp['pose']) == 5 for wp in path_waypoints_data):
            print(f"ERROR (play_taught_path): Path '{path_name}' data is empty or malformed.")
            return False

        print(f"INFO (play_taught_path): Starting path '{path_name}' ({len(path_waypoints_data)} waypoints).")

        # As in your test script, we assume the robot is already at Home
        # and operating modes are correct from initialize_robot()

        self.arm.update_joint_positions_cache()
        last_commanded_gripper_pos = self.gripper.get_position(use_cache=True)
        if last_commanded_gripper_pos is None:
            last_commanded_gripper_pos = self.gripper.open_pos
            print("WARN: Could not read initial gripper pos, assuming open state.")

        previous_waypoint_taught_timestamp = 0.0
        for i, waypoint_entry in enumerate(path_waypoints_data):
            target_full_pose = waypoint_entry['pose']
            current_waypoint_taught_timestamp = waypoint_entry['timestamp']

            target_arm_pose = target_full_pose[0:4]
            target_gripper_pos = int(target_full_pose[4])

            segment_duration_s = current_waypoint_taught_timestamp - previous_waypoint_taught_timestamp
            segment_duration_s = max(0.02, segment_duration_s)

            is_last_waypoint = (i == len(path_waypoints_data) - 1)
            wait_for_this_segment_physically = is_last_waypoint

            arm_timeout = (segment_duration_s + 1.0) if is_last_waypoint else (segment_duration_s + 0.5)
            arm_timeout = max(arm_timeout, 0.7)

            arm_success = self.arm.move_to_pose(
                target_arm_pose,
                desired_segment_duration_s=segment_duration_s,
                wait=wait_for_this_segment_physically,
                timeout_s=arm_timeout if is_last_waypoint else None
            )
            if not arm_success:
                print(f"ERROR: Failed ARM waypoint {i+1} for path '{path_name}'.")
                self.go_to_rest_pose(wait=True); return False

            gripper_desired_duration = max(0.1, segment_duration_s * 0.5)
            gripper_desired_duration = min(gripper_desired_duration, 1.0)

            if target_gripper_pos != last_commanded_gripper_pos or is_last_waypoint:
                gripper_timeout = (gripper_desired_duration + 0.7) if is_last_waypoint else (gripper_desired_duration + 0.5)
                gripper_timeout = max(gripper_timeout, 0.5)
                gripper_success = self.gripper.set_target_position(
                    target_gripper_pos,
                    desired_duration_s=gripper_desired_duration,
                    wait=wait_for_this_segment_physically,
                    timeout_s=gripper_timeout if is_last_waypoint else None
                )
                if not gripper_success and is_last_waypoint:
                    print(f"WARN: Failed GRIPPER state for final waypoint of path '{path_name}'.")

            if not wait_for_this_segment_physically:
                script_sleep_duration = segment_duration_s * script_pacing_factor
                script_sleep_duration = max(script_sleep_duration, minimal_script_sleep_s)
                time.sleep(script_sleep_duration)

            previous_waypoint_taught_timestamp = current_waypoint_taught_timestamp
            last_commanded_gripper_pos = target_gripper_pos

        print(f"INFO (play_taught_path): Finished path '{path_name}'. Holding final position.")
        return True
     
    def get_arm_positions(self, use_cache=False):
        if not self.is_connected or not self.arm: return None
        return self.arm.get_positions(use_cache)

    def get_gripper_position(self, use_cache=False):
        if not self.is_connected or not self.gripper: return None
        return self.gripper.get_position(use_cache)

    def get_gripper_load_current(self):
        if not self.is_connected or not self.gripper: return None
        return self.gripper.get_load_current()

# --- Main Test Program ---
if __name__ == '__main__':
    print("--- Starting OpenManipulatorXControl Standalone Test ---")
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
    ROBOT_HW_CONFIG = os.path.join(CONFIG_DIR, "robot_hardware_config.yaml")
    TEACH_CFG_FOR_RUN_PARAMS = os.path.join(CONFIG_DIR, "teach_config.yaml")

    # Load run parameters for play_taught_path
    script_pacing = 0.7 # Default if teach_config.yaml not found or parsable
    min_sleep = 0.01    # Default

    if os.path.exists(TEACH_CFG_FOR_RUN_PARAMS):
        try:
            with open(TEACH_CFG_FOR_RUN_PARAMS, 'r') as f_cfg:
                teach_cfg_loaded = yaml.safe_load(f_cfg)
                if teach_cfg_loaded and 'run_settings' in teach_cfg_loaded:
                    script_pacing = teach_cfg_loaded['run_settings'].get('script_pacing_factor', script_pacing)
                    min_sleep = teach_cfg_loaded['run_settings'].get('minimal_script_sleep_s', min_sleep)
                    print(f"INFO (Test): Loaded pacing factor: {script_pacing}, min_sleep: {min_sleep} from {TEACH_CFG_FOR_RUN_PARAMS}")
        except Exception as e:
            print(f"WARN (Test): Could not load pacing from {TEACH_CFG_FOR_RUN_PARAMS}, using defaults. Error: {e}")


    robot_controller = OpenManipulatorXControl(robot_hw_config_path=ROBOT_HW_CONFIG)

    if not robot_controller.is_initialized_properly:
        print("FATAL (Test): Robot controller failed to initialize from config. Exiting.")
        exit()

    try:
        print("\nAttempting to initialize robot (connect, setup, home, gripper open)...")
        if not robot_controller.initialize_robot(): # This already moves to home
            print("FATAL (Test): Full robot initialization sequence failed. Exiting.")
            exit()
        
        print("\nRobot initialized. Current state (at Home):")
        print(f"  Arm positions: {robot_controller.get_arm_positions()}")
        print(f"  Gripper position: {robot_controller.get_gripper_position()}")
        time.sleep(1)

        # --- Test Basic Arm Movements ---
        print("\nTesting arm movement: Going to Person Pose...") # *** MODIFIED TEST ***
        if robot_controller.go_to_person_pose(wait=True, segment_duration_s=2.0):
            print(f"  Arm at Person Pose: {robot_controller.get_arm_positions()}")
        else:
            print("  Failed to go to Person Pose.")
        time.sleep(1)

        print("\nTesting arm movement: Going to Rest Pose...")
        if robot_controller.go_to_rest_pose(wait=True, segment_duration_s=2.0):
            print(f"  Arm at Rest: {robot_controller.get_arm_positions()}")
        else:
            print("  Failed to go to Rest Pose.")
        time.sleep(1)

        print("\nTesting arm movement: Going back to Home Pose...")
        if robot_controller.go_to_home_pose(wait=True, segment_duration_s=2.0):
            print(f"  Arm at Home: {robot_controller.get_arm_positions()}")
        else:
            print("  Failed to go to Home Pose.")
        time.sleep(1)

        # --- Test Basic Gripper Actions ---
        print("\nTesting gripper: Closing gripper (default current)...")
        if robot_controller.close_gripper(wait_for_stop=True, desired_duration_s=1.0): 
            print(f"  Gripper closed. Position: {robot_controller.get_gripper_position()}, Load: {robot_controller.get_gripper_load_current()}")
        else:
            print("  Failed to close gripper.")
        time.sleep(1)

        print("\nTesting gripper: Opening gripper...")
        if robot_controller.open_gripper(wait=True, desired_duration_s=1.0):
            print(f"  Gripper opened. Position: {robot_controller.get_gripper_position()}")
        else:
            print("  Failed to open gripper.")
        time.sleep(1)

        # --- Dummy path test removed as requested ---

        print("\nTest sequence finished. Returning to Rest Pose before disconnect.")        
        robot_controller.open_gripper(wait=True, desired_duration_s=2.0)
        robot_controller.go_to_rest_pose(wait=True, segment_duration_s=2.0)

    except KeyboardInterrupt:
        print("\nWARN (Test): KeyboardInterrupt received. Attempting to disconnect.")
    except Exception as e:
        print(f"ERROR (Test): An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if robot_controller and robot_controller.is_connected: # Check if connected before trying to disconnect
            print("INFO (Test): Disconnecting robot in finally block...")
            robot_controller.disconnect()
        elif robot_controller and not robot_controller.is_initialized_properly:
            print("INFO (Test): Robot controller was not properly initialized. No active connection to disconnect.")
        else: # Handles case where robot_controller might be None if __init__ failed badly
            print("INFO (Test): Robot controller object not available or not connected. Exiting test.")
    print("--- OpenManipulatorXControl Standalone Test Finished ---")