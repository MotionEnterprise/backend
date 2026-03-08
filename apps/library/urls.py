"""
Library app URL configuration.
"""

from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    # Prompt CRUD endpoints
    path('prompts/', views.PromptListCreateView.as_view(), name='prompt-list'),
    path('prompts/<str:prompt_id>/', views.PromptDetailView.as_view(), name='prompt-detail'),
    path('prompts/name/<str:name>/', views.PromptByNameView.as_view(), name='prompt-by-name'),
    
    # Prompt actions
    path('prompts/<str:prompt_id>/archive/', views.PromptArchiveView.as_view(), name='prompt-archive'),
    path('prompts/<str:prompt_id>/versions/', views.PromptVersionView.as_view(), name='prompt-versions'),
    path('prompts/<str:prompt_id>/usage/', views.PromptUsageView.as_view(), name='prompt-usage'),
    
    # Metadata endpoints
    path('categories/', views.PromptCategoryView.as_view(), name='categories'),
    path('tags/', views.PromptTagsView.as_view(), name='tags'),
]