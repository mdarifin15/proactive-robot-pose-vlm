# path_smoother.py (Corrected to output standard numbers)

import yaml
import numpy as np
from scipy.signal import savgol_filter
import os

# --- Project root and data paths ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
INPUT_FILE = os.path.join(DATA_DIR, "taught_paths.yaml")
OUTPUT_FILE = os.path.join(DATA_DIR, "smoothed_paths.yaml")
WINDOW_LENGTH = 11
POLY_ORDER = 3
TIME_SCALING_FACTOR = 1.2
# --- End of Configuration ---


def smooth_path_data(path_data):
    """
    Applies a Savitzky-Golay filter to the joint data of a single path.
    Gripper data is preserved as is. Timestamps are recalculated.
    """
    if len(path_data) < WINDOW_LENGTH:
        print(f"  - WARN: Path is too short for smoothing (has {len(path_data)} points, needs {WINDOW_LENGTH}). Skipping.")
        return path_data

    timestamps = np.array([p['timestamp'] for p in path_data])
    joints = np.array([p['pose'][0:4] for p in path_data])
    gripper_values = np.array([p['pose'][4] for p in path_data])

    smoothed_joints = np.zeros_like(joints)
    for i in range(joints.shape[1]):
        smoothed_joints[:, i] = savgol_filter(joints[:, i], WINDOW_LENGTH, POLY_ORDER)

    original_duration = timestamps[-1] - timestamps[0]
    new_duration = original_duration * TIME_SCALING_FACTOR
    new_timestamps = np.linspace(0, new_duration, len(path_data))

    new_path_data = []
    for i in range(len(path_data)):
        new_pose = list(smoothed_joints[i]) + [int(gripper_values[i])]
        new_path_data.append({
            # --- THIS IS THE CORRECTED LINE ---
            'timestamp': float(round(new_timestamps[i], 4)),
            'pose': [int(round(p)) for p in new_pose]
        })

    return new_path_data


def main():
    """Main execution function."""
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file '{INPUT_FILE}' not found. Please teach paths first.")
        return

    print(f"Loading raw path data from '{INPUT_FILE}'...")
    with open(INPUT_FILE, 'r') as f:
        taught_paths = yaml.safe_load(f)

    if not taught_paths:
        print("Input file is empty. Nothing to do.")
        return

    smoothed_paths = {}
    print("\nStarting path smoothing process...")
    print(f"Filter settings: Window={WINDOW_LENGTH}, Polynomial Order={POLY_ORDER}, Time Scale={TIME_SCALING_FACTOR}x")
    
    for path_name, path_data in taught_paths.items():
        print(f" - Processing path: '{path_name}' ({len(path_data)} waypoints)")
        smoothed_data = smooth_path_data(path_data)
        smoothed_paths[path_name] = smoothed_data

    print(f"\nSaving smoothed paths to '{OUTPUT_FILE}'...")
    with open(OUTPUT_FILE, 'w') as f:
        yaml.dump(smoothed_paths, f, sort_keys=False, default_flow_style=None)

    print("\nProcess complete!")
    print(f"You can now test the new paths by updating your 'teach_config.yaml' to point to '{OUTPUT_FILE}'.")


if __name__ == '__main__':
    # Before running, you might need to install required libraries:
    # pip install pyyaml numpy scipy
    main()