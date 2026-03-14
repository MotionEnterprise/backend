"""
Generating State Handler

Handles messages while image generation is in progress.
"""

from ..evolution import send_text_message


def handle_generating(session, message) -> None:
    """
    Handle messages in the generating state.
    
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


def send_generation_complete_message(whatsapp_number: str) -> None:
    """
    Send confirmation message after generation is complete.
    
    This is called when the generated image is ready to be sent.
    
    Args:
        whatsapp_number: The user's WhatsApp number
    """
    message = (
        "Your image is ready!\n\n"
        "Not satisfied? Send REDO to try again.\n"
        "Happy? Send a new image to start fresh."
    )
    send_text_message(whatsapp_number, message)
