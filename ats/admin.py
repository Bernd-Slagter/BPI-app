from django.contrib import admin
from .models import Job, Candidate, Application


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'location', 'status', 'created_at')
    list_filter = ('status', 'department')
    search_fields = ('title', 'department', 'location')


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'email', 'phone', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'status', 'applied_at')
    list_filter = ('status',)
    search_fields = ('candidate__last_name', 'candidate__first_name', 'job__title')
    raw_id_fields = ('job', 'candidate')
