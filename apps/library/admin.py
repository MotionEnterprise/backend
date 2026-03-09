"""
Django admin configuration for Library app.

Since we use pymongo (not Django ORM), the Prompt model cannot be registered
with the standard Django admin. 

The Library app will appear in Django admin index, but with no models.
All CRUD operations are handled via API endpoints:
- /api/library/prompts/
"""

from django.contrib import admin

# Empty admin - pymongo models can't be registered with Django admin
# The app is registered in INSTALLED_APPS so it shows in admin index
