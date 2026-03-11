"""
Image Type Handler

Handles the image type selection question (Q2).
"""

import logging

from ..evolution import send_text_message
from ..session import get_prompt_document, get_jewellery_type_by_option

logger = logging.getLogger(__name__)


# Map option letters to image_type values
OUTPUT_MAP = {
    "A": "plain",
    "B": "human",
    "C": "aesthetic"
}


def handle_image_type(session, message) -> None:
    """
    Handle messages in the awaiting_image_type state.
    
    Expected: User selects an image type option.
    
    Args:
        session: The WhatsAppSession
        message: The parsed IncomingMessage
    """
    # Only accept text in this state
    if message.type != "text":
        # Re-ask Q2
        from ..constants import build_image_type_options_text
        jewellery_type_doc = get_jewellery_type_by_option(session.jewellery_type)
        options_text = build_image_type_options_text(jewellery_type_doc)
        send_text_message(
            message.sender,
            f"What kind of image are you looking for?\n\n{options_text}"
        )
        return
    
    # Parse user choice
    choice = message.text.strip().upper()
    
    if choice not in OUTPUT_MAP:
        # Invalid option - re-ask
        from ..constants import build_image_type_options_text
        jewellery_type_doc = get_jewellery_type_by_option(session.jewellery_type)
        options_text = build_image_type_options_text(jewellery_type_doc)
        send_text_message(
            message.sender,
            f"Invalid option. Please choose from:\n\n{options_text}"
        )
        return
    
    # Save image type
    session.image_type = OUTPUT_MAP[choice]
    
    # Get prompt document using category + image_type
    prompt_doc = get_prompt_document(session.category, session.image_type)
    
    if prompt_doc is None:
        # No prompt found for this combination
        send_text_message(
            message.sender,
            "This combination isn't available yet. Send STOP and try again."
        )
        return
    
    # Save prompt document
    session.prompt_document = prompt_doc
    
    # Get required dynamic fields only
    fields = session.dynamic_fields
    
    # Initialize dynamic_answers with None for all fields (required ones)
    session.dynamic_answers = {f["variable"]: None for f in fields}
    session.current_field_index = 0
    
    # Check if there are required dynamic fields
    if fields:
        session.state = "awaiting_dynamic"
        # Send first dynamic field question
        current_field = session.current_field
        send_text_message(message.sender, current_field["label"])
    else:
        # No required dynamic fields - proceed directly to generation
        # Apply defaults for any optional fields
        _apply_all_defaults(session)
        
        # Assemble final prompt
        base = prompt_doc.get("content", {}).get("text", "")
        base = base.replace("{jewellery_type}", session.jewellery_type or "")
        
        # Replace all placeholders with answers or defaults
        for variable, value in session.dynamic_answers.items():
            placeholder = f"{{{variable}}}"
            base = base.replace(placeholder, value or "")
        
        session.final_prompt = base
        session.state = "ready_for_generation"
        
        send_text_message(
            message.sender,
            "Got everything! Your image is being prepared..."
        )
        
        # Trigger generation (stub)
        from ..session import trigger_generation
        trigger_generation(session)
    
    logger.info(f"Saved image type '{session.image_type}' for {message.sender}")


def _apply_all_defaults(session) -> None:
    """
    Apply default values for all optional dynamic fields.
    
    Args:
        session: The WhatsAppSession
    """
    if session.prompt_document is None:
        return
    
    try:
        content = session.prompt_document.get("content", {})
        expected_input = content.get("expected_input_vars", {})
        all_fields = expected_input.get("dynamic_fields", [])
        
        for field in all_fields:
            variable = field.get("variable")
            required = field.get("required", True)
            
            # If not required, use default
            if not required:
                default_value = field.get("default_value", "")
                session.dynamic_answers[variable] = default_value
                
    except (AttributeError, KeyError, TypeError) as e:
        logger.error(f"Error applying default values: {str(e)}")
