"""
REDO Handler

Handles the REDO flow when user wants to regenerate with same or different settings.
"""

import logging

from ..evolution import send_text_message
from ..session import trigger_generation, load_session, save_session

logger = logging.getLogger(__name__)


# Map option letters to redo choices
REDO_OPTIONS = {
    "A": "same",
    "B": "change",
}


def handle_redo_choice(session, message) -> any:
    """
    Handle user's choice when they select REDO option.
    
    Expected: User selects A (same config) or B (change settings)
    
    Args:
        session: The WhatsAppSession (old completed session)
        message: The parsed IncomingMessage
        
    Returns:
        The new session to be used (for routing to save)
    """
    # Only accept text
    if message.type != "text":
        # Re-ask the choice
        send_redo_choice_message(message.sender)
        return session
    
    # Parse choice
    choice = message.text.strip().upper()
    
    if choice not in REDO_OPTIONS:
        # Invalid option - re-ask
        send_redo_choice_message(message.sender)
        return session
    
    user_choice = REDO_OPTIONS[choice]
    
    # Create new session document (this deactivates old sessions)
    new_session = load_session(session.whatsapp_number, create_new=True)
    
    # Copy data from old session
    new_session.image = session.image
    new_session.jewellery_type = session.jewellery_type
    new_session.category = session.category
    new_session.image_type = session.image_type
    new_session.prompt_document = session.prompt_document
    
    if user_choice == "same":
        # Keep same dynamic answers - just regenerate
        # Copy all dynamic answers
        new_session.dynamic_answers = dict(session.dynamic_answers) if session.dynamic_answers else {}
        new_session.current_field_index = 0  # Reset to run through again
        
        # Set state to generating and trigger
        new_session.state = "generating"
        
        # Save the new session
        save_session(new_session)
        
        send_text_message(
            message.sender,
            "Regenerating with your same settings..."
        )
        
        # Trigger generation (stub)
        trigger_generation(new_session)
        
        logger.info(f"REDO with same settings for {message.sender}")
        
    else:
        # Change settings - ask dynamic questions again
        # Clear dynamic answers to re-ask
        new_session.dynamic_answers = {}
        new_session.current_field_index = 0
        new_session.state = "awaiting_dynamic"
        
        # Save the new session
        save_session(new_session)
        
        # Get first dynamic field
        fields = new_session.dynamic_fields
        if fields:
            current_field = new_session.current_field
            send_text_message(message.sender, current_field["label"])
        else:
            # No dynamic fields - proceed to generation
            new_session.state = "generating"
            save_session(new_session)
            send_text_message(
                message.sender,
                "Got everything! Your image is being prepared..."
            )
            trigger_generation(new_session)
        
        logger.info(f"REDO with changed settings for {message.sender}")
    
    # Return the NEW session so views.py saves it
    return new_session


def send_redo_choice_message(whatsapp_number: str) -> None:
    """
    Send the REDO choice message to user.
    
    Args:
        whatsapp_number: The user's WhatsApp number
    """
    message = (
        "How would you like to regenerate?\n\n"
        "A. Keep same settings (same jewellery type, image type, and answers)\n"
        "B. Change settings (keep image, but answer questions again)"
    )
    send_text_message(whatsapp_number, message)
