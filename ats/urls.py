from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/new/', views.job_create, name='job_create'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('jobs/<int:pk>/edit/', views.job_edit, name='job_edit'),
    path('jobs/<int:pk>/delete/', views.job_delete, name='job_delete'),
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('candidates/new/', views.candidate_create, name='candidate_create'),
    path('candidates/<int:pk>/', views.candidate_detail, name='candidate_detail'),
    path('candidates/<int:pk>/edit/', views.candidate_edit, name='candidate_edit'),
    path('candidates/<int:pk>/delete/', views.candidate_delete, name='candidate_delete'),
    path('applications/', views.application_list, name='application_list'),
    path('applications/new/', views.application_create, name='application_create'),
    path('applications/<int:pk>/edit/', views.application_edit, name='application_edit'),
    path('applications/<int:pk>/delete/', views.application_delete, name='application_delete'),
    # AI matching
    path('jobs/<int:pk>/match/', views.job_match_candidates, name='job_match_candidates'),
    path('candidates/<int:pk>/match/', views.candidate_match_jobs, name='candidate_match_jobs'),
    # AI on-demand endpoints
    path('jobs/parse-file/', views.job_parse_file, name='job_parse_file'),
    path('jobs/enhance-preview/', views.job_enhance_preview, name='job_enhance_preview'),
    path('jobs/<int:pk>/enhance/', views.job_enhance, name='job_enhance'),
    path('applications/<int:pk>/screen/', views.application_screen, name='application_screen'),
    path('applications/<int:pk>/score/', views.application_score, name='application_score'),
    path('applications/<int:pk>/questions/', views.application_questions, name='application_questions'),
    path('candidates/<int:pk>/parse-resume/', views.candidate_parse_resume, name='candidate_parse_resume'),
    # Audit log
    path('audit/', views.audit_log_list, name='audit_log'),
]
