import secrets
import bcrypt
from datetime import datetime, timedelta
from mongoengine import (
    Document, EmbeddedDocument,
    StringField, EmailField, BooleanField,
    DateTimeField, IntField,
    ListField, EmbeddedDocumentField,
    ReferenceField, ObjectIdField,
)


class RecipeAccess(EmbeddedDocument):
    recipe_id = ObjectIdField(required=True)
    role      = StringField(
        choices=['Owner', 'Admin', 'Editor', 'Viewer'],
        required=True
    )


class UserSubscription(EmbeddedDocument):
    credits = IntField(default=0)
    type    = StringField(default='free')


class CreditSummary(EmbeddedDocument):
    total_used      = IntField(default=0)
    total_purchased = IntField(default=0)


class User(Document):
    email  = EmailField(required=True, unique=True)
    name   = StringField(required=True, min_length=2, max_length=50)
    avatar = StringField(default=None)

    password_hash = StringField(default=None)
    provider      = StringField(
        choices=['credentials', 'google'],
        required=True,
        default='credentials'
    )
    google_id     = StringField(default=None)

    is_verified   = BooleanField(default=False)

    reset_token   = StringField(default=None)
    reset_expires = DateTimeField(default=None)

    recipes        = ListField(EmbeddedDocumentField(RecipeAccess), default=list)
    subscription   = EmbeddedDocumentField(UserSubscription, default=UserSubscription)
    credit_summary = EmbeddedDocumentField(CreditSummary, default=CreditSummary)

    last_login_at         = DateTimeField(default=None)
    failed_login_attempts = IntField(default=0)
    locked_until          = DateTimeField(default=None)

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'users',
        'indexes': [
            'email',
            {'fields': ['google_id'], 'sparse': True},
            'locked_until',
            '-last_login_at',
            'is_verified',
        ]
    }

    def set_password(self, plain: str) -> None:
        self.password_hash = bcrypt.hashpw(
            plain.encode('utf-8'), bcrypt.gensalt(12)
        ).decode('utf-8')

    def check_password(self, plain: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.checkpw(
            plain.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def generate_reset_token(self) -> str:
        token = secrets.token_urlsafe(32)
        self.reset_token   = token
        self.reset_expires = datetime.utcnow() + timedelta(hours=1)
        return token

    def verify_reset_token(self, token: str) -> bool:
        if not self.reset_token or not self.reset_expires:
            return False
        if self.reset_token != token:
            return False
        if datetime.utcnow() > self.reset_expires:
            return False
        return True

    def clear_reset_token(self) -> None:
        self.reset_token   = None
        self.reset_expires = None

    def is_reset_token_expired(self) -> bool:
        if not self.reset_expires:
            return True
        return datetime.utcnow() > self.reset_expires

    def lock_account(self) -> None:
        self.locked_until          = datetime.utcnow() + timedelta(minutes=30)
        self.failed_login_attempts = 0

    def unlock_account(self) -> None:
        self.locked_until          = None
        self.failed_login_attempts = 0

    def can_attempt_login(self) -> bool:
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return False
        return True

    def add_recipe(self, recipe_id, role: str) -> bool:
        for r in self.recipes:
            if r.recipe_id == recipe_id:
                return False
        self.recipes.append(RecipeAccess(recipe_id=recipe_id, role=role))
        return True

    def remove_recipe(self, recipe_id) -> bool:
        for r in self.recipes:
            if r.recipe_id == recipe_id:
                self.recipes.remove(r)
                return True
        return False

    def has_recipe(self, recipe_id) -> bool:
        return any(r.recipe_id == recipe_id for r in self.recipes)

    def get_recipe_role(self, recipe_id) -> str | None:
        for r in self.recipes:
            if r.recipe_id == recipe_id:
                return r.role
        return None

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"<User {self.email}>"
