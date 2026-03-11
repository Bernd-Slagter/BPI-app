from collections import defaultdict
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .models import Job, Candidate, Application
from .forms import (
    JobForm, CandidateForm, ApplicationForm, ApplicationEditForm,
    VALID_JOB_STATUSES, VALID_APPLICATION_STATUSES,
)

# Application pipeline stages for flowcharts (order matters)
PIPELINE_STAGES = [
    ('submitted', 'Submitted'),
    ('screening', 'Screening'),
    ('interview', 'Interview'),
    ('offer', 'Offer'),
    ('hired', 'Hired'),
]
OUTCOME_STAGES = [
    ('rejected', 'Rejected'),
    ('withdrawn', 'Withdrawn'),
]
ALL_APPLICATION_STAGES = PIPELINE_STAGES + OUTCOME_STAGES


def home(request):
    """Dashboard: jobs, recent applications, stats."""
    jobs = Job.objects.filter(status='open')[:10]
    recent_applications = Application.objects.select_related('job', 'candidate')[:10]
    stats = {
        'open_jobs': Job.objects.filter(status='open').count(),
        'total_candidates': Candidate.objects.count(),
        'applications_pending': Application.objects.exclude(
            status__in=('hired', 'rejected', 'withdrawn')
        ).count(),
    }
    return render(request, 'ats/home.html', {
        'jobs': jobs,
        'recent_applications': recent_applications,
        'stats': stats,
    })


def job_list(request):
    """List all jobs (open by default)."""
    status_filter = request.GET.get('status', 'open')
    if status_filter not in VALID_JOB_STATUSES:
        status_filter = 'open'
    jobs = Job.objects.filter(status=status_filter).order_by('-created_at')
    return render(request, 'ats/job_list.html', {'jobs': jobs, 'status_filter': status_filter})


def job_detail(request, pk):
    """Job detail with its applications and pipeline."""
    job = get_object_or_404(Job.objects.prefetch_related('applications__candidate'), pk=pk)
    by_status = defaultdict(list)
    for app in job.applications.all():
        by_status[app.status].append(app)
    pipeline_columns = [
        (key, label, by_status.get(key, [])) for key, label in ALL_APPLICATION_STAGES
    ]
    return render(request, 'ats/job_detail.html', {
        'job': job,
        'pipeline_columns': pipeline_columns,
    })


@require_http_methods(['GET', 'POST'])
def job_create(request):
    form = JobForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Job created successfully.')
        return redirect('job_list')
    return render(request, 'ats/job_form.html', {'form': form, 'title': 'Add job'})


@require_http_methods(['GET', 'POST'])
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk)
    form = JobForm(request.POST or None, instance=job)
    if form.is_valid():
        form.save()
        messages.success(request, 'Job updated successfully.')
        return redirect('job_detail', pk=pk)
    return render(request, 'ats/job_form.html', {'form': form, 'job': job, 'title': f'Edit {job.title}'})


@require_http_methods(['GET', 'POST'])
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if request.method == 'POST':
        app_count = job.applications.count()
        job.delete()
        messages.success(request, f'Job deleted. {app_count} application(s) were also removed.')
        return redirect('job_list')
    return render(request, 'ats/confirm_delete.html', {
        'object': job,
        'object_type': 'job',
        'cancel_url': 'job_detail',
        'cancel_pk': pk,
        'extra_warning': f'This will permanently delete {job.applications.count()} application(s) for this position.' if job.applications.exists() else None,
    })


def candidate_list(request):
    """List all candidates."""
    candidates = Candidate.objects.prefetch_related('applications').order_by('last_name', 'first_name')
    return render(request, 'ats/candidate_list.html', {'candidates': candidates})


def candidate_detail(request, pk):
    """Candidate detail with their applications and pipeline."""
    candidate = get_object_or_404(Candidate.objects.prefetch_related('applications__job'), pk=pk)
    return render(request, 'ats/candidate_detail.html', {
        'candidate': candidate,
        'pipeline_stages': PIPELINE_STAGES,
        'outcome_stages': OUTCOME_STAGES,
    })


@require_http_methods(['GET', 'POST'])
def candidate_create(request):
    form = CandidateForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Candidate added successfully.')
        return redirect('candidate_list')
    return render(request, 'ats/candidate_form.html', {'form': form, 'title': 'Add candidate'})


@require_http_methods(['GET', 'POST'])
def candidate_edit(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    form = CandidateForm(request.POST or None, instance=candidate)
    if form.is_valid():
        form.save()
        messages.success(request, 'Candidate updated successfully.')
        return redirect('candidate_detail', pk=pk)
    return render(request, 'ats/candidate_form.html', {
        'form': form, 'candidate': candidate, 'title': f'Edit {candidate}',
    })


@require_http_methods(['GET', 'POST'])
def candidate_delete(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    if request.method == 'POST':
        app_count = candidate.applications.count()
        candidate.delete()
        messages.success(request, f'Candidate removed. {app_count} application(s) were also deleted.')
        return redirect('candidate_list')
    return render(request, 'ats/confirm_delete.html', {
        'object': candidate,
        'object_type': 'candidate',
        'cancel_url': 'candidate_detail',
        'cancel_pk': pk,
        'extra_warning': f'This will permanently delete {candidate.applications.count()} application(s).' if candidate.applications.exists() else None,
    })


def application_list(request):
    """List all applications with optional status filter."""
    status_filter = request.GET.get('status', '')
    if status_filter and status_filter not in VALID_APPLICATION_STATUSES:
        status_filter = ''
    applications = Application.objects.select_related('job', 'candidate').order_by('-applied_at')
    if status_filter:
        applications = applications.filter(status=status_filter)
    return render(request, 'ats/application_list.html', {
        'applications': applications,
        'status_filter': status_filter,
    })


@require_http_methods(['GET', 'POST'])
def application_create(request):
    job_id = request.GET.get('job')
    initial = None
    if job_id and job_id.isdigit():
        if Job.objects.filter(pk=int(job_id)).exists():
            initial = {'job': int(job_id)}
    form = ApplicationForm(request.POST or None, initial=initial)
    if form.is_valid():
        form.save()
        messages.success(request, 'Application added successfully.')
        return redirect('application_list')
    return render(request, 'ats/application_form.html', {'form': form, 'title': 'Add application'})


@require_http_methods(['GET', 'POST'])
def application_edit(request, pk):
    application = get_object_or_404(Application, pk=pk)
    form = ApplicationEditForm(request.POST or None, instance=application)
    if form.is_valid():
        form.save()
        messages.success(request, 'Application updated successfully.')
        return redirect('application_list')
    return render(request, 'ats/application_edit.html', {
        'form': form,
        'application': application,
        'title': 'Edit application',
    })


@require_http_methods(['GET', 'POST'])
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if request.method == 'POST':
        application.delete()
        messages.success(request, 'Application removed.')
        return redirect('application_list')
    return render(request, 'ats/confirm_delete.html', {
        'object': application,
        'object_type': 'application',
        'cancel_url': 'application_list',
    })
