"""
Image Type Handler

Handles the image type selection question (Q2).
"""

import logging

from ..evolution import send_text_message
from ..session import get_prompt_document, get_jewellery_type_by_option
from ..constants import build_image_type_options_text

logger = logging.getLogger(__name__)


# Map option letters to image_type values
OUTPUT_MAP = {
    "A": "plain",
    "B": "human",
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
    
    # Save prompt document and initialize dynamic fields
    session.prompt_document = prompt_doc
    fields = session.dynamic_fields
    session.dynamic_answers = {f["variable"]: None for f in fields}
    session.current_field_index = 0
    session.state = "awaiting_dynamic"
    
    # Send first dynamic field question if available
    if fields:
        current_field = session.current_field
        send_text_message(message.sender, current_field["label"])
    else:
        # No dynamic fields - proceed directly to generation
        session.state = "ready_for_generation"
        session.final_prompt = prompt_doc.get("content", {}).get("text", "")
        send_text_message(
            message.sender,
            "Got everything! Your image is being prepared..."
        )
        # Trigger generation (stub)
        from ..session import trigger_generation
        trigger_generation(session)
    
    logger.info(f"Saved image type '{session.image_type}' for {message.sender}")
