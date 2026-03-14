"""
Jewellery Type Handler

Handles the jewellery type selection question (Q1).
"""

import logging

from ..evolution import send_text_message
from ..session import get_jewellery_type_by_option, get_all_jewellery_types
from ..constants import build_jewellery_options_text, build_image_type_options_text

logger = logging.getLogger(__name__)


def handle_jewellery_type(session, message) -> None:
    """
    Handle messages in the awaiting_jewellery_type state.
    
    Expected: User selects a jewellery type option.
    
    Args:
        session: The WhatsAppSession
        message: The parsed IncomingMessage
    """
    # Only accept text in this state
    if message.type != "text":
        # Re-ask Q1
        jewellery_types = get_all_jewellery_types()
        options_text = build_jewellery_options_text()
        send_text_message(
            message.sender,
            f"What type of jewellery is this?\n\n{options_text}"
        )
        return
    
    # Parse user choice
    choice = message.text.strip()
    jewellery_type_doc = get_jewellery_type_by_option(choice)
    
    if not jewellery_type_doc:
        # Invalid option - re-ask
        options_text = build_jewellery_options_text()
        send_text_message(
            message.sender,
            f"Invalid option. Please choose from:\n\n{options_text}"
        )
        return
    
    # Save jewellery type and category
    session.jewellery_type = jewellery_type_doc["id"]
    session.category = jewellery_type_doc["category"]
    session.state = "awaiting_image_type"
    
    # Get human_part for Q2
    human_part = jewellery_type_doc.get("human_part", "")
    
    # Build Q2 with all three options
    if human_part:
        q2_text = (
            "What kind of image are you looking for?\n\n"
            "A. Plain background\n"
            "B. On human ({human_part})\n"
            "C. Aesthetic background"
        ).format(human_part=human_part)
    else:
        q2_text = build_image_type_options_text(jewellery_type_doc)
    
    send_text_message(message.sender, q2_text)
    
    logger.info(f"Saved jewellery type '{jewellery_type_doc['id']}' for {message.sender}")
