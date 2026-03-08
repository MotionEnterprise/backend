"""
Library app API views for Prompt CRUD operations.
Based on the comprehensive Prompt schema from dump.json.
"""

import json
import logging
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Prompt

logger = logging.getLogger(__name__)


def parse_json_request(request):
    """Parse JSON body from request"""
    try:
        return json.loads(request.body)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return None


def success_response(data=None, message: str = "Success", status: int = 200):
    """Standard success JSON response"""
    response = {
        'success': True,
        'message': message,
    }
    if data is not None:
        response['data'] = data
    return JsonResponse(response, status=status)


def error_response(message: str, errors=None, status: int = 400):
    """Standard error JSON response"""
    response = {
        'success': False,
        'message': message,
    }
    if errors:
        response['errors'] = errors
    return JsonResponse(response, status=status)


def validate_prompt_data(data: dict, partial: bool = False) -> tuple[bool, dict]:
    """
    Validate prompt input data.
    Returns (is_valid, errors_dict)
    """
    errors = {}
    
    # Name validation (required for create)
    if not partial or 'name' in data:
        if not data.get('name'):
            errors['name'] = 'Name is required'
        elif len(data.get('name', '')) > 200:
            errors['name'] = 'Name must be less than 200 characters'
    
    # Content text validation (required for create)
    if not partial or 'content' in data:
        content = data.get('content', {})
        if not content:
            content = {'text': ''}
        if isinstance(content, dict):
            text = content.get('text', '')
        else:
            text = content
        
        if not text and not partial:
            errors['content.text'] = 'Content text is required'
    
    # Category validation
    if 'category' in data:
        category = data.get('classification', {}).get('category') if isinstance(data.get('classification'), dict) else data.get('category')
        if category and category not in Prompt.CATEGORIES:
            errors['classification.category'] = f'Category must be one of: {", ".join(Prompt.CATEGORIES)}'
    
    # Tags validation
    if 'tags' in data:
        tags = data.get('classification', {}).get('tags') if isinstance(data.get('classification'), dict) else data.get('tags')
        if tags and not isinstance(tags, list):
            errors['classification.tags'] = 'Tags must be a list'
    
    # Model compatibility validation
    if 'model_compatibility' in data:
        models = data.get('compatibility', {}).get('model_compatibility') if isinstance(data.get('compatibility'), dict) else data.get('model_compatibility')
        if models and not isinstance(models, list):
            errors['compatibility.model_compatibility'] = 'Model compatibility must be a list'
    
    return len(errors) == 0, errors


# ==================== API Views ====================

@method_decorator(csrf_exempt, name='dispatch')
class PromptListCreateView(View):
    """
    GET: List all prompts with optional filtering
    POST: Create a new prompt
    """
    
    def get(self, request):
        """Get list of prompts with optional filters"""
        try:
            # Parse query parameters
            category = request.GET.get('category')
            tag = request.GET.get('tag')
            search = request.GET.get('search')
            include_archived = request.GET.get('include_archived', 'false').lower() == 'true'
            page = int(request.GET.get('page', 1))
            limit = min(int(request.GET.get('limit', 50)), 100)
            skip = (page - 1) * limit
            
            # Build filters
            filters = {}
            
            if category:
                filters['classification.category'] = category
            
            if tag:
                filters['classification.tags'] = tag
            
            # Default: exclude archived unless explicitly requested
            if not include_archived:
                filters['lifecycle.is_archived'] = False
            
            # Search or regular find
            if search:
                prompts = Prompt.search(search, skip=skip, limit=limit)
                total = len(prompts)  # Approximate for search
            else:
                prompts = Prompt.find_all(
                    filters=filters,
                    skip=skip,
                    limit=limit,
                    sort_by='lifecycle.created_at',
                    sort_order=-1
                )
                total = Prompt.count(filters)
            
            # Serialize prompts
            data = {
                'prompts': [p.to_dict() for p in prompts],
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                    'pages': (total + limit - 1) // limit if limit > 0 else 0
                }
            }
            
            return success_response(data=data, message="Prompts retrieved successfully")
            
        except ValueError as e:
            return error_response(f"Invalid parameter: {str(e)}", status=400)
        except Exception as e:
            logger.error(f"Error listing prompts: {str(e)}")
            return error_response("Failed to retrieve prompts", status=500)
    
    def post(self, request):
        """Create a new prompt"""
        try:
            data = parse_json_request(request)
            if not data:
                return error_response("Invalid JSON body", status=400)
            
            # Validate input
            is_valid, errors = validate_prompt_data(data, partial=False)
            if not is_valid:
                return error_response("Validation failed", errors=errors, status=400)
            
            # Extract nested data
            content = data.get('content', {})
            classification = data.get('classification', {})
            compatibility = data.get('compatibility', {})
            
            # Handle both flat and nested formats
            if isinstance(content, str):
                content_text = content
                language = 'en'
            else:
                content_text = content.get('text', '')
                language = content.get('language', 'en')
            
            dynamic_fields = content.get('expected_input_vars', {}).get('dynamic_fields', []) if isinstance(content, dict) else []
            
            # Create prompt
            prompt = Prompt(
                name=data['name'],
                content_text=content_text,
                description=data.get('description', ''),
                prompt_id=data.get('prompt_id'),
                category=classification.get('category', 'text_generation') if isinstance(classification, dict) else data.get('category', 'text_generation'),
                use_case=classification.get('use_case', '') if isinstance(classification, dict) else data.get('use_case', ''),
                tags=classification.get('tags', []) if isinstance(classification, dict) else data.get('tags', []),
                allowed_industries=classification.get('allowed_industries', []) if isinstance(classification, dict) else data.get('allowed_industries', []),
                model_compatibility=compatibility.get('model_compatibility', []) if isinstance(compatibility, dict) else data.get('model_compatibility', []),
                language=language,
                dynamic_fields=dynamic_fields,
                custom_fields=data.get('custom_fields', {}),
                created_by=data.get('created_by'),
                updated_by=data.get('updated_by'),
            )
            
            # Create initial version
            prompt.create_version('1.0.0', 'Initial version', created_by=data.get('created_by'))
            
            # Save to database
            prompt.save()
            
            logger.info(f"Created prompt: {prompt.id} ({prompt.name})")
            return success_response(
                data=prompt.to_dict(),
                message="Prompt created successfully",
                status=201
            )
            
        except ValueError as e:
            return error_response(str(e), status=400)
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}")
            return error_response("Failed to create prompt", status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PromptDetailView(View):
    """
    GET: Get a single prompt by ID
    PUT/PATCH: Update a prompt
    DELETE: Delete a prompt
    """
    
    def get(self, request, prompt_id):
        """Get a single prompt by ID"""
        try:
            prompt = Prompt.find_by_id(prompt_id)
            if not prompt:
                return error_response("Prompt not found", status=404)
            
            return success_response(data=prompt.to_dict())
            
        except InvalidId:
            return error_response("Invalid prompt ID format", status=400)
        except Exception as e:
            logger.error(f"Error getting prompt: {str(e)}")
            return error_response("Failed to retrieve prompt", status=500)
    
    def put(self, request, prompt_id):
        """Update a prompt (full update)"""
        return self._update(request, prompt_id, partial=False)
    
    def patch(self, request, prompt_id):
        """Partial update a prompt"""
        return self._update(request, prompt_id, partial=True)
    
    def _update(self, request, prompt_id, partial: bool = False):
        """Update prompt logic"""
        try:
            # Check if prompt exists
            prompt = Prompt.find_by_id(prompt_id)
            if not prompt:
                return error_response("Prompt not found", status=404)
            
            # Parse request body
            data = parse_json_request(request)
            if not data:
                return error_response("Invalid JSON body", status=400)
            
            # For partial updates, validate only provided fields
            is_valid, errors = validate_prompt_data(data, partial=partial)
            if not is_valid:
                return error_response("Validation failed", errors=errors, status=400)
            
            # Extract nested data
            content = data.get('content', {})
            classification = data.get('classification', {})
            compatibility = data.get('compatibility', {})
            
            # Update core fields
            if 'name' in data:
                prompt.name = data['name']
            if 'description' in data:
                prompt.description = data['description']
            if 'prompt_id' in data:
                prompt.prompt_id = data['prompt_id']
            
            # Update content
            if content:
                if isinstance(content, dict):
                    if 'text' in content:
                        prompt.content_text = content['text']
                    if 'language' in content:
                        prompt.language = content['language']
                    if 'expected_input_vars' in content:
                        prompt.dynamic_fields = content['expected_input_vars'].get('dynamic_fields', [])
                else:
                    prompt.content_text = content
            
            # Update classification
            if classification:
                if isinstance(classification, dict):
                    if 'category' in classification:
                        prompt.category = classification['category']
                    if 'use_case' in classification:
                        prompt.use_case = classification['use_case']
                    if 'tags' in classification:
                        prompt.tags = classification['tags']
                    if 'allowed_industries' in classification:
                        prompt.allowed_industries = classification['allowed_industries']
            
            # Update compatibility
            if compatibility:
                if isinstance(compatibility, dict):
                    if 'model_compatibility' in compatibility:
                        prompt.model_compatibility = compatibility['model_compatibility']
            
            # Update custom fields
            if 'custom_fields' in data:
                prompt.custom_fields = data['custom_fields']
            
            if 'updated_by' in data:
                prompt.updated_by = data['updated_by']
            
            # Save changes
            prompt.save()
            
            logger.info(f"Updated prompt: {prompt.id}")
            return success_response(data=prompt.to_dict(), message="Prompt updated successfully")
            
        except InvalidId:
            return error_response("Invalid prompt ID format", status=400)
        except ValueError as e:
            return error_response(str(e), status=400)
        except Exception as e:
            logger.error(f"Error updating prompt: {str(e)}")
            return error_response("Failed to update prompt", status=500)
    
    def delete(self, request, prompt_id):
        """Delete a prompt"""
        try:
            prompt = Prompt.find_by_id(prompt_id)
            if not prompt:
                return error_response("Prompt not found", status=404)
            
            success = prompt.delete()
            if success:
                logger.info(f"Deleted prompt: {prompt_id}")
                return success_response(message="Prompt deleted successfully")
            else:
                return error_response("Failed to delete prompt", status=500)
                
        except InvalidId:
            return error_response("Invalid prompt ID format", status=400)
        except Exception as e:
            logger.error(f"Error deleting prompt: {str(e)}")
            return error_response("Failed to delete prompt", status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PromptByNameView(View):
    """
    GET/PUT/DELETE: Access prompt by name instead of ID
    """
    
    def get(self, request, name):
        """Get prompt by name"""
        try:
            prompt = Prompt.find_by_name(name)
            if not prompt:
                return error_response("Prompt not found", status=404)
            return success_response(data=prompt.to_dict())
        except Exception as e:
            logger.error(f"Error getting prompt by name: {str(e)}")
            return error_response("Failed to retrieve prompt", status=500)
    
    def put(self, request, name):
        """Update prompt by name"""
        try:
            prompt = Prompt.find_by_name(name)
            if not prompt:
                return error_response("Prompt not found", status=404)
            
            # Reuse the detail view logic with the found prompt
            from django.test import RequestFactory
            factory = RequestFactory()
            fake_request = factory.put(request.body, content_type='application/json')
            fake_request.body = request.body
            
            # Parse and update
            data = parse_json_request(request)
            if not data:
                return error_response("Invalid JSON body", status=400)
            
            # Apply updates similar to _update
            if 'name' in data:
                prompt.name = data['name']
            if 'description' in data:
                prompt.description = data['description']
            
            content = data.get('content', {})
            if content and isinstance(content, dict):
                if 'text' in content:
                    prompt.content_text = content['text']
            
            classification = data.get('classification', {})
            if classification and isinstance(classification, dict):
                if 'category' in classification:
                    prompt.category = classification['category']
                if 'tags' in classification:
                    prompt.tags = classification['tags']
            
            prompt.save()
            return success_response(data=prompt.to_dict(), message="Prompt updated successfully")
            
        except Exception as e:
            logger.error(f"Error updating prompt by name: {str(e)}")
            return error_response("Failed to update prompt", status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PromptCategoryView(View):
    """
    GET: Get all categories
    """
    
    def get(self, request):
        """Get all valid categories"""
        try:
            categories = Prompt.get_categories()
            return success_response(data={'categories': categories})
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return error_response("Failed to retrieve categories", status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PromptTagsView(View):
    """
    GET: Get all tags
    """
    
    def get(self, request):
        """Get all unique tags from prompts"""
        try:
            tags = Prompt.get_all_tags()
            return success_response(data={'tags': tags})
        except Exception as e:
            logger.error(f"Error getting tags: {str(e)}")
            return error_response("Failed to retrieve tags", status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PromptArchiveView(View):
    """
    POST: Archive/unarchive a prompt
    """
    
    def post(self, request, prompt_id):
        """Archive or unarchive a prompt"""
        try:
            prompt = Prompt.find_by_id(prompt_id)
            if not prompt:
                return error_response("Prompt not found", status=404)
            
            data = parse_json_request(request)
            if not data:
                return error_response("Invalid JSON body", status=400)
            
            action = data.get('action', 'archive')
            
            if action == 'archive':
                prompt.archive()
                message = "Prompt archived successfully"
            elif action == 'unarchive':
                prompt.unarchive()
                message = "Prompt unarchived successfully"
            else:
                return error_response("Invalid action. Use 'archive' or 'unarchive'", status=400)
            
            prompt.save()
            return success_response(data=prompt.to_dict(), message=message)
            
        except Exception as e:
            logger.error(f"Error archiving prompt: {str(e)}")
            return error_response("Failed to archive prompt", status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PromptVersionView(View):
    """
    POST: Create a new version of a prompt
    GET: Get version history
    """
    
    def get(self, request, prompt_id):
        """Get version history of a prompt"""
        try:
            prompt = Prompt.find_by_id(prompt_id)
            if not prompt:
                return error_response("Prompt not found", status=404)
            
            return success_response(data={
                'versions': prompt.versions,
                'active_version': prompt.active_version
            })
            
        except Exception as e:
            logger.error(f"Error getting versions: {str(e)}")
            return error_response("Failed to retrieve versions", status=500)
    
    def post(self, request, prompt_id):
        """Create a new version of a prompt"""
        try:
            prompt = Prompt.find_by_id(prompt_id)
            if not prompt:
                return error_response("Prompt not found", status=404)
            
            data = parse_json_request(request)
            if not data:
                return error_response("Invalid JSON body", status=400)
            
            version = data.get('version')
            if not version:
                return error_response("Version number is required", status=400)
            
            changelog = data.get('changelog', '')
            
            # Update content to new version
            if 'content_text' in data:
                prompt.content_text = data['content_text']
            
            prompt.create_version(version, changelog, created_by=data.get('created_by'))
            prompt.save()
            
            return success_response(data=prompt.to_dict(), message=f"Version {version} created successfully")
            
        except Exception as e:
            logger.error(f"Error creating version: {str(e)}")
            return error_response("Failed to create version", status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PromptUsageView(View):
    """
    POST: Record usage of a prompt
    """
    
    def post(self, request, prompt_id):
        """Record usage of a prompt"""
        try:
            prompt = Prompt.find_by_id(prompt_id)
            if not prompt:
                return error_response("Prompt not found", status=404)
            
            data = parse_json_request(request)
            if not data:
                return error_response("Invalid JSON body", status=400)
            
            generation_time = data.get('generation_time', 0.0)
            cost = data.get('cost', 0.0)
            
            prompt.increment_usage(generation_time, cost)
            prompt.save()
            
            return success_response(data=prompt.to_dict(), message="Usage recorded successfully")
            
        except Exception as e:
            logger.error(f"Error recording usage: {str(e)}")
            return error_response("Failed to record usage", status=500)
