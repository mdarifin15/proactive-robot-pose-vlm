# arm_controller.py

import time
from dynamixel_sdk import GroupSyncWrite # For multi-joint position commands
from dxl_sdk_interface import DynamixelSDKInterface

class ArmController:
    PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC = 15.633 # Example, adjust if needed

    def __init__(self, joint_ids_list, arm_config, common_motion_config, 
                 dxl_io: DynamixelSDKInterface, port_handler, packet_handler):
        self.joint_ids = joint_ids_list
        if len(self.joint_ids) != 4:
            raise ValueError("ArmController expects a list of 4 joint IDs.")
        self.config = arm_config # e.g., robot_hardware_config['arm_settings']
        self.common_cfg = common_motion_config # e.g., robot_hardware_config['common_motion_parameters']
        self.dxl_io = dxl_io
        self.port_handler = port_handler
        self.packet_handler = packet_handler

        self.home_pose = list(self.config['home_pose'])
        self.rest_pose = list(self.config['rest_pose'])
        self.to_person_pose = list(self.config.get('to_person_pose', self.home_pose)) # *** ADDED: Load to_person_pose, fallback to home_pose if not defined ***
        if len(self.to_person_pose) != 4:
            print(f"WARN (ArmController): 'to_person_pose' in config is not length 4. Using home_pose as fallback for person_pose.")
            self.to_person_pose = list(self.home_pose)

        self.default_profile_vel = int(self.config['default_profile_vel'])
        self.default_profile_accel = int(self.config['default_profile_accel'])
        self.default_op_mode = int(self.config['default_operating_mode'])
        
        self.default_tolerance = int(self.common_cfg.get('default_joint_tolerance', 30))
        self.default_wait_timeout = float(self.common_cfg.get('default_wait_timeout_s', 7.0))

        # Initialize GroupSyncWrite for Goal Position
        addr_goal_pos = self.dxl_io._get_const("addr_goal_position")
        len_goal_pos = self.dxl_io._get_const("len_goal_position")
        if addr_goal_pos is None or len_goal_pos is None:
            raise ValueError("addr_goal_position or len_goal_position not in dxl_common_constants")
        self.groupSyncWritePosition = GroupSyncWrite(self.port_handler, self.packet_handler,
                                                     addr_goal_pos, len_goal_pos)

        self.current_torque_enabled_for_joints = [False] * len(self.joint_ids)
        self.current_positions_cache = [0] * len(self.joint_ids) # Init with placeholder

    def set_torque_all(self, enable, verbose=True):
        overall_success = True
        status_val = self.dxl_io._get_const('torque_enable_val', 1) if enable else self.dxl_io._get_const('torque_disable_val', 0)
        for i, motor_id in enumerate(self.joint_ids):
            if not self.dxl_io.write_data(motor_id, "addr_torque_enable", status_val, length_name="len_torque_enable", verbose_on_error=verbose): # len=1
                overall_success = False
            else:
                self.current_torque_enabled_for_joints[i] = enable
            time.sleep(0.005) # Small delay between commands
        if verbose: print(f"INFO [Arm Joints] Torque {'ENABLED' if enable else 'DISABLED'} {'successfully' if overall_success else 'with errors'}.")
        return overall_success

    def set_operating_mode_all(self, mode_val=None, force_torque_disable=True, verbose=True):
        target_mode = mode_val if mode_val is not None else self.default_op_mode
        
        # --- NEW: Check if a change is even necessary ---
        # Read the operating mode of the first joint as a representative sample.
        first_joint_id = self.joint_ids[0]
        try:
            current_mode = self.dxl_io.read_data(first_joint_id, "addr_operating_mode", length_name="len_operating_mode")
            if current_mode is not None and current_mode == target_mode:
                if verbose: print(f"INFO [Arm Joints] OpMode is already set to {target_mode}. No change needed.")
                # If the mode is already correct, do nothing and return success.
                # This prevents the torque from being disabled unnecessarily.
                return True
        except Exception as e:
            print(f"WARN [Arm Joints] Could not read current OpMode to verify: {e}. Proceeding with mode set.")
        # --- END OF NEW CHECK ---

        # If we get here, it means the mode is different or we couldn't check it,
        # so we proceed with the original logic.
        overall_success = True
        if force_torque_disable or any(self.current_torque_enabled_for_joints):
            if verbose: print(f"INFO [Arm Joints] Disabling torque to change OpMode to {target_mode}...")
            self.set_torque_all(False, verbose=False)
            time.sleep(0.1)

        for motor_id in self.joint_ids:
            if not self.dxl_io.write_data(motor_id, "addr_operating_mode", target_mode, length_name="len_operating_mode", verbose_on_error=verbose):
                overall_success = False
            time.sleep(0.005)
        
        if overall_success and verbose: print(f"INFO [Arm Joints] Operating mode set to {target_mode}.")
        elif not overall_success and verbose: print(f"ERROR [Arm Joints] Failed to set OpMode for one or more joints.")
        
        return overall_success

    def set_profile_velocity_all(self, velocity_val, verbose=False):
        overall_success = True
        safe_vel = max(1, int(velocity_val)) # Basic sanity check
        for motor_id in self.joint_ids:
            if not self.dxl_io.write_data(motor_id, "addr_profile_velocity", safe_vel, length_name="len_profile_velocity", verbose_on_error=verbose): # len=4
                overall_success = False
            time.sleep(0.005)
        return overall_success

    def set_profile_acceleration_all(self, accel_val, verbose=False):
        overall_success = True
        safe_accel = max(0, int(accel_val)) # 0 can mean infinite accel for some profiles
        for motor_id in self.joint_ids:
            if not self.dxl_io.write_data(motor_id, "addr_profile_acceleration", safe_accel, length_name="len_profile_acceleration", verbose_on_error=verbose): #len=4
                overall_success = False
            time.sleep(0.005)
        return overall_success

    def get_positions(self, use_cache=False, verbose_on_error=False):
        if use_cache and all(p is not None for p in self.current_positions_cache): # Check if cache is valid
            return list(self.current_positions_cache) # Return a copy

        positions = []
        success = True
        for i, motor_id in enumerate(self.joint_ids):
            pos = self.dxl_io.read_data(motor_id, "addr_present_position", length_name="len_present_position", verbose_on_error=verbose_on_error)
            if pos is None: success = False; break
            positions.append(pos)
            self.current_positions_cache[i] = pos
        return positions if success and len(positions) == len(self.joint_ids) else None

    def update_joint_positions_cache(self):
        return self.get_positions(use_cache=False, verbose_on_error=False) is not None


    def _wait_for_goal_achievement(self, target_positions, tolerance=None, timeout_s=None):
        _tol = tolerance if tolerance is not None else self.default_tolerance
        _time = timeout_s if timeout_s is not None else self.default_wait_timeout
        start_time = time.time()

        while time.time() - start_time < _time:
            current_positions = self.get_positions(use_cache=False)
            if current_positions is None:
                time.sleep(0.1) # Error reading, wait and retry
                continue
            
            all_reached = True
            for i in range(len(self.joint_ids)):
                if abs(current_positions[i] - target_positions[i]) > _tol:
                    all_reached = False
                    break
            if all_reached:
                #print(f"INFO [Arm Joints] Reached target pose {target_positions}.")
                return True
            time.sleep(0.05) # Check interval

        final_positions = self.get_positions(use_cache=False)
        print(f"WARN [Arm Joints] Did not reach target {target_positions} within timeout. Final: {final_positions}")
        return False

    def move_to_pose(self, target_arm_joint_positions, desired_segment_duration_s=None, wait=False, timeout_s=None):
        if len(target_arm_joint_positions) != len(self.joint_ids):
            print(f"ERROR [ArmCtrl] target_arm_joint_positions length mismatch. Expected {len(self.joint_ids)}."); return False
        if not all(self.current_torque_enabled_for_joints): # Check if all arm torques are on
            print(f"WARN [ArmCtrl] Torque not enabled for all arm joints. Motion may fail.");
            # Optionally attempt to enable torque here, or let it fail.
            # self.set_torque_all(True, verbose=False) 

        # Set profile velocities based on desired_segment_duration_s
        if desired_segment_duration_s is not None and desired_segment_duration_s > 0.01:
            if not self.update_joint_positions_cache(): # Get current positions for speed calc
                print("ERROR [ArmCtrl] Failed to read current arm positions for dynamic speed calc. Using default speeds.")
                self.set_profile_velocity_all(self.default_profile_vel, verbose=False)
            else:
                for i, motor_id in enumerate(self.joint_ids):
                    current_pos = self.current_positions_cache[i]
                    target_pos = target_arm_joint_positions[i]
                    distance = abs(target_pos - current_pos)
                    
                    profile_vel_reg_val = self.default_profile_vel
                    if distance == 0: profile_vel_reg_val = 1 # Minimal speed
                    elif distance > 0:
                        effective_duration = max(desired_segment_duration_s, 0.02)
                        # This calculation was from omx_control.py
                        required_speed_units_per_sec = distance / effective_duration
                        profile_vel_reg_val = int(round(required_speed_units_per_sec / self.PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC))
                        profile_vel_reg_val = max(1, min(profile_vel_reg_val, self.dxl_io._get_const("max_profile_velocity_val", 4000) ))
                    
                    self.dxl_io.write_data(motor_id, "addr_profile_velocity", profile_vel_reg_val, length_name="len_profile_velocity", verbose_on_error=False)
        else: # Use default velocity
            self.set_profile_velocity_all(self.default_profile_vel, verbose=False)

        # Use GroupSyncWrite for positions
        self.groupSyncWritePosition.clearParam()
        param_added_successfully = True
        for i, motor_id in enumerate(self.joint_ids):
            pos_val = int(target_arm_joint_positions[i])
            # Parameter for GroupSyncWrite should be little-endian format byte array
            param_goal = [ (pos_val >> 0) & 0xFF, 
                           (pos_val >> 8) & 0xFF, 
                           (pos_val >> 16) & 0xFF, 
                           (pos_val >> 24) & 0xFF ]
            if not self.groupSyncWritePosition.addParam(motor_id, param_goal):
                print(f"ERROR [ArmCtrl ID:{motor_id}] GroupSyncWrite addParam failed.");
                param_added_successfully = False; break
        
        if not param_added_successfully: return False

        comm_res = self.groupSyncWritePosition.txPacket()
        if comm_res != self.dxl_io.COMM_SUCCESS_VAL:
            print(f"ERROR [ArmCtrl] GroupSyncWrite txPacket failed: {self.packet_handler.getTxRxResult(comm_res)}"); return False

        # Update cache optimistically
        for i in range(len(self.joint_ids)): self.current_positions_cache[i] = target_arm_joint_positions[i]

        if wait:
            effective_timeout = timeout_s if timeout_s is not None else self.default_wait_timeout
            if not self._wait_for_goal_achievement(target_arm_joint_positions, self.default_tolerance, effective_timeout):
                return False # Wait failed
        return True


    def go_to_home_pose(self, wait=True, segment_duration_s=1.5):
        #print("INFO [ArmCtrl] Moving arm to Home Pose...")
        return self.move_to_pose(self.home_pose,
                                 desired_segment_duration_s=segment_duration_s,
                                 wait=wait)

    def go_to_rest_pose(self, wait=True, segment_duration_s=2.0):
        #print("INFO [ArmCtrl] Moving arm to Rest Pose...")
        return self.move_to_pose(self.rest_pose,
                                 desired_segment_duration_s=segment_duration_s,
                                 wait=wait)

    def go_to_person_pose(self, wait=True, segment_duration_s=2.0):
        #print("INFO [ArmCtrl] Moving arm to Person Pose...")
        return self.move_to_pose(self.to_person_pose,
                                 desired_segment_duration_s=segment_duration_s,
                                 wait=wait)

    def setup_default_state(self, enable_torque_after=False, verbose=True):
        if verbose: print(f"INFO [ArmCtrl] Setting up default state for arm joints...")
        if not self.set_operating_mode_all(verbose=verbose): return False # Sets to its default_op_mode
        if not self.set_profile_acceleration_all(self.default_profile_accel, verbose=verbose): return False
        if not self.set_profile_velocity_all(self.default_profile_vel, verbose=verbose): return False
        
        # For position mode, Goal Current is often not used or set to 0 (max for mode)
        # If using current-based position control for arm, would set goal current here.
        # Assuming arm is in Position Control Mode (3) from config.

        if enable_torque_after:
            if not self.set_torque_all(True, verbose=verbose): return False
        return True