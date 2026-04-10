from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.contrib import messages
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from .audit import log_action
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
    jobs = Job.objects.filter(status='open').annotate(
        app_count=models.Count('applications')
    )[:10]
    recent_applications = Application.objects.select_related('job', 'candidate')[:10]
    pipeline_counts = {
        s: Application.objects.filter(status=s).count()
        for s in ('submitted', 'screening', 'interview', 'offer', 'hired', 'rejected')
    }
    stats = {
        'open_jobs': Job.objects.filter(status='open').count(),
        'total_candidates': Candidate.objects.count(),
        'total_applications': Application.objects.count(),
        'applications_pending': Application.objects.exclude(
            status__in=('hired', 'rejected', 'withdrawn')
        ).count(),
        'hired_this_month': Application.objects.filter(status='hired').count(),
        'pipeline_counts': pipeline_counts,
    }
    return render(request, 'ats/home.html', {
        'jobs': jobs,
        'recent_applications': recent_applications,
        'stats': stats,
    })


def job_list(request):
    status_filter = request.GET.get('status', 'open')
    if status_filter not in VALID_JOB_STATUSES:
        status_filter = 'open'
    jobs = Job.objects.filter(status=status_filter).annotate(
        app_count=models.Count('applications')
    ).order_by('-created_at')
    return render(request, 'ats/job_list.html', {'jobs': jobs, 'status_filter': status_filter})


def job_detail(request, pk):
    job = get_object_or_404(Job.objects.prefetch_related('applications__candidate'), pk=pk)
    by_status = defaultdict(list)
    for app in job.applications.all():
        by_status[app.status].append(app)
    pipeline_columns = [
        (key, label, by_status.get(key, [])) for key, label in ALL_APPLICATION_STAGES
    ]
    applied_candidate_ids = job.applications.values_list('candidate_id', flat=True)
    suggested_candidates = Candidate.objects.exclude(pk__in=applied_candidate_ids).order_by('last_name', 'first_name')[:10]
    return render(request, 'ats/job_detail.html', {
        'job': job,
        'pipeline_columns': pipeline_columns,
        'suggested_candidates': suggested_candidates,
    })


@require_http_methods(['GET', 'POST'])
def job_create(request):
    form = JobForm(request.POST or None)
    if form.is_valid():
        job = form.save()
        log_action(request, 'job.created', job, f'Status: {job.status}')
        messages.success(request, 'Job created successfully.')
        return redirect('job_list')
    return render(request, 'ats/job_form.html', {'form': form, 'title': 'Add job'})


@require_http_methods(['GET', 'POST'])
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk)
    old_status = job.status
    form = JobForm(request.POST or None, instance=job)
    if form.is_valid():
        job = form.save()
        detail = f'Status: {old_status} → {job.status}' if old_status != job.status else f'Status: {job.status}'
        log_action(request, 'job.updated', job, detail)
        messages.success(request, 'Job updated successfully.')
        return redirect('job_detail', pk=pk)
    return render(request, 'ats/job_form.html', {'form': form, 'job': job, 'title': f'Edit {job.title}'})


@require_http_methods(['GET', 'POST'])
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if request.method == 'POST':
        app_count = job.applications.count()
        log_action(request, 'job.deleted', job, f'Had {app_count} application(s)')
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
    candidates = Candidate.objects.prefetch_related('applications').order_by('last_name', 'first_name')
    return render(request, 'ats/candidate_list.html', {'candidates': candidates})


def candidate_detail(request, pk):
    candidate = get_object_or_404(Candidate.objects.prefetch_related('applications__job'), pk=pk)
    applied_job_ids = candidate.applications.values_list('job_id', flat=True)
    suggested_jobs = Job.objects.filter(status='open').exclude(pk__in=applied_job_ids)[:10]
    conflicting_apps = candidate.applications.filter(status__in=['offer', 'hired'])
    conflict_list = list(conflicting_apps) if conflicting_apps.count() > 1 else []
    return render(request, 'ats/candidate_detail.html', {
        'candidate': candidate,
        'pipeline_stages': PIPELINE_STAGES,
        'outcome_stages': OUTCOME_STAGES,
        'suggested_jobs': suggested_jobs,
        'conflicting_apps': conflict_list,
    })


@require_http_methods(['GET', 'POST'])
def candidate_create(request):
    form = CandidateForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        candidate = form.save()
        log_action(request, 'candidate.created', candidate, f'Source: {candidate.get_source_display() or "unknown"}')
        if candidate.resume_file:
            try:
                from .ai_utils import parse_resume
                summary = parse_resume(candidate.resume_file.path, candidate.resume_summary)
                if summary and summary != candidate.resume_summary:
                    candidate.resume_summary = summary
                    candidate.save(update_fields=['resume_summary'])
                    log_action(request, 'ai.resume_parsed', candidate, 'Auto-parsed on create')
                    messages.success(request, 'Candidate added and resume parsed by AI.')
                else:
                    messages.success(request, 'Candidate added successfully.')
            except Exception:
                messages.success(request, 'Candidate added successfully.')
        else:
            messages.success(request, 'Candidate added successfully.')
        return redirect('candidate_list')
    return render(request, 'ats/candidate_form.html', {'form': form, 'title': 'Add candidate'})


@require_http_methods(['GET', 'POST'])
def candidate_edit(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    form = CandidateForm(request.POST or None, request.FILES or None, instance=candidate)
    if form.is_valid():
        candidate = form.save()
        log_action(request, 'candidate.updated', candidate)
        if candidate.resume_file and 'resume_file' in request.FILES:
            try:
                from .ai_utils import parse_resume
                summary = parse_resume(candidate.resume_file.path, candidate.resume_summary)
                if summary and summary != candidate.resume_summary:
                    candidate.resume_summary = summary
                    candidate.save(update_fields=['resume_summary'])
                    log_action(request, 'ai.resume_parsed', candidate, 'Re-parsed on file upload')
                    messages.success(request, 'Candidate updated and resume re-parsed by AI.')
                else:
                    messages.success(request, 'Candidate updated successfully.')
            except Exception:
                messages.success(request, 'Candidate updated successfully.')
        else:
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
        log_action(request, 'candidate.deleted', candidate, f'Had {app_count} application(s)')
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
    candidate_id = request.GET.get('candidate')
    initial = {}
    if job_id and job_id.isdigit():
        if Job.objects.filter(pk=int(job_id)).exists():
            initial['job'] = int(job_id)
    if candidate_id and candidate_id.isdigit():
        if Candidate.objects.filter(pk=int(candidate_id)).exists():
            initial['candidate'] = int(candidate_id)
    if not initial:
        initial = None
    form = ApplicationForm(request.POST or None, request.FILES or None, initial=initial)
    if form.is_valid():
        application = form.save()
        log_action(request, 'application.created', application,
                   f'Job: {application.job.title} | Candidate: {application.candidate}')
        try:
            from .ai_utils import score_candidate_job_match, screen_application
            candidate = application.candidate
            job = application.job
            match = score_candidate_job_match(candidate.resume_summary, job.title, job.description)
            screening = screen_application(candidate.resume_summary, job.title, job.description, application.notes)
            application.ai_match_score = match.get('score')
            application.ai_match_rationale = match.get('rationale', '')
            rec = screening.get('recommendation', '').upper()
            reasoning = screening.get('reasoning', '')
            application.ai_screening_notes = f"[{rec}] {reasoning}" if rec else reasoning
            application.save(update_fields=['ai_match_score', 'ai_match_rationale', 'ai_screening_notes'])
            log_action(request, 'ai.match_scored', application,
                       f'Score: {application.ai_match_score}/100 | Recommendation: {rec}')
        except Exception:
            pass
        messages.success(request, 'Application created. AI score and screening results are below.')
        return redirect('application_edit', pk=application.pk)
    return render(request, 'ats/application_form.html', {'form': form, 'title': 'Add application'})


@require_http_methods(['GET', 'POST'])
def application_edit(request, pk):
    application = get_object_or_404(Application, pk=pk)
    old_status = application.status
    form = ApplicationEditForm(request.POST or None, request.FILES or None, instance=application)
    if form.is_valid():
        application = form.save()
        detail = f'Status: {old_status} → {application.status}' if old_status != application.status else f'Status: {application.status}'
        if application.interview_date:
            detail += f' | Interview: {application.interview_date:%Y-%m-%d %H:%M}'
        if application.offer_amount:
            detail += f' | Offer: {application.offer_amount}'
        log_action(request, 'application.updated', application, detail)
        messages.success(request, 'Application updated.')
        return redirect('application_edit', pk=pk)
    return render(request, 'ats/application_edit.html', {
        'form': form,
        'application': application,
        'title': 'Edit application',
    })


@require_http_methods(['GET', 'POST'])
def application_delete(request, pk):
    application = get_object_or_404(Application, pk=pk)
    if request.method == 'POST':
        log_action(request, 'application.deleted', application)
        application.delete()
        messages.success(request, 'Application removed.')
        return redirect('application_list')
    return render(request, 'ats/confirm_delete.html', {
        'object': application,
        'object_type': 'application',
        'cancel_url': 'application_list',
    })


# ---------------------------------------------------------------------------
# AI-powered on-demand views
# ---------------------------------------------------------------------------

@require_http_methods(['POST'])
def job_parse_file(request):
    uploaded = request.FILES.get('job_file')
    if not uploaded:
        messages.error(request, 'Please select a file to parse.')
        return render(request, 'ats/job_form.html', {'form': JobForm(), 'title': 'Add job'})
    try:
        from .ai_utils import parse_job_file
        file_bytes = uploaded.read()
        data = parse_job_file(file_bytes, uploaded.name)
        if not data.get('title'):
            messages.error(request, 'Could not extract a job title from that file.')
            return render(request, 'ats/job_form.html', {'form': JobForm(), 'title': 'Add job'})
        form = JobForm(initial=data)
        log_action(request, 'ai.job_file_parsed', detail=f'File: {uploaded.name} → Title: {data.get("title")}')
        messages.success(request, f'Extracted "{data["title"]}" from {uploaded.name} — review and save.')
        return render(request, 'ats/job_form.html', {'form': form, 'title': 'Add job'})
    except Exception as exc:
        messages.error(request, f'File parsing failed: {exc}')
        return render(request, 'ats/job_form.html', {'form': JobForm(), 'title': 'Add job'})


@require_http_methods(['POST'])
def job_enhance_preview(request):
    title = request.POST.get('title', '').strip()
    department = request.POST.get('department', '').strip()
    location = request.POST.get('location', '').strip()
    existing_description = request.POST.get('description', '').strip()
    status = request.POST.get('status', 'open')
    if not title:
        messages.error(request, 'Please enter a job title before enhancing.')
        return render(request, 'ats/job_form.html', {'form': JobForm(request.POST), 'title': 'Add job'})
    try:
        from .ai_utils import enhance_job_description
        enhanced = enhance_job_description(title, department, existing_description)
        form = JobForm(initial={'title': title, 'department': department, 'location': location,
                                'description': enhanced, 'status': status})
        log_action(request, 'ai.job_description_enhanced', detail=f'Title: {title} (create preview)')
        messages.success(request, 'AI-enhanced description loaded — review and save when ready.')
        return render(request, 'ats/job_form.html', {'form': form, 'title': 'Add job'})
    except Exception as exc:
        messages.error(request, f'AI enhancement failed: {exc}')
        return render(request, 'ats/job_form.html', {'form': JobForm(request.POST), 'title': 'Add job'})


@require_http_methods(['POST'])
def job_enhance(request, pk):
    job = get_object_or_404(Job, pk=pk)
    try:
        from .ai_utils import enhance_job_description
        enhanced = enhance_job_description(job.title, job.department, job.description)
        form = JobForm(initial={'title': job.title, 'department': job.department,
                                'location': job.location, 'description': enhanced, 'status': job.status})
        log_action(request, 'ai.job_description_enhanced', job, 'Edit page enhancement')
        messages.success(request, 'AI-enhanced description loaded — review and save when ready.')
        return render(request, 'ats/job_form.html', {'form': form, 'job': job, 'title': f'Edit {job.title}'})
    except Exception as exc:
        messages.error(request, f'AI enhancement failed: {exc}')
        return redirect('job_edit', pk=pk)


@require_http_methods(['POST'])
def application_screen(request, pk):
    application = get_object_or_404(Application.objects.select_related('job', 'candidate'), pk=pk)
    try:
        from .ai_utils import screen_application
        result = screen_application(application.candidate.resume_summary, application.job.title,
                                    application.job.description, application.notes)
        rec = result.get('recommendation', '').upper()
        reasoning = result.get('reasoning', '')
        application.ai_screening_notes = f"[{rec}] {reasoning}" if rec else reasoning
        application.save(update_fields=['ai_screening_notes'])
        log_action(request, 'ai.screened', application, f'Recommendation: {rec}')
        messages.success(request, 'AI screening updated.')
    except Exception as exc:
        messages.error(request, f'AI screening failed: {exc}')
    return redirect('application_edit', pk=pk)


@require_http_methods(['POST'])
def application_score(request, pk):
    application = get_object_or_404(Application.objects.select_related('job', 'candidate'), pk=pk)
    try:
        from .ai_utils import score_candidate_job_match
        match = score_candidate_job_match(application.candidate.resume_summary,
                                          application.job.title, application.job.description)
        application.ai_match_score = match.get('score')
        application.ai_match_rationale = match.get('rationale', '')
        application.save(update_fields=['ai_match_score', 'ai_match_rationale'])
        log_action(request, 'ai.match_scored', application, f'Score: {application.ai_match_score}/100')
        messages.success(request, 'AI match score updated.')
    except Exception as exc:
        messages.error(request, f'AI scoring failed: {exc}')
    return redirect('application_edit', pk=pk)


@require_http_methods(['POST'])
def application_questions(request, pk):
    application = get_object_or_404(Application.objects.select_related('job', 'candidate'), pk=pk)
    if application.status != 'interview':
        messages.error(request, 'Interview questions can only be generated when the application is in the Interview stage.')
        return redirect('application_edit', pk=pk)
    try:
        from .ai_utils import generate_interview_questions
        questions = generate_interview_questions(application.candidate.resume_summary,
                                                  application.job.title, application.job.description)
        application.ai_interview_questions = questions
        application.save(update_fields=['ai_interview_questions'])
        log_action(request, 'ai.interview_questions_generated', application,
                   f'Job: {application.job.title} | Candidate: {application.candidate}')
        messages.success(request, 'Interview questions generated.')
    except Exception as exc:
        messages.error(request, f'Interview question generation failed: {exc}')
    return redirect('application_edit', pk=pk)


def job_match_candidates(request, pk):
    job = get_object_or_404(Job, pk=pk)
    applied_ids = set(job.applications.values_list('candidate_id', flat=True))
    candidates = list(Candidate.objects.exclude(pk__in=applied_ids))
    if not candidates:
        return render(request, 'ats/job_match.html', {'job': job, 'results': [], 'no_candidates': True})

    from .ai_utils import score_candidate_job_match

    def score_one(candidate):
        if not candidate.resume_summary:
            return {'candidate': candidate, 'score': None, 'rationale': ''}
        try:
            result = score_candidate_job_match(candidate.resume_summary, job.title, job.description)
            return {'candidate': candidate, 'score': result.get('score'), 'rationale': result.get('rationale', '')}
        except Exception:
            return {'candidate': candidate, 'score': None, 'rationale': ''}

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(score_one, c): c for c in candidates}
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda x: (x['score'] is None, -(x['score'] or 0)))
    log_action(request, 'ai.job_match_run', job,
               f'Scored {len(results)} candidate(s); top score: {results[0]["score"] if results else "n/a"}')
    return render(request, 'ats/job_match.html', {'job': job, 'results': results, 'no_candidates': False})


def candidate_match_jobs(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    applied_job_ids = set(candidate.applications.values_list('job_id', flat=True))
    jobs = list(Job.objects.filter(status='open').exclude(pk__in=applied_job_ids))
    if not jobs:
        return render(request, 'ats/candidate_match.html',
                      {'candidate': candidate, 'results': [], 'no_jobs': True})

    from .ai_utils import score_candidate_job_match

    def score_one(job):
        if not candidate.resume_summary:
            return {'job': job, 'score': None, 'rationale': ''}
        try:
            result = score_candidate_job_match(candidate.resume_summary, job.title, job.description)
            return {'job': job, 'score': result.get('score'), 'rationale': result.get('rationale', '')}
        except Exception:
            return {'job': job, 'score': None, 'rationale': ''}

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(score_one, j): j for j in jobs}
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda x: (x['score'] is None, -(x['score'] or 0)))
    log_action(request, 'ai.candidate_match_run', candidate,
               f'Scored {len(results)} job(s); top score: {results[0]["score"] if results else "n/a"}')
    return render(request, 'ats/candidate_match.html', {
        'candidate': candidate, 'results': results, 'no_jobs': False,
        'no_resume': not candidate.resume_summary,
    })


@require_http_methods(['POST'])
def candidate_parse_resume(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    if not candidate.resume_file:
        messages.error(request, 'No resume file uploaded for this candidate.')
        return redirect('candidate_detail', pk=pk)
    try:
        from .ai_utils import parse_resume
        summary = parse_resume(candidate.resume_file.path, candidate.resume_summary)
        candidate.resume_summary = summary
        candidate.save(update_fields=['resume_summary'])
        log_action(request, 'ai.resume_parsed', candidate, 'Manual re-parse triggered')
        messages.success(request, 'Resume re-parsed by AI.')
    except Exception as exc:
        messages.error(request, f'Resume parsing failed: {exc}')
    return redirect('candidate_detail', pk=pk)


# ---------------------------------------------------------------------------
# Audit log viewer
# ---------------------------------------------------------------------------

def audit_log_list(request):
    from .models import AuditLog
    action_filter = request.GET.get('action', '')
    logs = AuditLog.objects.select_related('user').order_by('-timestamp')
    if action_filter:
        logs = logs.filter(action__startswith=action_filter)
    # Collect distinct action prefixes for filter pills
    categories = [
        ('', 'All'),
        ('auth', 'Auth'),
        ('job', 'Jobs'),
        ('candidate', 'Candidates'),
        ('application', 'Applications'),
        ('ai', 'AI'),
    ]
    return render(request, 'ats/audit_log.html', {
        'logs': logs[:500],
        'action_filter': action_filter,
        'categories': categories,
    })
