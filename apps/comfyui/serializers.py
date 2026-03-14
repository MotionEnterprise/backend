"""
DRF Serializers for ComfyUI integration.

Provides serialization for job submission, status responses,
and file upload handling.
"""

from rest_framework import serializers

from .models import ComfyJob


class ComfyJobSerializer(serializers.ModelSerializer):
    """Serializer for ComfyJob model."""
    
    class Meta:
        model = ComfyJob
        fields = [
            "id",
            "generation_id",
            "prompt_id",
            "status",
            "output_files",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WorkflowSubmitSerializer(serializers.Serializer):
    """Serializer for workflow submission requests."""
    
    workflow = serializers.DictField(
        help_text="The ComfyUI workflow API JSON dict"
    )
    generation_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional link to a Generation App recipe/job"
    )


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload requests."""
    
    file = serializers.FileField(
        help_text="The file to upload (image or video)"
    )
    folder_type = serializers.ChoiceField(
        choices=["input", "output", "temp"],
        default="input",
        help_text="ComfyUI folder type for the upload"
    )
    overwrite = serializers.BooleanField(
        default=True,
        help_text="Whether to overwrite existing file with same name"
    )


class JobStatusSerializer(serializers.Serializer):
    """Serializer for job status response."""
    
    job_id = serializers.UUIDField()
    status = serializers.CharField()
    prompt_id = serializers.CharField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)
    output_files = serializers.ListField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class JobOutputsSerializer(serializers.Serializer):
    """Serializer for job outputs response."""
    
    job_id = serializers.UUIDField()
    files = serializers.ListField()
