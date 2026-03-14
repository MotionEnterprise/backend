"""
WhatsApp Session Models

MongoEngine document models for WhatsApp session management.
"""

from datetime import datetime
from mongoengine import (
    Document,
    EmbeddedDocument,
    StringField,
    BooleanField,
    DateTimeField,
    IntField,
    DictField,
    EmbeddedDocumentField,
    ObjectIdField,
)


class ImageMeta(EmbeddedDocument):
    """
    Embedded document for storing image metadata.
    Uses Supabase storage.
    """
    # Supabase file path (e.g., "phonenumber/20240315_123045_original.jpg")
    file_path = StringField(required=True)
    # Bucket name: "uploaded-media" for user uploads, "generated-media" for AI output
    bucket_name = StringField(default="uploaded-media")
    mimetype = StringField(default="image/jpeg")
    uploaded_at = DateTimeField(default=datetime.utcnow)


class GenerationMeta(EmbeddedDocument):
    """
    Embedded document for tracking ComfyUI generation state.
    Stored inside WhatsAppSession to keep everything together in MongoDB.
    """
    comfy_prompt_id = StringField(null=True, default=None)
    generation_status = StringField(
        choices=["pending", "running", "completed", "failed"],
        default="pending",
    )
    generated_image = EmbeddedDocumentField(ImageMeta, null=True, default=None)
    error_message = StringField(null=True, default=None)
    started_at = DateTimeField(null=True, default=None)
    completed_at = DateTimeField(null=True, default=None)


class WhatsAppSession(Document):
    """
    Document for storing WhatsApp user session state.
    Each session (flow) creates a new document.
    activeSession = true indicates the current active flow.
    """
    meta = {
        'collection': 'whatsapp_sessions',
        'db_alias': 'dev',
        'indexes': [
            {'fields': ['whatsapp_number', 'activeSession']},
            'state',
            'last_active',
        ]
    }

    # Identification
    whatsapp_number = StringField(required=True)
    activeSession = BooleanField(default=True)  # true for current, false for completed
    
    # Image
    image = EmbeddedDocumentField(ImageMeta, null=True, default=None)
    pending_image = EmbeddedDocumentField(ImageMeta, null=True, default=None)
    
    # Jewellery and prompt fields
    jewellery_type = StringField(null=True, default=None)
    category = StringField(null=True, default=None)
    image_type = StringField(null=True, default=None)
    prompt_document = DictField(null=True, default=None)
    
    # Dynamic fields tracking
    current_field_index = IntField(default=0)
    dynamic_answers = DictField(default=dict)
    
    # Final prompt
    final_prompt = StringField(null=True, default=None)
    
    # Retry and reminder tracking
    retry_count = IntField(default=0)
    reminder_sent = BooleanField(default=False)
    
    # ComfyUI generation tracking
    generation = EmbeddedDocumentField(GenerationMeta, null=True, default=None)
    
    # State
    state = StringField(required=True, default="idle")
    
    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)
    last_active = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField(null=True, default=None)

    def reset(self):
        """
        Reset all fields to default except whatsapp_number and created_at.
        Calls touch() to update last_active.
        """
        self.state = "idle"
        self.image = None
        self.pending_image = None
        self.jewellery_type = None
        self.category = None
        self.image_type = None
        self.prompt_document = None
        self.current_field_index = 0
        self.dynamic_answers = {}
        self.final_prompt = None
        self.retry_count = 0
        self.reminder_sent = False
        self.generation = None
        self.touch()

    def touch(self):
        """
        Update last_active timestamp to current UTC time.
        """
        self.last_active = datetime.utcnow()

    @property
    def dynamic_fields(self):
        """
        Get sorted list of dynamic fields from prompt_document where required=True.
        
        Returns:
            list: Sorted list of required dynamic field dicts
        """
        if self.prompt_document is None:
            return []
        
        try:
            content = self.prompt_document.get("content", {})
            expected_input = content.get("expected_input_vars", {})
            fields = expected_input.get("dynamic_fields", [])
            # Filter to only required fields and sort by order
            required_fields = [f for f in fields if f.get("required", True)]
            return sorted(required_fields, key=lambda x: x.get("order", 0))
        except (AttributeError, KeyError, TypeError):
            return []

    @property
    def current_field(self):
        """
        Get the current dynamic field being asked.
        
        Returns:
            dict or None: Current field dict or None if index out of range
        """
        fields = self.dynamic_fields
        if 0 <= self.current_field_index < len(fields):
            return fields[self.current_field_index]
        return None

    @property
    def all_answers_collected(self):
        """
        Check if all dynamic answers have been collected.
        
        Returns:
            bool: True if current_field_index >= len(dynamic_fields)
        """
        fields = self.dynamic_fields
        return self.current_field_index >= len(fields)

    def __str__(self):
        return f"<WhatsAppSession {self.whatsapp_number} [{self.state}] active={self.activeSession}>"
