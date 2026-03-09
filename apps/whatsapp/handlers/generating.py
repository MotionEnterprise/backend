"""
Generating State Handler

Handles messages while image generation is in progress.
"""

from ..evolution import send_text_message


def handle_generating(session, message) -> None:
    """
    Handle messages in the generating state.
    
    Expected: User may ask about status or cancel.
    
    Args:
        session: The WhatsAppSession
        message: The parsed IncomingMessage
    """
    # Inform user that generation is in progress
    send_text_message(
        message.sender,
        "Still working on your image, please wait...\n"
        "Reply STOP to cancel."
    )
