import re

with open('apps/lab/auto_trigger_views.py', 'r') as f:
    content = f.read()

# Fix 1: base_date calculation
old_base_date = """                    base_date = history.from_date
                    if isinstance(base_date, str):
                        base_date = datetime.strptime(base_date, '%Y-%m-%d').date()
                    elif not base_date:
                        base_date = timezone.now().date()"""

new_base_date = """                    # The newly created patient's Registration Date MUST be TODAY / TRIGGER DATE
                    base_date = timezone.now().date()"""
content = content.replace(old_base_date, new_base_date)

# Fix 2: Diagnosis Assignment Error Handling and Logging
old_diagnosis = """                    if new_patient:
                        from apps.lab.models import PatientVisitDiagnosis, DiagnosisDepartmentMapping
                        import random
                        
                        assigned_diagnosis = None
                        if history.department:
                            valid_mappings = list(DiagnosisDepartmentMapping.objects.filter(
                                department=history.department,
                                status='Active'
                            ).select_related('diagnosis'))
                            
                            if valid_mappings:
                                selected = random.choice(valid_mappings)
                                assigned_diagnosis = selected.diagnosis
                                
                                visit = PatientVisit.objects.filter(patient=new_patient).first()
                                if visit:
                                    PatientVisitDiagnosis.objects.create(
                                        visit=visit,
                                        diagnosis=assigned_diagnosis
                                    )
                                    visit.clinical_notes = f"Auto Trigger Generated Patient - Diagnosis: {assigned_diagnosis.name}"
                                    visit.save()

                        msg = f"Stage 1 & 2 Success: Created New Patient {new_patient.patient_id} ({new_patient.name}) [OP: {new_patient.op_number}] at {scheduled_dt.strftime('%H:%M')}"
                        if assigned_diagnosis:
                            msg += f" | Assigned Diagnosis: {assigned_diagnosis.name}"

                        AutoTriggerLog.objects.create(
                            history=history,
                            entry_no=history.processed_entries + 1,
                            entry_date=scheduled_dt.date(),
                            scheduled_at=scheduled_dt,
                            department=history.department.name if history.department else "GENERAL MEDICINE",
                            stage='STAGE 1 — PATIENT CREATION',
                            source_patient=source_patient,
                            new_patient=new_patient,
                            status='Success',
                            message=msg
                        )"""

new_diagnosis = """                    if new_patient:
                        from apps.lab.models import PatientVisitDiagnosis, DiagnosisDepartmentMapping
                        import random
                        
                        assigned_diagnosis = None
                        diagnosis_error = None
                        if history.department:
                            try:
                                valid_mappings = list(DiagnosisDepartmentMapping.objects.filter(
                                    department=history.department,
                                    status='Active'
                                ).select_related('diagnosis'))
                                
                                if valid_mappings:
                                    selected = random.choice(valid_mappings)
                                    assigned_diagnosis = selected.diagnosis
                                    
                                    visit = PatientVisit.objects.filter(patient=new_patient).first()
                                    if visit:
                                        PatientVisitDiagnosis.objects.create(
                                            visit=visit,
                                            diagnosis=assigned_diagnosis
                                        )
                                        visit.clinical_notes = f"Auto Trigger Generated Patient - Diagnosis: {assigned_diagnosis.name}"
                                        visit.save()
                            except Exception as d_err:
                                diagnosis_error = str(d_err)

                        msg = f"Source Patient: {source_patient.patient_id} | New Patient: {new_patient.patient_id} | Trigger Date: {timezone.now().strftime('%d-%b-%Y')}\\n"
                        msg += f"Patient Creation: SUCCESS\\nVisit: SUCCESS\\n"
                        if diagnosis_error:
                            msg += f"Diagnosis: FAILED ({diagnosis_error})"
                        else:
                            msg += "Diagnosis: SUCCESS"

                        AutoTriggerLog.objects.create(
                            history=history,
                            entry_no=history.processed_entries + 1,
                            entry_date=scheduled_dt.date(),
                            scheduled_at=scheduled_dt,
                            department=history.department.name if history.department else "GENERAL MEDICINE",
                            stage='STAGE 1 — PATIENT CREATION',
                            source_patient=source_patient,
                            new_patient=new_patient,
                            status='Success',
                            message=msg
                        )"""
content = content.replace(old_diagnosis, new_diagnosis)

with open('apps/lab/auto_trigger_views.py', 'w') as f:
    f.write(content)
