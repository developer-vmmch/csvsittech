import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "VMMCerp.settings")
django.setup()

from apps.patients.models import PatientVisit
from django.utils import timezone
from django.db import transaction

# Find all patients whose only visit (or visit_no=1) is REVIEW
bad_reviews = PatientVisit.objects.filter(visit_no=1, visit_type='REVIEW')

for review in bad_reviews:
    with transaction.atomic():
        patient = review.patient
        # Create an OP visit for this patient using their registration date
        op_visit = PatientVisit.objects.create(
            patient=patient,
            visit_no=1,
            department=patient.department,
            department_obj=patient.department_obj,
            visit_date=patient.registration_date or timezone.now(),
            visit_type='OP',
            clinical_notes='Historical OP Registration'
        )
        # Update the review visit to be visit_no=2
        review.visit_no = 2
        review.save()
        print(f"Fixed patient {patient.id}: created OP visit #1 and moved REVIEW to #2")

print("Done fixing existing reviews.")
