from datetime import datetime
from mongoengine import (
    Document, EmbeddedDocument,
    StringField, BooleanField, DateTimeField,
    IntField, ListField,
    EmbeddedDocumentField, ReferenceField,
    DictField,
)


class RecipeMember(EmbeddedDocument):
    user_id  = StringField(required=True)
    role     = StringField(choices=['Owner', 'Admin', 'Editor', 'Viewer'], required=True)
    name     = StringField(required=True)
    email    = StringField(required=True)
    added_at = DateTimeField(default=datetime.utcnow)


class GeneratedContentItem(EmbeddedDocument):
    id           = StringField(required=True)
    prompt_id    = StringField(required=True)
    url          = StringField(required=True)
    type         = StringField(choices=['image', 'video', 'audio', 'text'], required=True)
    size         = IntField(required=True)
    width        = IntField()
    height       = IntField()
    storage_path = StringField(required=True)
    user_id      = StringField(required=True)
    created_at   = DateTimeField(default=datetime.utcnow)


class HistoryRecord(EmbeddedDocument):
    prompt_id   = StringField(required=True)
    executed_at = DateTimeField(default=datetime.utcnow)
    user_id     = StringField(required=True)


class CreditUsageEntry(EmbeddedDocument):
    node_id   = StringField(required=True)
    node_type = StringField(required=True)
    cost      = IntField(required=True)
    timestamp = DateTimeField(default=datetime.utcnow)
    status    = StringField(choices=['completed', 'failed', 'pending'], default='pending')
    user_id   = StringField()


class Recipe(Document):
    name       = StringField(required=True)
    owner      = ReferenceField('accounts.User', required=True)
    visibility = StringField(choices=['public', 'private'], default='private')
    is_app     = BooleanField(default=False)

    canvas_snapshot   = DictField()
    members           = ListField(EmbeddedDocumentField(RecipeMember), default=list)
    generated_content = ListField(EmbeddedDocumentField(GeneratedContentItem), default=list)
    history           = ListField(EmbeddedDocumentField(HistoryRecord), default=list)
    credit_usage      = ListField(EmbeddedDocumentField(CreditUsageEntry), default=list)
    total_credit_cost = IntField(default=0)

    is_deleted = BooleanField(default=False)
    deleted_at = DateTimeField(default=None)

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'recipes',
        'indexes': ['owner', 'visibility', 'is_app', 'is_deleted']
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"<Recipe {self.name}>"


class NodeExecutionEntry(EmbeddedDocument):
    node_id   = StringField(required=True)
    node_name = StringField(required=True)
    credits   = IntField(required=True)
    status    = StringField(choices=['completed', 'failed', 'pending'], default='pending')


class Job(Document):
    name         = StringField(required=True)
    recipe       = ReferenceField(Recipe, required=True)
    triggered_by = ReferenceField('accounts.User', required=True)

    status         = StringField(
        choices=['pending', 'queued', 'processing', 'completed', 'failed', 'cancelled'],
        default='pending'
    )
    celery_task_id = StringField(default=None)

    execution_history = ListField(EmbeddedDocumentField(NodeExecutionEntry), default=list)
    total_credits     = IntField(default=0)

    output_assets = ListField(ReferenceField('generation.GeneratedAsset'), default=list)
    error_message = StringField(default=None)

    queued_at    = DateTimeField(default=None)
    started_at   = DateTimeField(default=None)
    completed_at = DateTimeField(default=None)
    created_at   = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'jobs',
        'indexes': ['recipe', 'triggered_by', 'status', '-created_at', 'celery_task_id']
    }

    def add_node_execution(self, node_id: str, node_name: str,
                           credits: int, status: str = 'completed') -> None:
        self.execution_history.append(
            NodeExecutionEntry(node_id=node_id, node_name=node_name,
                               credits=credits, status=status)
        )
        self.total_credits += credits

    def __str__(self):
        return f"<Job {self.name} [{self.status}]>"


class GeneratedAsset(Document):
    job            = ReferenceField(Job, required=True)
    recipe         = ReferenceField(Recipe, required=True)
    triggered_by   = ReferenceField('accounts.User', required=True)
    prompt_node_id = StringField()

    url               = StringField(required=True)
    storage_path      = StringField(required=True)
    original_filename = StringField()
    type              = StringField(choices=['image', 'video', 'audio', 'text'], required=True)
    size              = IntField()
    width             = IntField()
    height            = IntField()

    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'generated_assets',
        'indexes': ['job', 'recipe', 'triggered_by', ('recipe', '-created_at')]
    }

    def __str__(self):
        return f"<GeneratedAsset {self.type} [{self.id}]>"


class ExecutionLog(Document):
    user         = ReferenceField('accounts.User', required=True)
    recipe       = ReferenceField(Recipe, required=True)
    job          = ReferenceField(Job, required=True)
    triggered_by = ReferenceField('accounts.User', required=True)

    node_id   = StringField(required=True)
    node_type = StringField(required=True)
    credits   = IntField(required=True)
    status    = StringField(choices=['completed', 'failed'], required=True)

    executed_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'execution_logs',
        'indexes': [
            'user',
            'recipe',
            'job',
            'triggered_by',
            '-executed_at',
            ('user', '-executed_at'),
            ('recipe', '-executed_at'),
        ]
    }

    def __str__(self):
        return f"<ExecutionLog {self.node_type} -{self.credits} credits>"
