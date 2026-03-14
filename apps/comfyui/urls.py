"""
URL routing for ComfyUI Django app.

Provides REST API endpoints for:
- Health checks
- File uploads
- Workflow submission
- Job status polling
- Output retrieval
- Queue management
"""

from django.urls import path

from . import views

app_name = 'comfyui'

urlpatterns = [
    path('health/', views.HealthView.as_view(), name='comfyui-health'),
    path('upload/', views.UploadInputView.as_view(), name='comfyui-upload'),
    path('workflow/run/', views.WorkflowSubmitView.as_view(), name='comfyui-run'),
    path('job/<uuid:job_id>/status/', views.JobStatusView.as_view(), name='comfyui-status'),
    path('job/<uuid:job_id>/outputs/', views.JobOutputsView.as_view(), name='comfyui-outputs'),
    path('download/', views.FileDownloadView.as_view(), name='comfyui-download'),
    path('queue/', views.QueueView.as_view(), name='comfyui-queue'),
    path('queue/interrupt/', views.InterruptView.as_view(), name='comfyui-interrupt'),
]
