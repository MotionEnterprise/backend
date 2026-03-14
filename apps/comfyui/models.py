"""
Django models for ComfyUI job tracking.

Tracks the lifecycle of ComfyUI generation jobs in SQLite.
"""

import uuid
from django.db import models


class ComfyJob(models.Model):
    """
    Tracks the lifecycle of a single ComfyUI generation job.
    Stored in SQLite (same as the rest of your Django models).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"

    # Primary key — UUID used as Channels group name too
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Link to your existing Generation App
    # ForeignKey to generation.Recipe or generation.Job — adjust to your model name
    generation_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    # ComfyUI tracking
    prompt_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    client_id = models.CharField(max_length=255, null=True, blank=True)

    # State
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(null=True, blank=True)

    # Results — stored as JSON list of {filename, file_path, bucket_name, file_type, content_type}
    output_files = models.JSONField(default=list)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['generation_id']),
            models.Index(fields=['prompt_id']),
        ]

    def __str__(self):
        return f"ComfyJob({self.id}, {self.status})"
