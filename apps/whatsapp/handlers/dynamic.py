"""
Dynamic Field Handler

Handles dynamic questions from the prompt document.
"""

import logging

from ..evolution import send_text_message
from ..session import trigger_generation

logger = logging.getLogger(__name__)


def handle_dynamic(session, message) -> None:
    """
    Handle messages in the awaiting_dynamic state.
    
    Expected: User answers dynamic questions from prompt document.
    
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
    
    # All answers collected - assemble final prompt
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
    
    logger.info(f"Completed dynamic fields for {message.sender}")
