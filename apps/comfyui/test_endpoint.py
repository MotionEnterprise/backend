"""
Test endpoint for ComfyUI workflow execution.

This endpoint simulates the complete flow:
1. Get prompt from MongoDB
2. Fill in dynamic fields
3. Upload test image to ComfyUI
4. Submit workflow
5. Wait for completion
6. Download and save to Supabase
7. Return full details with Supabase URL

Endpoint: POST /comfyui/test/run/
"""

import asyncio
import logging
import os
from pathlib import Path

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.library.models import Prompt
from apps.media.supabase_storage import save_generated_image, GENERATED_MEDIA_BUCKET
from apps.whatsapp.workflow_builder import build_workflow

from .client import (
    upload_file,
    make_client_id,
    submit_workflow,
    stream_progress,
    get_history,
    download_output_file,
)
from .errors import ComfyConnectionError, ComfyExecutionError, ComfyTimeoutError

logger = logging.getLogger(__name__)

# Path to test image
TEST_IMAGE_PATH = Path(__file__).parent.parent.parent / "test" / "images" / "image.png"


class ComfyUITestRunView(APIView):
    """
    POST /comfyui/test/run/
    
    Test endpoint that runs the complete ComfyUI flow:
    - Fetches prompt from MongoDB (prompt_id: hand-human)
    - Fills in dynamic fields (skin_tone, body_part)
    - Uploads test image to ComfyUI
    - Submits workflow
    - Waits for completion
    - Saves output to Supabase
    - Returns full details
    
    Request body (all optional - uses defaults if not provided):
    {
        "prompt_id": "hand-human",  # default
        "skin_tone": "fair",         # dynamic field value
        "body_part": "finger",       # dynamic field value
    }
    
    Response:
    {
        "success": true,
        "prompt_id": "hand-human",
        "filled_prompt": "...",
        "uploaded_filename": "image.png",
        "prompt_id_comfy": "...",
        "client_id": "...",
        "output_files": [...],
        "supabase_urls": [...]
    }
    """
    
    def post(self, request):
        # Get parameters from request or use defaults
        prompt_id = request.data.get("prompt_id", "hand-human")
        skin_tone = request.data.get("skin_tone", "dark")
        body_part = request.data.get("body_part", "finger")
        
        logger.info(f"[TestRun] Starting test run for prompt_id={prompt_id}")
        
        try:
            # Step 1: Get prompt from MongoDB
            prompt = Prompt.find_by_prompt_id(prompt_id)
            if not prompt:
                return Response(
                    {"error": f"Prompt not found: {prompt_id}"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get the text content and fill in dynamic fields
            base_prompt = prompt.content_text
            
            # Fill in dynamic fields
            filled_prompt = base_prompt
            filled_prompt = filled_prompt.replace("{skin_tone}", skin_tone)
            filled_prompt = filled_prompt.replace("{body_part}", body_part)
            filled_prompt = filled_prompt.replace("{pose_style}", "relaxed natural pose")
            filled_prompt = filled_prompt.replace("{lighting_style}", "natural soft")
            filled_prompt = filled_prompt.replace("{background_style}", "blurred neutral")
            filled_prompt = filled_prompt.replace("{shot_type}", "macro close-up")
            
            logger.info(f"[TestRun] Filled prompt: {filled_prompt[:100]}...")
            
            # Step 2: Upload test image to ComfyUI
            if not TEST_IMAGE_PATH.exists():
                return Response(
                    {"error": f"Test image not found: {TEST_IMAGE_PATH}"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            with open(TEST_IMAGE_PATH, "rb") as f:
                image_bytes = f.read()
            
            upload_result = asyncio.run(upload_file(
                file_bytes=image_bytes,
                filename="test_image.png",
                content_type="image/png",
                folder_type="input",
                overwrite=True,
            ))
            
            uploaded_filename = upload_result["name"]
            logger.info(f"[TestRun] Uploaded image: {uploaded_filename}")
            
            # Step 3: Build workflow
            workflow = build_workflow(
                comfyui_filename=uploaded_filename,
                prompt=filled_prompt
            )
            
            # Step 4: Submit workflow
            client_id = make_client_id()
            comfy_prompt_id = asyncio.run(submit_workflow(workflow, client_id))
            logger.info(f"[TestRun] Submitted workflow, prompt_id={comfy_prompt_id}")
            
            # Step 5: Wait for completion via WebSocket
            output_files = []
            supabase_urls = []
            
            async def wait_for_completion():
                nonlocal output_files, supabase_urls
                async for event in stream_progress(client_id, comfy_prompt_id):
                    logger.info(f"[TestRun] Event: {event.get('type')}")
                    if event.get("done"):
                        break
                
                # Get history to find output files
                history = await get_history(comfy_prompt_id)
                
                # Extract output files
                outputs = history.get(comfy_prompt_id, {}).get("outputs", {})
                for node_id, node_output in outputs.items():
                    for img in node_output.get("images", []):
                        filename = img["filename"]
                        subfolder = img.get("subfolder", "")
                        
                        # Download from ComfyUI
                        file_bytes = await download_output_file(
                            filename=filename,
                            subfolder=subfolder,
                            file_type="output"
                        )
                        
                        # Save to Supabase
                        supabase_path = save_generated_image(
                            file_bytes=file_bytes,
                            phone_number=f"test_{prompt_id}",
                            content_type="image/png"
                        )
                        
                        # Build full URL
                        from django.conf import settings
                        supabase_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{GENERATED_MEDIA_BUCKET}/{supabase_path}"
                        
                        output_files.append({
                            "filename": filename,
                            "subfolder": subfolder,
                            "node_id": node_id,
                            "supabase_path": supabase_path,
                            "supabase_url": supabase_url
                        })
                        supabase_urls.append(supabase_url)
            
            asyncio.run(wait_for_completion())
            
            # Return full details
            return Response({
                "success": True,
                "prompt_id": prompt_id,
                "filled_prompt": filled_prompt,
                "dynamic_fields": {
                    "skin_tone": skin_tone,
                    "body_part": body_part,
                    "pose_style": "relaxed natural pose",
                    "lighting_style": "natural soft",
                    "background_style": "blurred neutral",
                    "shot_type": "macro close-up"
                },
                "uploaded_filename": uploaded_filename,
                "client_id": client_id,
                "prompt_id_comfy": comfy_prompt_id,
                "output_count": len(output_files),
                "output_files": output_files,
                "supabase_urls": supabase_urls
            })
            
        except ComfyConnectionError as e:
            logger.error(f"[TestRun] ComfyConnectionError: {e}")
            return Response(
                {"error": "ComfyUI connection failed", "detail": str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except ComfyExecutionError as e:
            logger.error(f"[TestRun] ComfyExecutionError: {e}")
            return Response(
                {"error": "ComfyUI execution failed", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except ComfyTimeoutError as e:
            logger.error(f"[TestRun] ComfyTimeoutError: {e}")
            return Response(
                {"error": "ComfyUI timeout", "detail": str(e)},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except Exception as e:
            logger.exception(f"[TestRun] Unexpected error: {e}")
            return Response(
                {"error": "Unexpected error", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
