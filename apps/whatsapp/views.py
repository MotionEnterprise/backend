"""
WhatsApp Webhook Views

Django REST Framework views for handling WhatsApp webhook events.
"""

import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .parser import parse_evolution_payload
from .session import load_session, save_session
from .interrupts import handle_interrupt
from .router import route

logger = logging.getLogger(__name__)


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
        2. Load session
        3. Handle interrupts
        4. Route to appropriate handler
        5. Save session
        6. Return 200
        """
        try:
            # Step 1: Parse payload
            message = parse_evolution_payload(request.data)
            
            # If no valid message, return 200 (Evolution API expects acknowledgment)
            if message is None:
                return Response(status=200)
            
            logger.info(f"Received {message.type} from {message.sender}")
            
            # Step 2: Load session (don't create new here, let handlers do it)
            session = load_session(message.sender)
            
            # Step 3: Handle interrupts (STOP, REDO, new image)
            if handle_interrupt(session, message):
                save_session(session)
                return Response(status=200)
            
            # Step 4: Route to appropriate handler
            # This may create a NEW session for fresh flows
            session = route(session, message)
            
            # Step 5: Save session (the one returned from route)
            if session:
                save_session(session)
            
        except Exception as e:
            # Log error but still return 200 to prevent webhook retries
            logger.error(f"Webhook error: {str(e)}", exc_info=True)
        
        return Response(status=200)
