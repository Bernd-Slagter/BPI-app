from django import forms
from django.core.exceptions import ValidationError
from .models import Job, Candidate, Application

VALID_JOB_STATUSES = {'open', 'on_hold', 'filled', 'cancelled'}
VALID_APPLICATION_STATUSES = {
    'submitted', 'screening', 'interview', 'offer', 'hired', 'rejected', 'withdrawn'
}


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'department', 'location', 'employment_type', 'salary_min', 'salary_max', 'deadline', 'description', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Senior Backend Engineer'}),
            'department': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Engineering'}),
            'location': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Remote or New York, NY'}),
            'employment_type': forms.Select(attrs={'class': 'input'}),
            'salary_min': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'e.g. 60000', 'min': '0'}),
            'salary_max': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'e.g. 90000', 'min': '0'}),
            'deadline': forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
            'description': forms.Textarea(attrs={'class': 'input', 'rows': 6, 'placeholder': 'Role requirements and responsibilities'}),
            'status': forms.Select(attrs={'class': 'input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.fields.get('title'):
            self.fields['title'].required = True
        # Add empty label for optional select
        self.fields['employment_type'].empty_label = None
        self.fields['employment_type'].choices = [('', '— Select type —')] + list(Job.employment_type_choices)

    def clean(self):
        cleaned = super().clean()
        salary_min = cleaned.get('salary_min')
        salary_max = cleaned.get('salary_max')
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise ValidationError('Minimum salary cannot exceed maximum salary.')
        return cleaned


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['first_name', 'last_name', 'email', 'phone', 'linkedin_url', 'source', 'resume_summary', 'resume_file']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input'}),
            'last_name': forms.TextInput(attrs={'class': 'input'}),
            'email': forms.EmailInput(attrs={'class': 'input'}),
            'phone': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Optional'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'input', 'placeholder': 'https://linkedin.com/in/username'}),
            'source': forms.Select(attrs={'class': 'input'}),
            'resume_summary': forms.Textarea(attrs={'class': 'input', 'rows': 4, 'placeholder': 'Brief summary or paste resume highlights'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('first_name', 'last_name', 'email'):
            if self.fields.get(name):
                self.fields[name].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            return email
        qs = Candidate.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('A candidate with this email already exists.')
        return email


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['job', 'candidate', 'status', 'notes', 'attachment', 'contract_file']
        widgets = {
            'job': forms.Select(attrs={'class': 'input'}),
            'candidate': forms.Select(attrs={'class': 'input'}),
            'status': forms.Select(attrs={'class': 'input'}),
            'notes': forms.Textarea(attrs={'class': 'input', 'rows': 3, 'placeholder': 'Internal notes (optional)'}),
        }

    def clean(self):
        cleaned = super().clean()
        job = cleaned.get('job')
        candidate = cleaned.get('candidate')
        if job and candidate:
            qs = Application.objects.filter(job=job, candidate=candidate)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('This candidate has already applied to this job.')
        return cleaned


class ApplicationEditForm(forms.ModelForm):
    """Edit status, notes, files, and stage-specific fields."""
    class Meta:
        model = Application
        fields = ['status', 'notes', 'interview_date', 'offer_amount', 'attachment', 'contract_file']
        widgets = {
            'status': forms.Select(attrs={'class': 'input'}),
            'notes': forms.Textarea(attrs={'class': 'input', 'rows': 3}),
            'interview_date': forms.DateTimeInput(attrs={'class': 'input', 'type': 'datetime-local'}),
            'offer_amount': forms.NumberInput(attrs={'class': 'input', 'placeholder': 'e.g. 75000', 'min': '0', 'step': '0.01'}),
        }
