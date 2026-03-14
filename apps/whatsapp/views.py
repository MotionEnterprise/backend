"""
WhatsApp Webhook Views

Django REST Framework views for handling WhatsApp webhook events.
"""

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .parser import parse_evolution_payload
from .session import load_session, save_session, _get_dev_db
from .interrupts import handle_interrupt
from .router import route

logger = logging.getLogger(__name__)


def _find_session_for_interrupt(whatsapp_number: str):
    """
    Find the appropriate session for interrupt handling.
    
    Priority:
    1. Active session (activeSession=True)
    2. Most recent completed/generating session if no active session
    
    Returns:
        WhatsAppSession or None
    """
    from .models import WhatsAppSession
    
    # Ensure database connection is initialized
    _get_dev_db()
    
    # First try to find active session
    session = WhatsAppSession.objects(
        whatsapp_number=whatsapp_number,
        activeSession=True
    ).first()
    
    if session:
        return session
    
    # No active session - find most recent completed or generating session
    session = WhatsAppSession.objects(
        whatsapp_number=whatsapp_number
    ).order_by('-created_at').first()
    
    return session


class WhatsAppWebhookView(APIView):
    """
    Webhook view for receiving Evolution API events.
    
    Accepts POST requests from Evolution API webhook.
    """
    
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Handle incoming webhook events from Evolution API.
        
        Sequence:
        1. Parse payload
        2. Find existing session (don't create new for interrupts)
        3. Handle interrupts (STOP, REDO, new image)
        4. If no interrupt, use the found session or create new for flow
        5. Route to appropriate handler
        6. Save session
        7. Return 200
        """
        try:
            # Step 1: Parse payload
            message = parse_evolution_payload(request.data)
            print(f'request headers - ', request.headers)
            
            # If no valid message, return 200 (Evolution API expects acknowledgment)
            if message is None:
                return Response(status=200)
            
            logger.info(f"Received {message.type} from {message.sender}")
            
            # Step 2: Find existing session (for interrupt handling)
            # Don't create new session yet - let interrupts handle finding existing sessions
            existing_session = _find_session_for_interrupt(message.sender)
            
            # Step 3: Handle interrupts (STOP, REDO, new image)
            # Pass the message so interrupt handler can find the right session
            if existing_session and handle_interrupt(existing_session, message):
                save_session(existing_session)
                return Response(status=200)
            
            # Step 4: For new flows, use existing session or create new if needed
            # If we found an existing session, use it (could be completed, idle, etc.)
            # Only create new if no existing session found
            if existing_session:
                session = existing_session
            else:
                session = load_session(message.sender)
            
            # Step 5: Route to appropriate handler
            # This may create a NEW session for fresh flows
            session = route(session, message)
            
            # Step 6: Save session (the one returned from route)
            if session:
                save_session(session)
            
        except Exception as e:
            # Log error but still return 200 to prevent webhook retries
            logger.error(f"Webhook error: {str(e)}", exc_info=True)
        
        return Response(status=200)
