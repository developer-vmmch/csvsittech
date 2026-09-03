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
        
        # 1. Check for plans that should start today
        pending_plans = MonthlyTriggerPlan.objects.filter(
            status__in=['Scheduled', 'Active'],
            is_saved=True,
            trigger_start_time__lte=current_time,
            trigger_stop_time__gte=current_time,
            automation_start_date__lte=today,
            automation_end_date__gte=today
        )
        for plan in pending_plans:
            plan.status = 'Running'
            plan.save(update_fields=['status'])
            MonthlyTriggerExecutionLog.objects.create(
                plan=plan, target_date=today, action='AUTOMATION STARTED', status='Running',
                reason='Scheduled start time reached'
            )
            
        # 2. Check for running plans that should stop (daily stop time reached or ended)
        running_plans = MonthlyTriggerPlan.objects.filter(status='Running', is_saved=True)
        for plan in running_plans:
            is_end_of_plan = plan.automation_end_date and today >= plan.automation_end_date and current_time > plan.trigger_stop_time
            is_end_of_day = current_time > plan.trigger_stop_time
            
            if is_end_of_plan or is_end_of_day:
                plan.status = 'Completed' if is_end_of_plan else 'Scheduled'
                plan.save(update_fields=['status'])
                
                MonthlyTriggerDailyTarget.objects.filter(
                    plan=plan, target_date=today, status__in=['Not Started', 'Running']
                ).update(status='Completed')
                
                MonthlyTriggerExecutionLog.objects.create(
                    plan=plan, target_date=today, action='DAILY AUTOMATION STOPPED', status='Completed',
                    reason='Daily stop time reached'
                )

        # 3. Find active running plans
        active_plans = MonthlyTriggerPlan.objects.filter(
            status='Running',
            is_saved=True,
            trigger_start_time__lte=current_time,
            trigger_stop_time__gte=current_time,
            automation_start_date__lte=today,
            automation_end_date__gte=today
        )
        
        if not active_plans.exists():
            return
            
        # Get minimum configured interval across all active plans (default 15s)
        min_interval_mins = min([p.interval_mins for p in active_plans]) if active_plans else 0.25
        global_interval_secs = max(1, int(min_interval_mins * 60))
            
        # Enforce GLOBAL Interval across the entire system
        last_log = MonthlyTriggerExecutionLog.objects.filter(
            target_date=today, action__in=['PATIENT CREATED', 'DUPLICATE DETECTED']
        ).order_by('-created_at').first()
        
        if last_log:
            elapsed = (now - last_log.created_at).total_seconds()
            if elapsed < global_interval_secs:
                return # Global interval not yet elapsed
        
        # Get valid targets for today across ALL active plans
        targets = MonthlyTriggerDailyTarget.objects.filter(
            plan__in=active_plans, 
            target_date=today,
            status__in=['Not Started', 'Running']
        ).select_related('department', 'plan')
        
        if not targets.exists():
            return
            
        # Update status to running
        targets.filter(status='Not Started').update(status='Running')
        
        # Target-aware mixing algorithm
        eligible_targets = []
        below_min_targets = []
        for t in targets:
            total_created = t.new_op_created + t.review_created
            if total_created < t.max_entries:
                eligible_targets.append(t)
            if t.new_op_created < t.new_op_target or t.review_created < t.review_target:
                below_min_targets.append(t)
                
        if not eligible_targets:
            # All completed for these targets
            targets.filter(status='Running').update(status='Completed')
            # Mark plans as completed if all their targets are done
            for plan in active_plans:
                MonthlyTriggerExecutionLog.objects.create(
                    plan=plan, target_date=today, action='DAILY AUTOMATION COMPLETED', status='Completed', reason='All targets reached max'
                )
            return
                
        # Phase 1: If any department is below minimum, ONLY consider those
        targets_to_consider = below_min_targets if below_min_targets else eligible_targets
            
        # Weight calculation
        weighted_targets = []
        for t in targets_to_consider:
            total_created = t.new_op_created + t.review_created
            remaining_to_min = max(0, t.min_entries - total_created)
            remaining_to_max = t.max_entries - total_created
            
            if below_min_targets:
                # Phase 1 Weighting
                weight = 100 + remaining_to_min * 10
            else:
                # Phase 2 Weighting
                weight = 10 + remaining_to_max
                
            # Reduce priority if recently selected to enforce shuffling globally
            last_dept_log = MonthlyTriggerExecutionLog.objects.filter(
                target_date=today, action='PATIENT CREATED'
            ).order_by('-created_at').first()
            
            if last_dept_log and last_dept_log.reason and 'Department: ' + t.department.name in last_dept_log.reason:
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
            selected_target = targets_to_consider[0]
            
        # Determine OP Type
        is_new_op_below = selected_target.new_op_created < selected_target.new_op_target
        is_review_below = selected_target.review_created < selected_target.review_target
        
        if is_new_op_below and is_review_below:
            op_type = 'NEW OP' if random.random() < 0.8 else 'REVIEW'
        elif is_new_op_below:
            op_type = 'NEW OP'
        elif is_review_below:
            op_type = 'REVIEW'
        else:
            op_type = 'NEW OP'
            
        # Generate or Review Patient
        plan = selected_target.plan
        self.generate_and_save_patient(plan, selected_target, today, op_type)
            
    def generate_and_save_patient(self, plan, target, today, op_type):
        if op_type == 'REVIEW':
            # Select an existing 'D' patient from the review source month
            if plan.review_source_month_year:
                try:
                    year_str, month_str = plan.review_source_month_year.split('-')
                    year, month = int(year_str), int(month_str)
                    
                    source_patients = Patient.objects.filter(
                        patient_type='D',
                        department_obj=target.department,
                        registration_date__year=year,
                        registration_date__month=month
                    )
                except:
                    source_patients = Patient.objects.filter(patient_type='D', department_obj=target.department)
            else:
                source_patients = Patient.objects.filter(patient_type='D', department_obj=target.department)
                
            if not source_patients.exists():
                # Fallback to any D patient
                source_patients = Patient.objects.filter(patient_type='D')
                if not source_patients.exists():
                    # No D patients available to review, fallback to NEW OP
                    op_type = 'NEW OP'
                    
        if op_type == 'REVIEW':
            # We want to randomly pick a patient but not repeat them in the same run if possible
            # To optimize, we just pick randomly.
            source_patient = random.choice(list(source_patients))
            
            with transaction.atomic():
                # Check Duplicate Review
                is_dup_review = MonthlyTriggerGeneratedPatient.objects.filter(
                    target=target,
                    patient=source_patient,
                    op_type='REVIEW'
                ).exists()
                
                if is_dup_review:
                    target.duplicates_count += 1
                    target.save(update_fields=['duplicates_count'])
                    MonthlyTriggerExecutionLog.objects.create(
                        plan=plan, target_date=today, action='DUPLICATE DETECTED', status='Duplicate',
                        reason=f"Department: {target.department.name} - Duplicate REVIEW patient {source_patient.patient_id}",
                        duplicates_count=1
                    )
                    return
                
                # Assign a review diagnosis visit
                age_group, diagnosis, err = self.assign_diagnosis(source_patient, target.department, today, 'REVIEW')
                
                # Log success
                MonthlyTriggerGeneratedPatient.objects.create(
                    target=target, patient=source_patient, status='Success', op_type='REVIEW',
                    age_group_snapshot=age_group.label if age_group else None,
                    diagnosis_snapshot=diagnosis.name if diagnosis else None
                )
                target.review_created += 1
                target.created_count += 1
                target.save(update_fields=['review_created', 'created_count'])
                
                MonthlyTriggerExecutionLog.objects.create(
                    plan=plan, target_date=today, action='PATIENT CREATED', status='Success',
                    reason=f"Department: {target.department.name} - REVIEW Patient ID: {source_patient.patient_id}" + (f" (Diag: {diagnosis.name})" if diagnosis else " (No Diag)"),
                    review_completed_count=1
                )
                if err:
                    MonthlyTriggerExecutionLog.objects.create(
                        plan=plan, target_date=today, action='DIAGNOSIS WARNING', status='Warning',
                        reason=f"Patient {source_patient.patient_id}: {err}"
                    )
            return

        # NEW OP LOGIC
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
                mobile_no=''
            ).exists()
            
            if is_dup:
                target.duplicates_count += 1
                target.save(update_fields=['duplicates_count'])
                MonthlyTriggerExecutionLog.objects.create(
                    plan=plan, target_date=today, action='DUPLICATE DETECTED', status='Duplicate',
                    reason=f"Department: {target.department.name} - Duplicate patient {gen_data['name']}",
                    duplicates_count=1
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
                mobile_no='',
                patient_type='D',
                created_source='D',
                department=target.department.name,
                department_obj=target.department,
                registration_date=today, # NEW PATIENT REGISTRATION DATE = CURRENT AUTOMATION DATE
                auto_trigger_stage='MONTHLY TRIGGER'
            )
            
            new_patient.op_number = Patient.generate_next_op_number()
            new_patient.save()
            
            # Assign Diagnosis
            age_group, diagnosis, err = self.assign_diagnosis(new_patient, target.department, today, 'NEW OP')

            # Link to Target
            MonthlyTriggerGeneratedPatient.objects.create(
                target=target, patient=new_patient, status='Success', op_type='NEW OP',
                age_group_snapshot=age_group.label if age_group else None,
                diagnosis_snapshot=diagnosis.name if diagnosis else None
            )
            
            target.new_op_created += 1
            target.created_count += 1
            target.save(update_fields=['new_op_created', 'created_count'])
            
            MonthlyTriggerExecutionLog.objects.create(
                plan=plan, target_date=today, action='PATIENT CREATED', status='Success',
                reason=f"Department: {target.department.name} - Patient ID: {new_patient.patient_id}" + (f" (Diag: {diagnosis.name})" if diagnosis else " (No Diag)"),
                new_op_created_count=1
            )
            if err:
                MonthlyTriggerExecutionLog.objects.create(
                    plan=plan, target_date=today, action='DIAGNOSIS WARNING', status='Warning',
                    reason=f"Patient {new_patient.patient_id}: {err}"
                )
            
    def assign_diagnosis(self, patient, department, target_date, op_type='NEW OP'):
        from apps.lab.models import DiagnosisDepartmentMapping, PatientVisitDiagnosis, AgeGroup
        from apps.patients.models import PatientVisit
        from django.utils import timezone
        
        # 1. Determine Patient Age Group
        patient_age_days = (patient.age_years or 0) * 365
        matched_age_group = None
        
        for ag in AgeGroup.objects.filter(is_active=True).order_by('sort_order'):
            min_days = 0
            if ag.min_age_value:
                if ag.min_age_unit == 'Years': min_days = ag.min_age_value * 365
                elif ag.min_age_unit == 'Months': min_days = ag.min_age_value * 30
                else: min_days = ag.min_age_value
                
            max_days = float('inf')
            if ag.max_age_value:
                if ag.max_age_unit == 'Years': max_days = ag.max_age_value * 365 + 364
                elif ag.max_age_unit == 'Months': max_days = ag.max_age_value * 30 + 29
                else: max_days = ag.max_age_value
                
            if min_days <= patient_age_days <= max_days:
                if ag.gender == 'All' or ag.gender == patient.gender:
                    matched_age_group = ag
                    break
        
        # 2. Find Diagnosis Mapping
        mappings = DiagnosisDepartmentMapping.objects.filter(department=department, status='Active')
        
        selected_mapping = None
        if matched_age_group:
            exact_mappings = mappings.filter(age_group=matched_age_group)
            if exact_mappings.exists():
                selected_mapping = random.choice(list(exact_mappings))
                
        if not selected_mapping:
            # Fallback to department-level mapping
            dept_mappings = mappings.filter(age_group__isnull=True)
            if dept_mappings.exists():
                selected_mapping = random.choice(list(dept_mappings))
                
        if not selected_mapping:
            return matched_age_group, None, "Diagnosis mapping not found"
            
        # 3. Create or find visit
        if op_type == 'REVIEW':
            latest_visit = PatientVisit.objects.filter(patient=patient).order_by('-visit_no').first()
            if not latest_visit:
                latest_visit = PatientVisit.objects.create(
                    patient=patient,
                    visit_no=1,
                    department=patient.department,
                    department_obj=patient.department_obj,
                    visit_date=timezone.make_aware(datetime.combine(patient.registration_date, datetime.min.time())),
                    visit_type='OP',
                    clinical_notes='Historical OP Registration'
                )
                
            next_visit_no = latest_visit.visit_no + 1
            now = timezone.localtime()
            visit_datetime = timezone.make_aware(datetime.combine(target_date, now.time()))
            
            visit = PatientVisit.objects.create(
                patient=patient,
                visit_no=next_visit_no,
                department=department.name,
                department_obj=department,
                visit_date=visit_datetime,
                visit_type='REVIEW',
                clinical_notes='Automated Monthly Trigger Review'
            )
        else:
            visit = PatientVisit.objects.filter(patient=patient).first()
            if not visit:
                now = timezone.localtime()
                visit_datetime = timezone.make_aware(datetime.combine(target_date, now.time()))
                visit = PatientVisit.objects.create(
                    patient=patient,
                    visit_no=1,
                    department=department.name,
                    department_obj=department,
                    visit_date=visit_datetime,
                    visit_type='OP'
                )
            
        # 4. Save Diagnosis against the visit
        PatientVisitDiagnosis.objects.create(
            visit=visit,
            diagnosis=selected_mapping.diagnosis
        )
        
        return matched_age_group, selected_mapping.diagnosis, None
