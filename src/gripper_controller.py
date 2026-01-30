# gripper_controller.py

import time
from dxl_sdk_interface import DynamixelSDKInterface # Assuming this is in the same directory or path

class GripperController:
    # Define constants based on typical X-series profile unit if needed for calculations here,
    # or rely on pre-calculated values from config for desired_duration_s.
    PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC = 15.633 # Example, same as in old omx_control

    def __init__(self, motor_id, gripper_config, common_motion_config, dxl_io: DynamixelSDKInterface):
        self.motor_id = motor_id
        self.config = gripper_config # e.g., robot_hardware_config['gripper_settings']
        self.common_cfg = common_motion_config # e.g., robot_hardware_config['common_motion_parameters']
        self.dxl_io = dxl_io

        # Extract and store key config values for frequent use
        self.open_pos = int(self.config['open_pos'])
        self.close_pos = int(self.config['close_pos'])
        self.default_grasp_current = int(self.config['default_grasp_current_limit'])
        self.default_profile_vel = int(self.config['default_profile_vel'])
        self.default_profile_accel = int(self.config['default_profile_accel'])
        self.default_op_mode = int(self.config['default_operating_mode'])
        
        self.action_timeout_s = float(self.common_cfg.get('gripper_action_timeout_s', 3.0)) # From common or specific
        self.grasp_wait_s = float(self.common_cfg.get('gripper_grasp_wait_s', 1.0))
        self.default_tolerance = int(self.common_cfg.get('default_joint_tolerance', 30))


        self.current_torque_enabled = False
        self.current_pos_cache = self.open_pos # Initialize cache to a known state

    def set_torque(self, enable, verbose=True):
        status_val = self.dxl_io._get_const('torque_enable_val', 1) if enable else self.dxl_io._get_const('torque_disable_val', 0)
        success = self.dxl_io.write_data(self.motor_id, "addr_torque_enable", status_val, length_name="len_torque_enable", verbose_on_error=verbose) # Assuming len_torque_enable = 1
        if success:
            self.current_torque_enabled = enable
            if verbose: print(f"INFO [Gripper ID:{self.motor_id}] Torque {'ENABLED' if enable else 'DISABLED'}.")
        else:
            if verbose: print(f"ERROR [Gripper ID:{self.motor_id}] Failed to {'enable' if enable else 'disable'} torque.")
        return success

    def set_operating_mode(self, mode_val=None, force_torque_disable=True, verbose=True):
        target_mode = mode_val if mode_val is not None else self.default_op_mode
        
        # Read current mode
        current_mode_read = self.dxl_io.read_data(self.motor_id, "addr_operating_mode", length_name="len_operating_mode", verbose_on_error=False)
        if current_mode_read == target_mode:
            if verbose: print(f"INFO [Gripper ID:{self.motor_id}] Already in OpMode {target_mode}.")
            return True

        if force_torque_disable or self.current_torque_enabled:
            if verbose: print(f"INFO [Gripper ID:{self.motor_id}] Disabling torque to change OpMode to {target_mode}...")
            self.set_torque(False, verbose=False)
            time.sleep(0.05) # Allow time for torque to disable

        success = self.dxl_io.write_data(self.motor_id, "addr_operating_mode", target_mode, length_name="len_operating_mode", verbose_on_error=verbose)
        time.sleep(0.05) # Allow mode to set

        if success:
            verified_mode = self.dxl_io.read_data(self.motor_id, "addr_operating_mode", length_name="len_operating_mode", verbose_on_error=verbose)
            if verified_mode == target_mode:
                if verbose: print(f"INFO [Gripper ID:{self.motor_id}] OpMode successfully set to {target_mode}.")
                # Optionally re-enable torque if it was on before
                # if self.current_torque_enabled and force_torque_disable: self.set_torque(True, verbose=False)
                return True
            else:
                if verbose: print(f"ERROR [Gripper ID:{self.motor_id}] OpMode verification failed. Expected {target_mode}, got {verified_mode}.")
                # Try to revert? Or just report error.
                return False
        return False

    def set_goal_current(self, current_value, verbose=True):
        # Clamp current_value if necessary, e.g., based on motor datasheet max for Goal Current
        # For XM430, Goal Current (102) range is 0 ~ 1193 typically.
        clamped_current = max(0, min(int(current_value), self.dxl_io._get_const("max_goal_current_val", 1193))) # Example max
        if verbose: print(f"INFO [Gripper ID:{self.motor_id}] Setting Goal Current to {clamped_current}.")
        return self.dxl_io.write_data(self.motor_id, "addr_goal_current", clamped_current, length_name="len_goal_current", verbose_on_error=verbose)

    def _set_profile_velocity(self, velocity_val, verbose=False):
        safe_velocity_val = max(1, min(int(velocity_val), self.dxl_io._get_const("max_profile_velocity_val", 4000))) # Example max
        return self.dxl_io.write_data(self.motor_id, "addr_profile_velocity", safe_velocity_val, length_name="len_profile_velocity", verbose_on_error=verbose)

    def _set_profile_acceleration(self, accel_val, verbose=False):
        safe_accel_val = max(0, min(int(accel_val), self.dxl_io._get_const("max_profile_acceleration_val", 1000))) # Example max, 0 for infinite accel
        return self.dxl_io.write_data(self.motor_id, "addr_profile_acceleration", safe_accel_val, length_name="len_profile_acceleration", verbose_on_error=verbose)

    def get_position(self, use_cache=False, verbose_on_error=False):
        if use_cache and self.current_pos_cache is not None:
            return self.current_pos_cache
        pos = self.dxl_io.read_data(self.motor_id, "addr_present_position", length_name="len_present_position", verbose_on_error=verbose_on_error)
        if pos is not None: self.current_pos_cache = pos
        return pos

    def get_load_current(self, verbose_on_error=False):
        raw_current = self.dxl_io.read_data(self.motor_id, "addr_present_current", length_name="len_present_current", verbose_on_error=verbose_on_error)
        if raw_current is not None:
            # Convert to signed int if necessary (assuming 2-byte value from X-series)
            if raw_current > 32767: raw_current -= 65536
        return raw_current
        
    def is_moving(self, verbose_on_error=False):
        moving_status = self.dxl_io.read_data(self.motor_id, "addr_moving", length_name="len_moving", verbose_on_error=verbose_on_error)
        return moving_status == 1 if moving_status is not None else None # Or False if None, depends on desired strictness

    def set_target_position(self, target_pos, desired_duration_s=None, wait=True, timeout_s=None, current_limit_override=None):
        if not self.current_torque_enabled:
            print(f"WARN [Gripper ID:{self.motor_id}] Torque is OFF. Cannot set position."); return False

        _timeout = timeout_s if timeout_s is not None else self.action_timeout_s
        
        if current_limit_override is not None:
            self.set_goal_current(current_limit_override, verbose=False)
        # Else, assume goal current is already set (e.g. default or by a prepare_ method)

        # Set profile velocity based on desired_duration_s or use default
        if desired_duration_s is not None and desired_duration_s > 0.01:
            current_gripper_pos = self.get_position(use_cache=True) # Use cache as it might be called rapidly
            if current_gripper_pos is None: current_gripper_pos = self.open_pos # Fallback
            
            distance = abs(target_pos - current_gripper_pos)
            profile_vel_reg_val = self.default_profile_vel
            if distance == 0: profile_vel_reg_val = 1 # Min speed if already there
            elif distance > 0:
                effective_duration = max(desired_duration_s, 0.02)
                required_speed_units_per_sec = distance / self.PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC # Rough calc
                profile_vel_reg_val = int(round(required_speed_units_per_sec / effective_duration )) # This formula is off, let's use the one from old omx_control
                # Corrected speed calc from old omx_control.py's set_gripper_position
                required_speed_units_per_sec_corrected = distance / effective_duration
                profile_vel_reg_val = int(round(required_speed_units_per_sec_corrected / self.PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC))
                profile_vel_reg_val = max(1, min(profile_vel_reg_val, self.dxl_io._get_const("max_profile_velocity_val", 4000)))


            self._set_profile_velocity(profile_vel_reg_val)
        else:
            self._set_profile_velocity(self.default_profile_vel)

        if not self.dxl_io.write_data(self.motor_id, "addr_goal_position", target_pos, length_name="len_goal_position"):
            return False
        self.current_pos_cache = target_pos # Tentative update

        if wait:
            start_time = time.time()
            while time.time() - start_time < _timeout:
                moving = self.is_moving()
                if moving is None : time.sleep(0.05); continue # Comm error, retry
                if not moving:
                    final_pos = self.get_position(use_cache=False) # Verify final position
                    if final_pos is not None and abs(final_pos - target_pos) <= self.default_tolerance:
                        #print(f"INFO [Gripper ID:{self.motor_id}] Reached target position {target_pos}.")
                        return True
                    elif final_pos is not None: # Stopped but not at target
                        #print(f"INFO [Gripper ID:{self.motor_id}] Stopped at {final_pos} (target {target_pos}). May be load/current limit.")
                        return True # Consider this success for gripper if it stopped (e.g. grasp)
                    else: # Error reading final position
                        print(f"WARN [Gripper ID:{self.motor_id}] Stopped, but failed to read final position.")
                        return False 
                time.sleep(0.05)
            print(f"WARN [Gripper ID:{self.motor_id}] Timeout waiting for gripper to reach {target_pos}.")
            return False
        return True # If not waiting, command sent is success

    def open(self, wait=True, desired_duration_s=None):
        #print(f"INFO [Gripper ID:{self.motor_id}] Opening gripper to {self.open_pos}.")
        # For opening, usually, we don't need a specific current limit override unless it's sticking
        return self.set_target_position(self.open_pos,
                                        desired_duration_s=desired_duration_s,
                                        wait=wait,
                                        timeout_s=self.action_timeout_s,
                                        current_limit_override=self.default_grasp_current) # Use default current for robust open

    def close(self, goal_current_limit=None, target_close_pos=None, wait_for_stop=True, desired_duration_s=None):
        _current_limit = goal_current_limit if goal_current_limit is not None else self.default_grasp_current
        _target_pos = target_close_pos if target_close_pos is not None else self.close_pos
        
        #print(f"INFO [Gripper ID:{self.motor_id}] Closing gripper towards {_target_pos} with current limit {_current_limit}.")
        # Set specific current for this close action
        self.set_goal_current(_current_limit, verbose=False) # Set current limit before moving
        
        return self.set_target_position(_target_pos,
                                        desired_duration_s=desired_duration_s,
                                        wait=wait_for_stop, # wait_for_stop corresponds to 'wait'
                                        timeout_s=self.action_timeout_s)


    def pick_object(self, goal_current_limit=None, grasp_wait_s=None, desired_duration_s=None):
        _grasp_wait_s = grasp_wait_s if grasp_wait_s is not None else self.grasp_wait_s
        #print(f"--- Attempting to pick object ---")
        if not self.close(goal_current_limit=goal_current_limit, # Pass through
                          target_close_pos=self.close_pos, # Always try to fully close
                          wait_for_stop=True, 
                          desired_duration_s=desired_duration_s):
            print(f"WARN [Gripper ID:{self.motor_id}] Gripper close command failed during pick.")
            return False # If close itself had an issue or timed out before stopping

        #print(f"INFO [Gripper ID:{self.motor_id}] Gripper grasp attempt complete. Waiting for {_grasp_wait_s}s...")
        time.sleep(_grasp_wait_s)
        
        final_load = self.get_load_current()
        final_pos = self.get_position(use_cache=False)
        #print(f"INFO [Gripper ID:{self.motor_id}] Grasp hold complete. Final state: Pos={final_pos}, LoadCurrent={final_load}")
        # Add heuristic check if needed, similar to old omx_control
        return True


    def release_object(self, wait=True, desired_duration_s=None):
        #print("--- Releasing object ---")
        return self.open(wait=wait, desired_duration_s=desired_duration_s)

    def prepare_for_gentle_grasp(self, desired_duration_s=1.0, verbose=True):
        # Uses logic from previous full omx_control.py version
        current_pos = self.get_position(use_cache=True)
        if current_pos is None: current_pos = self.open_pos 
        typical_grasp_distance = abs(self.close_pos - current_pos)
        if typical_grasp_distance < 50 : typical_grasp_distance = 300 
        
        profile_vel_reg_val = self.default_profile_vel
        if desired_duration_s > 0.01 and typical_grasp_distance > 0:
            required_speed_units_per_sec = typical_grasp_distance / desired_duration_s
            profile_vel_reg_val = int(round(required_speed_units_per_sec / self.PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC))
            profile_vel_reg_val = max(10, min(profile_vel_reg_val, self.default_profile_vel)) 
        else: profile_vel_reg_val = max(10, int(self.default_profile_vel * 0.33)) 

        gentle_accel_val = self.default_profile_accel // 2 
        gentle_accel_val = max(5, gentle_accel_val) 

        if verbose: print(f"INFO [Gripper ID:{self.motor_id}] Prep Gentle Grasp: Vel={profile_vel_reg_val}, Accel={gentle_accel_val}, CurrentLimit={self.default_grasp_current}")
        
        success = True
        if not self._set_profile_velocity(profile_vel_reg_val): success = False
        if not self._set_profile_acceleration(gentle_accel_val): success = False
        if not self.set_goal_current(self.default_grasp_current, verbose=False): success = False
        return success

    def prepare_for_gentle_release(self, desired_duration_s=1.5, verbose=True):
        # Uses logic from previous full omx_control.py version
        current_pos = self.get_position(use_cache=True)
        if current_pos is None: current_pos = self.close_pos 
        full_open_distance = abs(self.open_pos - current_pos)
        if full_open_distance < 50: full_open_distance = abs(self.open_pos - self.close_pos)

        profile_vel_reg_val = self.default_profile_vel
        if desired_duration_s > 0.01 and full_open_distance > 0:
            required_speed_units_per_sec = full_open_distance / desired_duration_s
            profile_vel_reg_val = int(round(required_speed_units_per_sec / self.PROFILE_VEL_UNIT_TO_POS_UNITS_PER_SEC))
            profile_vel_reg_val = max(10, min(profile_vel_reg_val, self.default_profile_vel))
        else: profile_vel_reg_val = max(10, int(self.default_profile_vel * 0.33))

        gentle_accel_val = self.default_profile_accel // 2
        gentle_accel_val = max(5, gentle_accel_val)

        if verbose: print(f"INFO [Gripper ID:{self.motor_id}] Prep Gentle Release: Vel={profile_vel_reg_val}, Accel={gentle_accel_val}")
        
        success = True
        if not self._set_profile_velocity(profile_vel_reg_val): success = False
        if not self._set_profile_acceleration(gentle_accel_val): success = False
        if not self.set_goal_current(self.default_grasp_current, verbose=False): success = False # Ensure current limit is set
        return success

    def reset_to_default_profiles_and_current(self, verbose=True):
        if verbose: print(f"INFO [Gripper ID:{self.motor_id}] Resetting gripper to default profiles and current limit.")
        success = True
        if not self._set_profile_velocity(self.default_profile_vel): success = False
        if not self._set_profile_acceleration(self.default_profile_accel): success = False
        if not self.set_goal_current(self.default_grasp_current, verbose=False): success = False
        return success

    def setup_default_state(self, enable_torque_after=False, verbose=True):
        if verbose: print(f"INFO [Gripper ID:{self.motor_id}] Setting up default state...")
        if not self.set_operating_mode(verbose=verbose): return False # Sets to its default_op_mode
        if not self.reset_to_default_profiles_and_current(verbose=verbose): return False
        if enable_torque_after:
            if not self.set_torque(True, verbose=verbose): return False
        return True