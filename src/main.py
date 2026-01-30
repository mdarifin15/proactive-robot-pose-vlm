# main.py (Final Corrected Version)

import sys
import os
import yaml
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

from google import genai
import tts_handler
import robot_gui

# --- Project root and config/data paths ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(PROJECT_ROOT, 'config')
CONFIG_ROBOT_PATH = os.path.join(CONFIG_DIR, 'robot_hardware_config.yaml')
CONFIG_LLM_PATH = os.path.join(CONFIG_DIR, 'llm_config.yaml')
CONFIG_TTS_PATH = os.path.join(CONFIG_DIR, 'tts_config.yaml')

def load_all_configurations():
    """MODIFIED: Loads all three required configuration files."""
    configs = {"robot": None, "llm": None, "tts": None}
    try:
        with open(CONFIG_ROBOT_PATH, 'r') as f:
            configs["robot"] = yaml.safe_load(f)
        with open(CONFIG_LLM_PATH, 'r') as f:
            configs["llm"] = yaml.safe_load(f)
        with open(CONFIG_TTS_PATH, 'r') as f:
            configs["tts"] = yaml.safe_load(f)
        print("MAIN: All configurations (Robot HW, LLM, TTS) loaded successfully.")
        return configs
    except FileNotFoundError as e:
        print(f"FATAL ERROR: Configuration file not found: {e.filename}")
        return None
    except Exception as e:
        print(f"FATAL ERROR: Error loading configurations: {e}")
        return None

if __name__ == '__main__':
    print("MAIN: Starting Robot Assistant Application...")

    load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("MAIN: CRITICAL ERROR: GEMINI_API_KEY not set. Exiting.")
        sys.exit(1)

    all_configs = load_all_configurations()
    if not all_configs:
        sys.exit(1)

    gemini_client = None
    try:
        # --- This is YOUR original, working initialization method ---
        gemini_client = genai.Client(api_key=gemini_api_key)
        print("MAIN: Gemini Client initialized successfully.")
    except Exception as e:
        print(f"MAIN: CRITICAL ERROR: Failed to initialize Gemini Client: {e}")
        sys.exit(1)

    app = QApplication(sys.argv)

    gui_window = robot_gui.RobotAppGUI(
        config_robot=all_configs['robot'],
        config_llm=all_configs['llm'],
        config_tts=all_configs['tts'],
        gemini_client=gemini_client
    )
    gui_window.show()

    exit_code = app.exec()
    print("MAIN: Application has been closed. Exiting.")
    sys.exit(exit_code)