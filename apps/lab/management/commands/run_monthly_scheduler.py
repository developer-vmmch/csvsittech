import time
import random
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.lab.models import MonthlyTriggerPlan, MonthlyTriggerDailyTarget, MonthlyTriggerExecutionLog, MonthlyTriggerGeneratedPatient
from apps.patients.models import Patient, Department
from apps.lab.synthetic_patient_generator import SyntheticPatientGenerator
from django.db import transaction

class Command(BaseCommand):
    help = 'Runs the Monthly Trigger background scheduler with Target-Aware Mixing'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Started Monthly Trigger Scheduler..."))
        while True:
            try:
                self.process_next_patient()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error in scheduler: {e}"))
            time.sleep(10) # check every 10 seconds for work
            
    def process_next_patient(self):
        now = timezone.localtime()
        today = now.date()
        current_time = now.time()
        
        # Find active plans
        active_plans = MonthlyTriggerPlan.objects.filter(
            status='Active',
            is_saved=True,
            trigger_start_time__lte=current_time,
            trigger_stop_time__gte=current_time,
            automation_start_date__lte=today,
            automation_end_date__gte=today
        )
        
        if not active_plans.exists():
            return
            
        for plan in active_plans:
            # Enforce Interval
            last_log = MonthlyTriggerExecutionLog.objects.filter(
                plan=plan, target_date=today, action='PATIENT CREATED'
            ).order_by('-created_at').first()
            
            if last_log:
                elapsed = (now - last_log.created_at).total_seconds()
                if elapsed < (plan.interval_mins * 60):
                    continue # Not enough time passed for this plan
            
            # Get valid targets for today
            targets = MonthlyTriggerDailyTarget.objects.filter(
                plan=plan, 
                target_date=today,
                status__in=['Not Started', 'Running']
            ).select_related('department')
            
            if not targets.exists():
                continue
                
            # Update status to running
            targets.filter(status='Not Started').update(status='Running')
            
            # Target-aware mixing algorithm
            eligible_targets = []
            for t in targets:
                if t.created_count < t.max_entries:
                    eligible_targets.append(t)
                    
            if not eligible_targets:
                # All completed
                targets.filter(status='Running').update(status='Completed')
                MonthlyTriggerExecutionLog.objects.create(
                    plan=plan, target_date=today, action='DAILY AUTOMATION COMPLETED', status='Completed', reason='All targets reached max'
                )
                continue
                
            # Weight calculation
            weighted_targets = []
            for t in eligible_targets:
                # Priority 1: Below minimum
                is_below_min = t.created_count < t.min_entries
                remaining_to_min = max(0, t.min_entries - t.created_count)
                remaining_to_max = t.max_entries - t.created_count
                
                weight = 10
                if is_below_min:
                    weight += 1000 + remaining_to_min * 10
                else:
                    weight += remaining_to_max
                    
                # Reduce priority if recently selected
                last_dept_log = MonthlyTriggerExecutionLog.objects.filter(
                    plan=plan, target_date=today, action='PATIENT CREATED'
                ).order_by('-created_at').first()
                
                if last_dept_log and 'Department: ' + t.department.name in last_dept_log.reason:
                    weight = weight // 2
                    
                weighted_targets.append((weight, t))
                
            # Select target
            total_weight = sum(w for w, t in weighted_targets)
            r = random.uniform(0, total_weight)
            upto = 0
            selected_target = None
            for w, t in weighted_targets:
                if upto + w >= r:
                    selected_target = t
                    break
                upto += w
                
            if not selected_target:
                selected_target = eligible_targets[0]
                
            # Generate Patient
            self.generate_and_save_patient(plan, selected_target, today)
            
    def generate_and_save_patient(self, plan, target, today):
        # Find source patient
        source_patients = Patient.objects.filter(
            department_obj=target.department,
            registration_date__gte=plan.source_from_date,
            registration_date__lte=plan.source_to_date
        )
        if not source_patients.exists():
            source_patients = Patient.objects.filter(
                registration_date__gte=plan.source_from_date,
                registration_date__lte=plan.source_to_date
            )
            
        if source_patients.exists():
            source_patient = random.choice(list(source_patients))
        else:
            # Fallback source
            source_patient = Patient.objects.filter(department_obj=target.department).first()
            if not source_patient:
                source_patient = Patient.objects.first()
                
        if not source_patient:
            return
            
        gen_data = SyntheticPatientGenerator.generate(source_patient)
        
        with transaction.atomic():
            # Check duplicate (simplified check based on generated data)
            is_dup = Patient.objects.filter(
                name=gen_data['name'], 
                guardian_name=gen_data['guardian_name'],
                mobile_no=gen_data['mobile_no']
            ).exists()
            
            if is_dup:
                target.duplicates_count += 1
                target.save(update_fields=['duplicates_count'])
                MonthlyTriggerExecutionLog.objects.create(
                    plan=plan, target_date=today, action='DUPLICATE DETECTED', status='Duplicate',
                    reason=f"Department: {target.department.name} - Duplicate patient {gen_data['name']}"
                )
                return
                
            # Create new patient
            new_patient = Patient.objects.create(
                title=gen_data['title'],
                name=gen_data['name'],
                gender=source_patient.gender,
                dob=source_patient.dob,
                age_years=source_patient.age_years,
                guardian_title=gen_data['guardian_title'],
                guardian_relationship=source_patient.guardian_relationship,
                guardian_name=gen_data['guardian_name'],
                guardian_phone=gen_data['guardian_phone'],
                street=gen_data['street'],
                village_area=gen_data['village_area'],
                city=gen_data['city'],
                state=gen_data['state'],
                pincode=gen_data['pincode'],
                mobile_no=gen_data['mobile_no'],
                department=target.department.name,
                department_obj=target.department,
                registration_date=today, # NEW PATIENT REGISTRATION DATE = CURRENT AUTOMATION DATE
                auto_trigger_stage='MONTHLY TRIGGER'
            )
            
            # Generate IDs
            new_patient.generate_op_number()
            new_patient.generate_patient_id()
            new_patient.save()
            
            # Link to Target
            MonthlyTriggerGeneratedPatient.objects.create(
                target=target, patient=new_patient, status='Success'
            )
            
            target.created_count += 1
            target.save(update_fields=['created_count'])
            
            # Assign Diagnosis
            self.assign_diagnosis(new_patient, target.department)
            
            MonthlyTriggerExecutionLog.objects.create(
                plan=plan, target_date=today, action='PATIENT CREATED', status='Success',
                reason=f"Department: {target.department.name} - Patient ID: {new_patient.patient_id}"
            )
            
    def assign_diagnosis(self, patient, department):
        from apps.lab.models import DiagnosisDepartmentMapping
        mappings = DiagnosisDepartmentMapping.objects.filter(department=department)
        if mappings.exists():
            mapping = random.choice(list(mappings))
            from apps.patients.models import PatientDiagnosis
            PatientDiagnosis.objects.create(
                patient=patient,
                diagnosis=mapping.diagnosis,
                doctor=mapping.doctor if mapping.doctor else None,
                notes="Assigned by Monthly Trigger"
            )
