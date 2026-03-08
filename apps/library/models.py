"""
Library app models using pymongo for MongoDB database operations.
Based on the Prompt schema from dump.json with full versioning support.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from bson import ObjectId
from core.database import get_library_collection


class PromptVersion:
    """Represents a single version of a prompt"""
    
    def __init__(
        self,
        version: str,
        content_text: str,
        changelog: str = '',
        created_by: str = None
    ):
        self.version = version
        self.content_text = content_text
        self.changelog = changelog
        self.created_by = created_by
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'content_text': self.content_text,
            'changelog': self.changelog,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptVersion':
        pv = cls(
            version=data.get('version', '1.0.0'),
            content_text=data.get('content_text', ''),
            changelog=data.get('changelog', ''),
            created_by=data.get('created_by')
        )
        if isinstance(data.get('created_at'), datetime):
            pv.created_at = data['created_at']
        return pv


class DynamicField:
    """Represents a dynamic input variable for the prompt"""
    
    def __init__(
        self,
        variable: str,
        label: str,
        field_type: str = 'string',
        required: bool = True,
        default_value: str = None,
        enum_options: List[str] = None
    ):
        self.id = str(uuid4())
        self.variable = variable
        self.label = label
        self.field_type = field_type
        self.required = required
        self.default_value = default_value
        self.enum_options = enum_options or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'variable': self.variable,
            'label': self.label,
            'type': self.field_type,
            'required': self.required,
            'default_value': self.default_value,
            'enum_options': self.enum_options
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DynamicField':
        df = cls(
            variable=data.get('variable', ''),
            label=data.get('label', ''),
            field_type=data.get('type', 'string'),
            required=data.get('required', True),
            default_value=data.get('default_value'),
            enum_options=data.get('enum_options', [])
        )
        if 'id' in data:
            df.id = data['id']
        return df


class Prompt:
    """
    Prompt model for the Library database.
    Uses pymongo for direct MongoDB operations.
    
    Based on comprehensive Prompt schema with:
    - Version control
    - Dynamic input variables
    - Classification and tagging
    - Model compatibility
    - Usage statistics
    - Lifecycle management
    - Custom fields
    """
    
    COLLECTION_NAME = 'prompts'
    
    # Valid categories
    CATEGORIES = [
        'text_generation',
        'image_generation',
        'code_generation',
        'data_analysis',
        'creative_writing',
        'translation',
        'summarization'
    ]
    
    def __init__(
        self,
        name: str,
        content_text: str,
        description: str = '',
        prompt_id: str = None,
        category: str = 'text_generation',
        use_case: str = '',
        tags: List[str] = None,
        allowed_industries: List[str] = None,
        model_compatibility: List[str] = None,
        language: str = 'en',
        dynamic_fields: List[Dict[str, Any]] = None,
        custom_fields: Dict[str, Any] = None,
        is_archived: bool = False,
        created_by: str = None,
        updated_by: str = None,
        _id: ObjectId = None
    ):
        # Core identification
        self._id = _id
        self.prompt_id = prompt_id or self._generate_prompt_id(name)
        self.name = name
        self.description = description
        
        # Content
        self.content_text = content_text
        self.language = language
        self.dynamic_fields = dynamic_fields or []
        
        # Classification
        self.category = category
        self.use_case = use_case
        self.tags = tags or []
        self.allowed_industries = allowed_industries or []
        
        # Compatibility
        self.model_compatibility = model_compatibility or []
        
        # Versioning
        self.versions = []
        self.active_version = '1.0.0'
        
        # Usage stats
        self.total_uses = 0
        self.usage_count = 0
        self.last_used_at = None
        self.avg_generation_time = 0.0
        self.cost_estimate = 0.0
        
        # Lifecycle
        self.is_archived = is_archived
        self.archived_at = None
        self.created_by = created_by
        self.updated_by = updated_by
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Custom fields (horizontally expandable)
        self.custom_fields = custom_fields or {}
    
    def _generate_prompt_id(self, name: str) -> str:
        """Generate a prompt_id from name"""
        import re
        # Convert name to lowercase, replace spaces with hyphens
        clean = re.sub(r'[^a-z0-9\s-]', '', name.lower())
        clean = re.sub(r'[\s]+', '-', clean)
        return clean.strip('-')
    
    @property
    def id(self) -> str:
        """Return string representation of ObjectId"""
        return str(self._id) if self._id else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prompt to dictionary"""
        return {
            'id': self.id,
            'prompt_id': self.prompt_id,
            'name': self.name,
            'description': self.description,
            'versioning': {
                'versions': self.versions,
                'active_version': self.active_version
            },
            'content': {
                'text': self.content_text,
                'language': self.language,
                'expected_input_vars': {
                    'dynamic_fields': self.dynamic_fields
                }
            },
            'classification': {
                'category': self.category,
                'use_case': self.use_case,
                'tags': self.tags,
                'allowed_industries': self.allowed_industries
            },
            'compatibility': {
                'model_compatibility': self.model_compatibility
            },
            'usage_stats': {
                'total_uses': self.total_uses,
                'usage_count': self.usage_count,
                'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
                'avg_generation_time': self.avg_generation_time,
                'cost_estimate': self.cost_estimate
            },
            'lifecycle': {
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                'is_archived': self.is_archived,
                'archived_at': self.archived_at.isoformat() if self.archived_at else None
            },
            'custom_fields': self.custom_fields,
            'created_by': self.created_by,
            'updated_by': self.updated_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prompt':
        """Create Prompt instance from dictionary"""
        # Extract nested data
        versioning = data.get('versioning', {})
        content = data.get('content', {})
        classification = data.get('classification', {})
        compatibility = data.get('compatibility', {})
        usage_stats = data.get('usage_stats', {})
        lifecycle = data.get('lifecycle', {})
        
        input_vars = content.get('expected_input_vars', {})
        dynamic_fields = input_vars.get('dynamic_fields', [])
        
        # Convert dynamic fields to proper format
        if dynamic_fields and isinstance(dynamic_fields[0], dict) and 'variable' not in dynamic_fields[0]:
            # Already in correct format
            processed_fields = dynamic_fields
        else:
            processed_fields = []
            for field in dynamic_fields:
                if isinstance(field, dict):
                    if 'variable' in field:
                        processed_fields.append(field)
                    elif 'id' in field:
                        processed_fields.append(field)
        
        prompt = cls(
            name=data.get('name', ''),
            content_text=content.get('text', ''),
            description=data.get('description', ''),
            prompt_id=data.get('prompt_id'),
            category=classification.get('category', 'text_generation'),
            use_case=classification.get('use_case', ''),
            tags=classification.get('tags', []),
            allowed_industries=classification.get('allowed_industries', []),
            model_compatibility=compatibility.get('model_compatibility', []),
            language=content.get('language', 'en'),
            dynamic_fields=processed_fields,
            custom_fields=data.get('custom_fields', {}),
            is_archived=lifecycle.get('is_archived', False),
            created_by=data.get('created_by'),
            updated_by=data.get('updated_by'),
            _id=data.get('_id')
        )
        
        # Versioning
        prompt.versions = versioning.get('versions', [])
        prompt.active_version = versioning.get('active_version', '1.0.0')
        
        # Usage stats
        prompt.total_uses = usage_stats.get('total_uses', 0)
        prompt.usage_count = usage_stats.get('usage_count', 0)
        if usage_stats.get('last_used_at'):
            if isinstance(usage_stats['last_used_at'], str):
                prompt.last_used_at = datetime.fromisoformat(usage_stats['last_used_at'])
            else:
                prompt.last_used_at = usage_stats['last_used_at']
        prompt.avg_generation_time = usage_stats.get('avg_generation_time', 0.0)
        prompt.cost_estimate = usage_stats.get('cost_estimate', 0.0)
        
        # Lifecycle
        if lifecycle.get('created_at'):
            if isinstance(lifecycle['created_at'], str):
                prompt.created_at = datetime.fromisoformat(lifecycle['created_at'])
            else:
                prompt.created_at = lifecycle['created_at']
        if lifecycle.get('updated_at'):
            if isinstance(lifecycle['updated_at'], str):
                prompt.updated_at = datetime.fromisoformat(lifecycle['updated_at'])
            else:
                prompt.updated_at = lifecycle['updated_at']
        if lifecycle.get('archived_at'):
            if isinstance(lifecycle['archived_at'], str):
                prompt.archived_at = datetime.fromisoformat(lifecycle['archived_at'])
            else:
                prompt.archived_at = lifecycle['archived_at']
            
        return prompt
    
    # ==================== CRUD Operations ====================
    
    @classmethod
    def get_collection(cls):
        """Get the prompts collection"""
        return get_library_collection(cls.COLLECTION_NAME)
    
    def save(self) -> 'Prompt':
        """Insert or update the prompt in database"""
        collection = self.get_collection()
        
        prompt_data = {
            'prompt_id': self.prompt_id,
            'name': self.name,
            'description': self.description,
            'versioning': {
                'versions': self.versions,
                'active_version': self.active_version
            },
            'content': {
                'text': self.content_text,
                'language': self.language,
                'expected_input_vars': {
                    'dynamic_fields': self.dynamic_fields
                }
            },
            'classification': {
                'category': self.category,
                'use_case': self.use_case,
                'tags': self.tags,
                'allowed_industries': self.allowed_industries
            },
            'compatibility': {
                'model_compatibility': self.model_compatibility
            },
            'usage_stats': {
                'total_uses': self.total_uses,
                'usage_count': self.usage_count,
                'last_used_at': self.last_used_at,
                'avg_generation_time': self.avg_generation_time,
                'cost_estimate': self.cost_estimate
            },
            'lifecycle': {
                'created_at': self.created_at,
                'updated_at': datetime.utcnow(),
                'is_archived': self.is_archived,
                'archived_at': self.archived_at
            },
            'custom_fields': self.custom_fields,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
        }
        
        if self._id:
            # Update existing
            collection.update_one(
                {'_id': self._id},
                {'$set': prompt_data}
            )
        else:
            # Check for duplicate name
            existing = collection.find_one({'name': self.name})
            if existing:
                raise ValueError(f"Prompt with name '{self.name}' already exists")
            
            # Insert new
            prompt_data['lifecycle']['created_at'] = datetime.utcnow()
            result = collection.insert_one(prompt_data)
            self._id = result.inserted_id
        
        return self
    
    @classmethod
    def find_by_id(cls, prompt_id: str) -> Optional['Prompt']:
        """Find a prompt by ID"""
        try:
            collection = cls.get_collection()
            data = collection.find_one({'_id': ObjectId(prompt_id)})
            if data:
                return cls.from_dict(data)
        except Exception:
            pass
        return None
    
    @classmethod
    def find_by_prompt_id(cls, prompt_id: str) -> Optional['Prompt']:
        """Find a prompt by prompt_id (custom identifier)"""
        try:
            collection = cls.get_collection()
            data = collection.find_one({'prompt_id': prompt_id})
            if data:
                return cls.from_dict(data)
        except Exception:
            pass
        return None
    
    @classmethod
    def find_by_name(cls, name: str) -> Optional['Prompt']:
        """Find a prompt by exact name"""
        try:
            collection = cls.get_collection()
            data = collection.find_one({'name': name})
            if data:
                return cls.from_dict(data)
        except Exception:
            pass
        return None
    
    @classmethod
    def find_all(
        cls,
        filters: Dict[str, Any] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = 'created_at',
        sort_order: int = -1
    ) -> List['Prompt']:
        """Find all prompts with optional filters"""
        collection = cls.get_collection()
        filters = filters or {}
        
        cursor = collection.find(filters).skip(skip).limit(limit)
        cursor = cursor.sort(sort_by, sort_order)
        
        return [cls.from_dict(doc) for doc in cursor]
    
    @classmethod
    def find_by_category(cls, category: str, skip: int = 0, limit: int = 50) -> List['Prompt']:
        """Find prompts by category"""
        return cls.find_all(
            filters={'classification.category': category},
            skip=skip,
            limit=limit
        )
    
    @classmethod
    def find_public(cls, skip: int = 0, limit: int = 50) -> List['Prompt']:
        """Find non-archived prompts"""
        return cls.find_all(
            filters={'lifecycle.is_archived': False},
            skip=skip,
            limit=limit
        )
    
    @classmethod
    def search(cls, query: str, skip: int = 0, limit: int = 50) -> List['Prompt']:
        """Search prompts by name, description, content, or tags"""
        collection = cls.get_collection()
        
        filters = {
            '$or': [
                {'name': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}},
                {'content.text': {'$regex': query, '$options': 'i'}},
                {'classification.tags': {'$regex': query, '$options': 'i'}},
            ]
        }
        
        cursor = collection.find(filters).skip(skip).limit(limit)
        cursor = cursor.sort('lifecycle.created_at', -1)
        
        return [cls.from_dict(doc) for doc in cursor]
    
    @classmethod
    def find_by_tag(cls, tag: str, skip: int = 0, limit: int = 50) -> List['Prompt']:
        """Find prompts by tag"""
        return cls.find_all(
            filters={'classification.tags': tag},
            skip=skip,
            limit=limit
        )
    
    def delete(self) -> bool:
        """Delete this prompt"""
        if not self._id:
            return False
        
        collection = self.get_collection()
        result = collection.delete_one({'_id': self._id})
        return result.deleted_count > 0
    
    @classmethod
    def delete_by_id(cls, prompt_id: str) -> bool:
        """Delete a prompt by ID"""
        try:
            collection = cls.get_collection()
            result = collection.delete_one({'_id': ObjectId(prompt_id)})
            return result.deleted_count > 0
        except Exception:
            return False
    
    @classmethod
    def count(cls, filters: Dict[str, Any] = None) -> int:
        """Count prompts matching filters"""
        collection = cls.get_collection()
        filters = filters or {}
        return collection.count_documents(filters)
    
    @classmethod
    def get_categories(cls) -> List[str]:
        """Get all unique categories"""
        return cls.CATEGORIES
    
    @classmethod
    def get_all_tags(cls) -> List[str]:
        """Get all unique tags from prompts"""
        collection = cls.get_collection()
        tags = collection.distinct('classification.tags')
        return [t for t in tags if t]
    
    # ==================== Version Control ====================
    
    def create_version(self, version: str, changelog: str = '', created_by: str = None) -> None:
        """Create a new version of the prompt"""
        version_entry = {
            'version': version,
            'content_text': self.content_text,
            'changelog': changelog,
            'created_by': created_by or self.updated_by,
            'created_at': datetime.utcnow().isoformat()
        }
        self.versions.append(version_entry)
        self.active_version = version
    
    def get_active_content(self) -> str:
        """Get the active version's content text"""
        return self.content_text
    
    # ==================== Usage Tracking ====================
    
    def increment_usage(self, generation_time: float = 0.0, cost: float = 0.0) -> None:
        """Record a usage of this prompt"""
        self.total_uses += 1
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        
        # Update running average
        if self.total_uses > 0:
            self.avg_generation_time = (
                (self.avg_generation_time * (self.total_uses - 1) + generation_time) 
                / self.total_uses
            )
        self.cost_estimate = cost
    
    # ==================== Archive ====================
    
    def archive(self) -> None:
        """Archive this prompt"""
        self.is_archived = True
        self.archived_at = datetime.utcnow()
    
    def unarchive(self) -> None:
        """Unarchive this prompt"""
        self.is_archived = False
        self.archived_at = None
