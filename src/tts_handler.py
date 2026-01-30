# tts_handler.py
import os
import asyncio
import traceback
from google import genai 
import pyaudio
import io
import time 

# --- Constants for Jitter Buffer ---
PREBUFFER_DURATION_SECONDS = 0.75 

# --- PyAudio Instance Management (Module-Level) ---
_pya_instance_tts = None
TTS_ENABLED_FLAG = True 

def init_pyaudio_for_tts():
    """Initializes the global PyAudio instance for this module if not already done."""
    global _pya_instance_tts, TTS_ENABLED_FLAG
    if not TTS_ENABLED_FLAG: 
        # print("TTS_HANDLER: TTS explicitly disabled, not initializing PyAudio.") # Optional
        return None
    if _pya_instance_tts is None:
        try:
            print("TTS_HANDLER: Initializing PyAudio instance...")
            _pya_instance_tts = pyaudio.PyAudio()
            print("TTS_HANDLER: PyAudio instance initialized successfully.")
        except Exception as e:
            print(f"TTS_HANDLER: CRITICAL - Failed to initialize PyAudio: {e}")
            traceback.print_exc()
            TTS_ENABLED_FLAG = False 
            return None
    return _pya_instance_tts

def terminate_pyaudio_for_tts():
    """Terminates the global PyAudio instance for this module."""
    global _pya_instance_tts
    if _pya_instance_tts is not None:
        try:
            print("TTS_HANDLER: Terminating PyAudio instance...")
            _pya_instance_tts.terminate()
            print("TTS_HANDLER: PyAudio instance terminated.")
        except Exception as e:
            print(f"TTS_HANDLER: Warning - Error terminating PyAudio: {e}")
        finally: 
            _pya_instance_tts = None

def set_tts_enabled_status(is_enabled):
    """Sets the global TTS enabled flag and manages PyAudio instance accordingly."""
    global TTS_ENABLED_FLAG
    TTS_ENABLED_FLAG = is_enabled
    if not is_enabled and _pya_instance_tts: 
        terminate_pyaudio_for_tts()

async def speak_using_live_session( 
    core_intent_for_robot_to_express, 
    live_session, 
    pya_instance_local, 
    all_tts_configs: dict, 
    gui_speech_update_callback=None
    ):
    global TTS_ENABLED_FLAG
    if not TTS_ENABLED_FLAG or not live_session or not pya_instance_local:
        msg = f"Robot (TTS Disabled/setup issue): {core_intent_for_robot_to_express}"
        # Try to inform GUI even if TTS is off here, based on the flag.
        if gui_speech_update_callback: 
            gui_speech_update_callback(f"System: TTS disabled. Intended: {core_intent_for_robot_to_express.split(':')[0].strip()}...")
        print(msg)
        return
        
    stream = None
    robot_persona_prompt = all_tts_configs['robot_persona_prompt_tts']
    pyaudio_settings = all_tts_configs['pyaudio_settings']
    final_llm_prompt = robot_persona_prompt + "'" + core_intent_for_robot_to_express + "'"

    # Log the core intent for developer debugging
    #print(f"TTS_HANDLER (Executing Core Intent for Speech): {core_intent_for_robot_to_express}") 
    
    # Initial GUI message indicating processing
    #if gui_speech_update_callback:
    #    gui_speech_update_callback(f"Robot: Processing \"{core_intent_for_robot_to_express.split(':')[0].strip()}...\"")

    try:
        pyaudio_format_val = pyaudio_settings.get('format_int', pyaudio.paInt16)
        if pyaudio_format_val == 8: pyaudio_format_val = pyaudio.paInt16

        pyaudio_rate = pyaudio_settings['playback_rate']
        pyaudio_channels = pyaudio_settings['channels']
        bytes_per_sample = pya_instance_local.get_sample_size(pyaudio_format_val)
        bytes_per_second = pyaudio_rate * pyaudio_channels * bytes_per_sample
        prebuffer_target_bytes = int(bytes_per_second * PREBUFFER_DURATION_SECONDS)

        stream = pya_instance_local.open(
            format=pyaudio_format_val, 
            channels=pyaudio_channels,
            rate=pyaudio_rate, 
            output=True,
            frames_per_buffer=pyaudio_settings['chunk_size']
        )
        
        await live_session.send(input=final_llm_prompt, end_of_turn=True) 
        
        turn_iterator = live_session.receive() 
        audio_chunks_processed_count = 0
        # We are not expecting separate text parts from Live API for TTS based on user feedback
        
        initial_buffer_list = []
        current_buffered_bytes = 0
        initial_buffering_complete = False

        # print(f"DEBUG_TTS: Pre-buffering target: {prebuffer_target_bytes} bytes...") # Optional

        async for response_chunk in turn_iterator:
            if hasattr(response_chunk, 'error') and response_chunk.error:
                err_msg_stream = f"System Alert: Error in speech stream - {response_chunk.error}"
                print(f"TTS_HANDLER Error in stream: {response_chunk.error}")
                if gui_speech_update_callback: gui_speech_update_callback(err_msg_stream)
                break 
            
            audio_data_piece = None
            if hasattr(response_chunk, 'data') and response_chunk.data:
                audio_data_piece = response_chunk.data
            
            if audio_data_piece:
                if not initial_buffering_complete:
                    initial_buffer_list.append(audio_data_piece)
                    current_buffered_bytes += len(audio_data_piece)
                    if current_buffered_bytes >= prebuffer_target_bytes:
                        initial_buffering_complete = True
                        for buffered_chunk in initial_buffer_list:
                            await asyncio.to_thread(stream.write, buffered_chunk)
                        audio_chunks_processed_count += 1 
                        initial_buffer_list.clear() 
                else: 
                    await asyncio.to_thread(stream.write, audio_data_piece)
                    audio_chunks_processed_count += 1 
        
        if not initial_buffering_complete and initial_buffer_list:
            for buffered_chunk in initial_buffer_list:
                await asyncio.to_thread(stream.write, buffered_chunk)
                audio_chunks_processed_count +=1 
            initial_buffer_list.clear()

        if stream and audio_chunks_processed_count > 0:
            if not stream.is_stopped():
                await asyncio.to_thread(stream.stop_stream) 
            wait_start_time = time.monotonic(); max_wait_drain = 10.0 
            while stream.is_active():
                if time.monotonic() - wait_start_time > max_wait_drain: break
                await asyncio.sleep(0.05) 
        
        # --- GUI Update for what was spoken (using Core Intent as proxy) ---
        if audio_chunks_processed_count > 0: 
            # Summarize the core intent for GUI display
            intent_summary = core_intent_for_robot_to_express
            if ":" in intent_summary: # Try to get the part after "Core Intent:"
                intent_summary = intent_summary.split(':', 1)[1].strip()
            # Capitalize first letter for display
            intent_summary = intent_summary[0].upper() + intent_summary[1:] if intent_summary else "an action"

            display_text = f"Robot [Spoke about]: \"{intent_summary}\""
            if gui_speech_update_callback:
                gui_speech_update_callback(display_text)
            #print(f"  TTS_HANDLER: {display_text}") # Console log
        else: # No audio was processed
            warn_msg = "System Alert: No audio was generated or played for the speech task."
            if gui_speech_update_callback: gui_speech_update_callback(warn_msg) 
            print(f"TTS_HANDLER Warning: {warn_msg}")
            # Fallback to printing the original instruction for the console
            print(f"ROBOT (TTS Fallback - Console Print for core intent): {core_intent_for_robot_to_express}")
            
    except Exception as e: 
        err_msg = f"System Alert: Error in speech generation - {type(e).__name__}."
        print(f"Error in TTS_HANDLER (speak_using_live_session): {type(e).__name__} - {e}"); traceback.print_exc() 
        if gui_speech_update_callback: gui_speech_update_callback(err_msg) 
        fallback_msg_exception = f"ROBOT (TTS Fallback - Print for core intent): {core_intent_for_robot_to_express}"
        print(fallback_msg_exception)
        if gui_speech_update_callback: gui_speech_update_callback(fallback_msg_exception) # Also send to GUI
    finally: 
        if stream:
            try:
                if not stream.is_stopped(): await asyncio.to_thread(stream.stop_stream)
                await asyncio.to_thread(stream.close) 
            except Exception as e_stream_close:
                print(f"TTS_HANDLER Warning: Error closing PyAudio stream in finally: {e_stream_close}")