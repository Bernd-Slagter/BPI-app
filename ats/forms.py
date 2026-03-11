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
        fields = ['title', 'department', 'location', 'description', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Senior Backend Engineer'}),
            'department': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Engineering'}),
            'location': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. Remote or New York, NY'}),
            'description': forms.Textarea(attrs={'class': 'input', 'rows': 4, 'placeholder': 'Role requirements and responsibilities'}),
            'status': forms.Select(attrs={'class': 'input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.fields.get('title'):
            self.fields['title'].required = True


class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['first_name', 'last_name', 'email', 'phone', 'resume_summary']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'input'}),
            'last_name': forms.TextInput(attrs={'class': 'input'}),
            'email': forms.EmailInput(attrs={'class': 'input'}),
            'phone': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Optional'}),
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
        fields = ['job', 'candidate', 'status', 'notes']
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
    """Edit status and notes only (job/candidate fixed)."""
    class Meta:
        model = Application
        fields = ['status', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'input'}),
            'notes': forms.Textarea(attrs={'class': 'input', 'rows': 3}),
        }
