# llm_analyzer.py

import PIL.Image
import json
import os
import re
import traceback
from google import genai # Assuming this is your working import for google-genai SDK

# Constants like AVAILABLE_ROBOT_ACTIONS and GEMINI_MODEL_NAME will now be passed in
# or loaded from config by the calling module.
# The main prompt template will also be passed in.

def extract_json_from_llm_text(llm_text_response):
    """
    Extracts a JSON block from the LLM's text response.
    Assumes JSON is wrapped in ```json ... ``` or is the main parsable JSON.
    """
    if not llm_text_response:
        print("LLM JSON Extractor: Received empty text response.")
        return None
        
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", llm_text_response, re.DOTALL | re.IGNORECASE)
    
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"LLM JSON Parse Error (from markdown block): {e}")
            print(f"Extracted string: {json_str}")
            return None # Failed to parse the extracted block
    else:
        # If no markdown block, try to parse the whole string if it looks like JSON
        # This is a fallback. The prompt strongly requests JSON in a markdown block.
        try:
            # A simple check if the string starts with { and ends with }
            if llm_text_response.strip().startswith('{') and llm_text_response.strip().endswith('}'):
                return json.loads(llm_text_response)
            else:
                print("LLM JSON Extractor: No JSON markdown block found and response doesn't appear to be direct JSON.")
                return None
        except json.JSONDecodeError as e:
            print(f"LLM JSON Parse Error (direct parse attempt): {e}")
            print(f"Full response text was: {llm_text_response}")
            return None

def get_image_analysis_for_gui(
    image_path, 
    client_to_use, 
    vision_model_name, 
    prompt_template, 
    available_actions_list
    ):
    """
    Analyzes an image using the Gemini model and returns structured information
    for the GUI: symptom description, insights, and suggested actions.

    Args:
        image_path (str): Path to the image file.
        client_to_use (genai.Client): Initialized Gemini client.
        vision_model_name (str): Name of the vision model to use.
        prompt_template (str): The prompt template string, expecting {action_list_placeholder}.
        available_actions_list (list): List of available robot actions for the prompt.

    Returns:
        dict: A dictionary with keys "symptom_description", "symptom_insights_text", 
              "action_labels", "raw_llm_response", "error".
              Values will be None or empty if errors occur or data not found.
    """
    results = {
        "symptom_description": None,
        "symptom_insights_text": None,
        "action_labels": [],
        "raw_llm_response": None,
        "error": None
    }

    try:
        if not client_to_use:
            results["error"] = "Gemini client not provided."
            return results

        print(f"LLM_ANALYZER: Loading image from: {image_path}")
        img = PIL.Image.open(image_path)
        
        # Format the prompt with the available actions
        formatted_actions = ", ".join([f"'{action}'" for action in available_actions_list])
        final_prompt = prompt_template.format(action_list_placeholder=formatted_actions)
        
        print(f"LLM_ANALYZER: Sending request to vision model '{vision_model_name}'...")
        # print(f"LLM_ANALYZER: Using prompt:\n{final_prompt[:300]}...") # For debugging prompt

        response = client_to_use.models.generate_content( 
            model=vision_model_name, 
            contents=[final_prompt, img] # Send prompt first, then image
        )
        
        results["raw_llm_response"] = response.text if hasattr(response, 'text') else "No text in response"

        if not response.candidates: # Check if response has candidates
            results["error"] = "LLM response has no candidates."
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and \
               hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                block_reason_message = getattr(response.prompt_feedback, 'block_reason_message', '')
                results["error"] = f"LLM response blocked: {response.prompt_feedback.block_reason}. {block_reason_message}".strip()
            return results
        
        # Extract text from parts, robustly
        llm_full_text = ""
        first_candidate = response.candidates[0]
        if hasattr(first_candidate, 'content') and hasattr(first_candidate.content, 'parts') and first_candidate.content.parts:
            for part in first_candidate.content.parts:
                if hasattr(part, 'text') and part.text is not None:
                    llm_full_text += part.text 
        
        if not llm_full_text and hasattr(response, 'text') and response.text: # Fallback
            llm_full_text = response.text

        results["raw_llm_response"] = llm_full_text # Store the full text for potential debugging

        if not llm_full_text:
            results["error"] = "LLM vision response was empty or contained no text parts."
            return results

        print("LLM_ANALYZER: Vision response received. Attempting to parse JSON...")
        parsed_json = extract_json_from_llm_text(llm_full_text)

        if parsed_json:
            results["symptom_description"] = parsed_json.get("symptom_description", "Description not found in LLM response.")
            results["symptom_insights_text"] = parsed_json.get("symptom_insights_text", "Insights not found in LLM response.")
            raw_action_labels = parsed_json.get("action_labels", [])
            
            # Validate action labels against the available list
            results["action_labels"] = [label for label in raw_action_labels if label in available_actions_list]
            if len(results["action_labels"]) != len(raw_action_labels):
                print(f"LLM_ANALYZER Warning: Some suggested actions were filtered: {set(raw_action_labels) - set(results['action_labels'])}")
            if not results["action_labels"] and raw_action_labels: # If all actions were filtered
                 print(f"LLM_ANALYZER Warning: All suggested actions {raw_action_labels} were invalid.")


            if not results["symptom_description"] and not results["symptom_insights_text"] and not results["action_labels"]:
                 results["error"] = "Parsed JSON, but required fields (description, insights, actions) are missing."
        else:
            results["error"] = "Failed to parse JSON from LLM response. Raw response logged."
            print(f"LLM_ANALYZER Full text for debugging JSON failure: {llm_full_text}")

        return results

    except FileNotFoundError:
        results["error"] = f"Image file not found at '{image_path}'."
        return results
    except Exception as e:
        results["error"] = f"Unexpected error during image analysis: {type(e).__name__} - {e}"
        traceback.print_exc() # Print full traceback for unexpected errors
        return results

if __name__ == "__main__":
    # This standalone test requires manual setup of configs or dummy values.
    print("--- Testing LLM Analyzer Module Independently ---")
    
    # --- Dummy Configs for Standalone Test ---
    # In a real run, these would be loaded from YAML files by the main app and passed in.
    TEST_API_KEY = os.getenv("GEMINI_API_KEY") # Ensure this is set in your environment
    if not TEST_API_KEY:
        print("GEMINI_API_KEY not set. Cannot run standalone test.")
        exit()

    test_client = genai.Client(api_key=TEST_API_KEY)
    
    # These should match your config.yaml structures
    test_vision_model_name = "gemini-2.0-flash" # From llm_config.yaml
    test_available_actions = [ # From robot_config.yaml
        "Neutral", "Call Doctor", "Take Tools", "Drug", 
        "Person", "Tissue", "Water", "Cool compress"
    ]
    test_prompt_template = """\
Based on the provided image of a person:
1.  **Symptom Description:** Provide a single, empathetic paragraph (2-3 sentences) describing the person's primary observed symptom(s) or condition. This should be suitable for direct display to a user.
2.  **Symptom Likelihoods:** List up to 3-4 potential symptoms or conditions you infer from the image. For each, provide an estimated likelihood as a percentage (e.g., "Headache: 70%"). Format this as a bulleted list within a single string (use \\n for new lines). Do not include any explanations or justifications for these likelihoods.
3.  **Suggested Robot Actions:** Based on the primary symptom/condition, suggest a sequence of **two (2) or three (3) distinct action labels** from the `action_list_placeholder` below that an assistive robot should perform to help. The available actions for you to choose from are: {action_list_placeholder}. **CRITICAL: Your `action_labels` list in the JSON output MUST NOT include 'Person' or 'Neutral'.** These are handled by separate robot logic or are default states. If a situation very strongly calls for only a single, critical action (e.g., "Call Doctor") from the list (excluding 'Person' or 'Neutral'), you may provide just that one action. Otherwise, please provide two or three distinct actions.

Your entire response MUST be a single JSON object with the following exact keys:
"symptom_description": (string),
"symptom_insights_text": (string, containing the formatted bulleted list for probabilities/insights),
"action_labels": (list of strings, e.g., ["Action1", "Action2"])

Example JSON output:
{{
"symptom_description": "The person in the image appears to be resting in bed and using a tissue, possibly indicating symptoms of a cold or flu.",
"symptom_insights_text": "- Common Cold: 80%\\n- Allergies: 30%\\n- Fatigue: 65%", # Example with percentages
"action_labels": ["Tissue", "Water"]
}}
Example if only one critical action is appropriate:
{{
"symptom_description": "The person appears to be having a severe medical emergency.",
"symptom_insights_text": "- Possible heart attack: High likelihood",
"action_labels": ["Call Doctor"]
}}
"""
    # Create a dummy image for testing
    dummy_image_path = "llm_analyzer_test_image.jpg"
    if not os.path.exists(dummy_image_path):
        try:
            print(f"Creating dummy image for test: {dummy_image_path}")
            dummy_img = PIL.Image.new('RGB', (100, 100), color = 'cyan')
            dummy_img.save(dummy_image_path)
        except Exception as e_img:
            print(f"Could not create dummy image: {e_img}. Test may fail.")
            exit()

    if os.path.exists(dummy_image_path):
        print(f"\nAnalyzing dummy image: {dummy_image_path}")
        analysis_result = get_image_analysis_for_gui(
            dummy_image_path,
            test_client,
            test_vision_model_name,
            test_prompt_template,
            test_available_actions
        )
        print("\n--- Analysis Result ---")
        if analysis_result["error"]:
            print(f"Error: {analysis_result['error']}")
        else:
            print(f"Symptom Description: {analysis_result['symptom_description']}")
            print(f"Symptom Insights:\n{analysis_result['symptom_insights_text']}")
            print(f"Suggested Actions: {analysis_result['action_labels']}")
        # print(f"\nRaw LLM Response:\n{analysis_result['raw_llm_response']}") # For debugging LLM output
    else:
        print(f"Cannot run test, dummy image '{dummy_image_path}' not found and could not be created.")