from django.conf import settings
from django.db import models


class Job(models.Model):
    """A job position open for applications."""
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    status_choices = [
        ('open', 'Open'),
        ('on_hold', 'On Hold'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='open')
    employment_type_choices = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ]
    employment_type = models.CharField(max_length=20, choices=employment_type_choices, blank=True)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True, help_text='Application deadline')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Candidate(models.Model):
    """A person who can apply for jobs."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    linkedin_url = models.URLField(blank=True)
    source_choices = [
        ('', 'Unknown'),
        ('direct', 'Direct application'),
        ('linkedin', 'LinkedIn'),
        ('referral', 'Referral'),
        ('job_board', 'Job board'),
        ('agency', 'Recruitment agency'),
        ('other', 'Other'),
    ]
    source = models.CharField(max_length=20, blank=True, choices=source_choices)
    resume_summary = models.TextField(blank=True)
    resume_file = models.FileField(upload_to='resumes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Application(models.Model):
    """A candidate's application to a job."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    status_choices = [
        ('submitted', 'Submitted'),
        ('screening', 'Screening'),
        ('interview', 'Interview'),
        ('offer', 'Offer'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    status = models.CharField(max_length=20, choices=status_choices, default='submitted')
    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    offer_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ai_match_score = models.IntegerField(null=True, blank=True)
    ai_match_rationale = models.TextField(blank=True)
    ai_screening_notes = models.TextField(blank=True)
    ai_interview_questions = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        unique_together = [['job', 'candidate']]

    def __str__(self):
        return f"{self.candidate} → {self.job} ({self.get_status_display()})"


class AuditLog(models.Model):
    """Immutable record of every significant action in the system."""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100, db_index=True)
    object_type = models.CharField(max_length=50, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=250, blank=True)
    detail = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} [{self.action}] {self.object_repr}"
