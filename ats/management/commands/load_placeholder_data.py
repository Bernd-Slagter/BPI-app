from django.core.management.base import BaseCommand
from ats.models import Job, Candidate, Application


PLACEHOLDER_JOBS = [
    {
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "location": "New York, NY",
        "description": "Build scalable APIs and services. 5+ years Python or Go.",
        "status": "open",
    },
    {
        "title": "Frontend Developer",
        "department": "Engineering",
        "location": "Remote",
        "description": "React/TypeScript. Design systems and accessibility.",
        "status": "open",
    },
    {
        "title": "Product Manager",
        "department": "Product",
        "location": "San Francisco, CA",
        "description": "Own roadmap and stakeholder alignment. 3+ years PM experience.",
        "status": "open",
    },
    {
        "title": "DevOps Engineer",
        "department": "Engineering",
        "location": "Austin, TX",
        "description": "Kubernetes, CI/CD, cloud infrastructure.",
        "status": "on_hold",
    },
    {
        "title": "Data Analyst",
        "department": "Data",
        "location": "Chicago, IL",
        "description": "SQL, dashboards, and reporting. Tableau or Looker.",
        "status": "filled",
    },
]

PLACEHOLDER_CANDIDATES = [
    {"first_name": "Alex", "last_name": "Chen", "email": "alex.chen@example.com", "phone": "+1 555-0101", "resume_summary": "Backend engineer, 6 years Python."},
    {"first_name": "Jordan", "last_name": "Smith", "email": "jordan.smith@example.com", "phone": "+1 555-0102", "resume_summary": "Full-stack, React and Node."},
    {"first_name": "Sam", "last_name": "Williams", "email": "sam.williams@example.com", "phone": "+1 555-0103", "resume_summary": "Product manager, B2B SaaS."},
    {"first_name": "Riley", "last_name": "Johnson", "email": "riley.johnson@example.com", "phone": "+1 555-0104", "resume_summary": "Frontend specialist, design systems."},
    {"first_name": "Casey", "last_name": "Brown", "email": "casey.brown@example.com", "phone": "+1 555-0105", "resume_summary": "DevOps, AWS and K8s."},
    {"first_name": "Morgan", "last_name": "Davis", "email": "morgan.davis@example.com", "phone": "+1 555-0106", "resume_summary": "Data analyst, SQL and Python."},
    {"first_name": "Taylor", "last_name": "Martinez", "email": "taylor.martinez@example.com", "phone": "+1 555-0107", "resume_summary": "Backend and data pipelines."},
]

# (job_index, candidate_index, status) - 0-based indices into PLACEHOLDER_JOBS and PLACEHOLDER_CANDIDATES
PLACEHOLDER_APPLICATIONS = [
    (0, 0, "interview"),   # Alex Chen -> Senior Backend
    (0, 6, "screening"),   # Taylor Martinez -> Senior Backend
    (1, 1, "offer"),       # Jordan Smith -> Frontend
    (1, 3, "submitted"),   # Riley Johnson -> Frontend
    (2, 2, "interview"),   # Sam Williams -> Product Manager
    (2, 3, "rejected"),    # Riley -> PM
    (3, 4, "submitted"),   # Casey Brown -> DevOps
    (4, 5, "hired"),       # Morgan Davis -> Data Analyst (filled)
]


class Command(BaseCommand):
    help = "Load placeholder jobs, candidates, and applications into the ATS database."

    def handle(self, *args, **options):
        self.stdout.write("Loading placeholder data...")

        for data in PLACEHOLDER_JOBS:
            Job.objects.get_or_create(
                title=data["title"],
                defaults={
                    "department": data["department"],
                    "location": data["location"],
                    "description": data["description"],
                    "status": data["status"],
                },
            )
        jobs = list(Job.objects.order_by("id"))
        self.stdout.write(f"  Jobs: {len(jobs)}")

        for data in PLACEHOLDER_CANDIDATES:
            Candidate.objects.get_or_create(
                email=data["email"],
                defaults={
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "phone": data["phone"],
                    "resume_summary": data["resume_summary"],
                },
            )
        candidates = list(Candidate.objects.order_by("id"))
        self.stdout.write(f"  Candidates: {len(candidates)}")

        created = 0
        for ji, ci, status in PLACEHOLDER_APPLICATIONS:
            if ji < len(jobs) and ci < len(candidates):
                _, was_created = Application.objects.get_or_create(
                    job=jobs[ji],
                    candidate=candidates[ci],
                    defaults={"status": status},
                )
                if was_created:
                    created += 1
        self.stdout.write(f"  Applications: {created} new")

        self.stdout.write(self.style.SUCCESS("Placeholder data loaded."))
