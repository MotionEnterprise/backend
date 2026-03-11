"""
Dynamic Field Handler

Handles dynamic questions from the prompt document.
"""

import logging

from ..evolution import send_text_message
from ..session import trigger_generation, complete_session

logger = logging.getLogger(__name__)


def handle_dynamic(session, message) -> None:
    """
    Handle messages in the awaiting_dynamic state.
    
    Expected: User answers dynamic questions from prompt document.
    Only required fields (required=True) are asked.
    
    Args:
        session: The WhatsAppSession
        message: The parsed IncomingMessage
    """
    # Only accept text in this state
    if message.type != "text":
        # Re-ask current field
        current_field = session.current_field
        if current_field:
            send_text_message(message.sender, current_field["label"])
        return
    
    # Get current field being asked
    current_field = session.current_field
    if current_field is None:
        logger.warning(f"No current field for {message.sender}, session may be in invalid state")
        return
    
    # Save the answer
    current_key = current_field["variable"]
    session.dynamic_answers[current_key] = message.text.strip()
    session.current_field_index += 1
    
    # Check if more answers are needed
    if not session.all_answers_collected:
        # Send next question
        next_field = session.current_field
        send_text_message(message.sender, next_field["label"])
        return
    
    # All answers collected - apply defaults for optional fields
    _apply_default_values(session)
    
    # Assemble final prompt
    base = session.prompt_document.get("content", {}).get("text", "")
    
    # Replace placeholders
    base = base.replace("{jewellery_type}", session.jewellery_type or "")
    
    for variable, value in session.dynamic_answers.items():
        placeholder = f"{{{variable}}}"
        base = base.replace(placeholder, value or "")
    
    session.final_prompt = base
    session.state = "ready_for_generation"
    
    # Send confirmation
    send_text_message(
        message.sender,
        "Got everything! Your image is being prepared..."
    )
    
    # Trigger generation (stub)
    trigger_generation(session)
    
    # Complete the session (sets activeSession=False)
    # complete_session(session)
    
    logger.info(f"Completed dynamic fields for {message.sender}")


def _apply_default_values(session) -> None:
    """
    Apply default values for optional dynamic fields.
    
    Args:
        session: The WhatsAppSession
    """
    if session.prompt_document is None:
        return
    
    try:
        content = session.prompt_document.get("content", {})
        expected_input = content.get("expected_input_vars", {})
        all_fields = expected_input.get("dynamic_fields", [])
        
        # Get all field variables that were NOT answered (not in dynamic_answers)
        answered_keys = set(session.dynamic_answers.keys())
        
        for field in all_fields:
            variable = field.get("variable")
            required = field.get("required", True)
            
            # If not required and not answered, use default
            if not required and variable not in answered_keys:
                default_value = field.get("default_value", "")
                session.dynamic_answers[variable] = default_value
                logger.debug(f"Applied default '{default_value}' for optional field '{variable}'")
                
    except (AttributeError, KeyError, TypeError) as e:
        logger.error(f"Error applying default values: {str(e)}")
