"""
Celery tasks for the Generation App.

This module provides integration with ComfyUI for image generation.
"""

import logging

from apps.comfyui.tasks import run_comfyui_workflow
from apps.comfyui.models import ComfyJob

logger = logging.getLogger(__name__)


def trigger_comfyui_generation(recipe, workflow_dict):
    """
    Trigger a ComfyUI generation job for a Recipe.
    
    Called from the existing generation logic when a Recipe is ready for generation.
    This function creates a ComfyJob record and queues the Celery task to execute
    the workflow on ComfyUI (RunPod).
    
    Args:
        recipe: The Recipe instance (MongoDB document) to generate content for
        workflow_dict: The ComfyUI workflow JSON dict (workflow_api.json format)
                      with any injected input filenames
    
    Returns:
        ComfyJob: The created ComfyJob instance
    
    Flow:
        1. Create ComfyJob record with generation_id (Recipe.id)
        2. Queue the Celery task run_comfyui_workflow
        3. Return the job for tracking
    
    Example:
        # In your generation logic when a Recipe is ready:
        workflow = load_workflow_template(recipe.template_id)
        # Inject any uploaded input filenames if needed:
        # workflow["1"]["inputs"]["image"] = uploaded_filename
        job = trigger_comfyui_generation(recipe, workflow)
    """
    logger.info(f"[Generation] Triggering ComfyUI generation for Recipe {recipe.id}")
    
    # Validate inputs
    if not recipe or not hasattr(recipe, 'id'):
        raise ValueError("Invalid recipe: must be a Recipe instance with an id")
    
    if not workflow_dict:
        raise ValueError("Invalid workflow_dict: must be a non-empty dict")
    
    # Create ComfyJob record - links to the Generation App via generation_id
    job = ComfyJob.objects.create(
        generation_id=str(recipe.id),
        status=ComfyJob.Status.PENDING,
    )
    
    logger.info(f"[Generation] Created ComfyJob {job.id} for Recipe {recipe.id}")
    
    # Queue the Celery task - returns immediately, doesn't wait for completion
    run_comfyui_workflow.delay(
        job_id=str(job.id),
        workflow=workflow_dict,
    )
    
    logger.info(f"[Generation] Queued ComfyUI workflow for job {job.id}")
    
    return job
