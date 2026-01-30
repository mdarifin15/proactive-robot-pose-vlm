# dxl_sdk_interface.py

import time
from dynamixel_sdk import COMM_SUCCESS

class DynamixelSDKInterface:
    def __init__(self, port_handler, packet_handler, dxl_common_constants):
        """
        Initializes with SDK handlers and common Dynamixel constants.
        Args:
            port_handler: Instance of PortHandler from dynamixel_sdk.
            packet_handler: Instance of PacketHandler from dynamixel_sdk.
            dxl_common_constants (dict): Loaded dynamixel_common_constants from config.
        """
        self.port_handler = port_handler
        self.packet_handler = packet_handler
        self.dxl_consts = dxl_common_constants
        self.COMM_SUCCESS_VAL = self.dxl_consts.get('comm_success_val', COMM_SUCCESS) # Default to SDK's COMM_SUCCESS if not in YAML

    def _get_const(self, name, default=None):
        """Helper to get a constant value, printing a warning if not found."""
        val = self.dxl_consts.get(name)
        if val is None:
            print(f"WARN (DynamixelSDKInterface): Constant '{name}' not found in dxl_common_constants. Using default: {default}")
            return default
        return val

    def _check_comm_status(self, motor_id, comm_result, error_val, operation_name="Operation", verbose=True):
        """
        Checks communication result and Dynamixel error.
        Returns True if successful, False otherwise.
        """
        if comm_result != self.COMM_SUCCESS_VAL:
            if verbose:
                print(f"ERROR [ID:{motor_id}] {operation_name} Comm: {self.packet_handler.getTxRxResult(comm_result)}")
            return False
        elif error_val != 0:
            if verbose:
                # Try to check if it's a hardware error status being read
                # This is a bit of a heuristic; context matters.
                addr_hw_err = self._get_const('addr_hardware_error_status', -1) # Get address if defined
                if operation_name.startswith("Read") and operation_name.endswith(f"Ad:{addr_hw_err}"):
                     # If reading hardware error status, the error_val itself is data if comm_result was success
                     # but packetHandler might still flag it as packet error if error bits are set.
                     # This case is tricky. For now, we assume if comm_result is success, error_val IS the data.
                     # If we are here, it means comm_result wasn't success OR error_val is a Dynamixel packet error.
                     print(f"ERROR [ID:{motor_id}] {operation_name} PacketErr: {self.packet_handler.getRxPacketError(error_val)} (RawVal: {error_val})")
                else:
                    print(f"ERROR [ID:{motor_id}] {operation_name} PacketErr: {self.packet_handler.getRxPacketError(error_val)} (RawVal: {error_val})")

            # Check for hardware errors specifically if the operation wasn't reading the error status itself
            # and error_val suggests a hardware issue (e.g., bit 7 set, though this varies by SDK usage)
            # For simplicity, any non-zero error_val after a successful comm_result is treated as a packet error.
            return False
        return True

    def read_data(self, motor_id, address_name, length_name=None, verbose_on_error=True):
        """
        Reads data from a specified address name for a motor.
        Address name and (optional) length name are keys in dxl_common_constants.
        Returns: Value read, or None on failure.
        """
        address = self._get_const(address_name)
        if address is None: return None

        length = 0
        if length_name:
            length = self._get_const(length_name)
            if length is None: return None
        elif "len_" in address_name: # Try to infer length from address name if length_name not provided
             inferred_length_name = address_name.replace("addr_", "len_")
             length = self._get_const(inferred_length_name)
             if length is None:
                 print(f"WARN (DynamixelSDKInterface): Could not infer length for {address_name}. Assuming based on common types or specify length_name.")
                 # Heuristic: guess based on common names, or default to 1 if unsure and not standard
                 if "position" in address_name.lower() or "velocity" in address_name.lower() or "pwm" in address_name.lower() or "current" in address_name.lower() and "goal_current" not in address_name.lower() : # goal_current is often 2B
                     if "goal_current" in address_name.lower() or "present_current" in address_name.lower():
                         length = self._get_const("len_present_current", 2) # default to 2 for current
                     elif "goal_position" in address_name.lower() or "present_position" in address_name.lower():
                         length = self._get_const("len_present_position", 4)
                     elif "velocity" in address_name.lower():
                          length = self._get_const("len_profile_velocity", 4) # Assuming profile vel
                     else:
                         length = 4 # Common for position/velocity
                 else: # Default to 1 byte if unsure
                     length = 1


        data = None
        comm_result = -1 # Initialize to a non-success value
        error_val = 0

        if length == 1:
            data, comm_result, error_val = self.packet_handler.read1ByteTxRx(self.port_handler, motor_id, address)
        elif length == 2:
            data, comm_result, error_val = self.packet_handler.read2ByteTxRx(self.port_handler, motor_id, address)
        elif length == 4:
            data, comm_result, error_val = self.packet_handler.read4ByteTxRx(self.port_handler, motor_id, address)
        else:
            if verbose_on_error:
                print(f"ERROR [ID:{motor_id}] Unsupported data length {length} for read at {address_name} (Addr: {address})")
            return None

        operation_desc = f"Read{length}B {address_name} Ad:{address}"
        if not self._check_comm_status(motor_id, comm_result, error_val, operation_desc, verbose=verbose_on_error):
            # Specific case for reading hardware error status: if comm was success but error_val is non-zero,
            # error_val *is* the hardware status byte.
            if address_name == "addr_hardware_error_status" and comm_result == self.COMM_SUCCESS_VAL:
                return error_val # Return the hardware error bits as data
            return None
        return data

    def write_data(self, motor_id, address_name, value, length_name=None, verbose_on_error=True):
        """
        Writes data to a specified address name for a motor.
        Returns: True on success, False on failure.
        """
        address = self._get_const(address_name)
        if address is None: return False

        length = 0
        if length_name:
            length = self._get_const(length_name)
            if length is None: return False
        elif "len_" in address_name: # Try to infer length
             inferred_length_name = address_name.replace("addr_", "len_")
             length = self._get_const(inferred_length_name)
             if length is None: # Fallback logic similar to read_data
                 if "goal_current" in address_name.lower(): length = self._get_const("len_goal_current",2)
                 elif "position" in address_name.lower(): length = self._get_const("len_goal_position",4)
                 elif "velocity" in address_name.lower(): length = self._get_const("len_profile_velocity",4)
                 elif "acceleration" in address_name.lower(): length = self._get_const("len_profile_acceleration",4) # Assuming 4 for profile accel
                 else: length = 1 # Default to 1 byte
        else: # Default to 1 byte if no length info
            length = 1


        comm_result = -1
        error_val = 0

        if length == 1:
            comm_result, error_val = self.packet_handler.write1ByteTxRx(self.port_handler, motor_id, address, int(value))
        elif length == 2:
            comm_result, error_val = self.packet_handler.write2ByteTxRx(self.port_handler, motor_id, address, int(value))
        elif length == 4:
            comm_result, error_val = self.packet_handler.write4ByteTxRx(self.port_handler, motor_id, address, int(value))
        else:
            if verbose_on_error:
                print(f"ERROR [ID:{motor_id}] Unsupported data length {length} for write at {address_name} (Addr: {address})")
            return False

        operation_desc = f"Write{length}B {address_name} Ad:{address} Val:{value}"
        return self._check_comm_status(motor_id, comm_result, error_val, operation_desc, verbose=verbose_on_error)