import sys
import os

# Add project root to path
sys.path.append(r"c:\Users\chand\Downloads\backend")

try:
    from apps.whatsapp.constants import build_image_type_options_text
    from apps.whatsapp.workflow_builder import build_workflow
    import random

    print("--- Verifying constants.py ---")
    options = build_image_type_options_text({"human_part": "finger"})
    print(f"Options with human part: \n{options}")
    assert "On human (finger)" in options
    
    options_default = build_image_type_options_text()
    print(f"Default options: \n{options_default}")
    assert "Plain background" in options_default
    print("constants.py logic verified.")

    print("\n--- Verifying workflow_builder.py ---")
    mock_filename = "test_image.jpg"
    mock_prompt = "A beautiful gold ring"
    workflow = build_workflow(mock_filename, mock_prompt)
    
    assert workflow["46"]["inputs"]["image"] == mock_filename
    assert workflow["6"]["inputs"]["text"] == mock_prompt
    assert isinstance(workflow["25"]["inputs"]["noise_seed"], int)
    print("workflow_builder.py logic verified.")

except Exception as e:
    print(f"Verification failed: {e}")
    sys.exit(1)
