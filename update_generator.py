import re

file_path = 'apps/lab/auto_trigger_views.py'
with open(file_path, 'r') as f:
    content = f.read()

# Replace the eligible_patients querying block
old_eligible = """        # Step 1: Find eligible source patients based on Department and Date Range
        eligible_patients = list(Patient.objects.filter(
            department_obj=history.department,
            registration_date__gte=history.from_date,
            registration_date__lte=history.to_date
        ).order_by('id'))

        if not eligible_patients:
            # Fallback to all patients in department
            eligible_patients = list(Patient.objects.filter(
                department_obj=history.department
            ).order_by('id'))

        if not eligible_patients:
            # Fallback to any active patient in system
            eligible_patients = list(Patient.objects.all().order_by('id'))"""

new_eligible = """        # Step 1: Find eligible source patients based on Department and Date Range
        start_date_patients = list(Patient.objects.filter(
            department_obj=history.department,
            registration_date=history.from_date
        ).order_by('id'))
        
        end_date_patients = list(Patient.objects.filter(
            department_obj=history.department,
            registration_date=history.to_date
        ).order_by('id'))
        
        if not start_date_patients:
            start_date_patients = list(Patient.objects.filter(registration_date=history.from_date).order_by('id'))
        if not start_date_patients:
            start_date_patients = list(Patient.objects.all().order_by('id'))
            
        if not end_date_patients:
            end_date_patients = list(Patient.objects.filter(registration_date=history.to_date).order_by('id'))
        if not end_date_patients:
            end_date_patients = list(Patient.objects.all().order_by('id'))
            
        eligible_patients = start_date_patients # For loop bounds and general access"""

content = content.replace(old_eligible, new_eligible)

# Replace the generation loop
old_gen = """                    for attempt in range(1, max_retries + 1):
                        synth_data = SyntheticPatientGenerator.generate(source_patient)
                        
                        norm_name = normalize_text(synth_data['name'])
                        norm_guardian = normalize_text(synth_data['guardian_name'])
                        norm_address = normalize_text(synth_data['street'])"""

new_gen = """                    for attempt in range(1, max_retries + 1):
                        import random
                        start_patient = random.choice(start_date_patients)
                        end_patient = random.choice(end_date_patients)
                        
                        s_name_parts = start_patient.name.split() if start_patient.name else ['Unknown']
                        e_name_parts = end_patient.name.split() if end_patient.name else ['Unknown']
                        
                        first_name = s_name_parts[0]
                        last_name = e_name_parts[-1] if len(e_name_parts) > 1 else e_name_parts[0]
                        new_name = f"{first_name} {last_name}".strip()
                        
                        synth_data = {
                            'name': new_name,
                            'title': start_patient.title or 'Mr',
                            'guardian_title': start_patient.guardian_title or 'Mr',
                            'guardian_name': start_patient.guardian_name or start_patient.name,
                            'street': end_patient.street or 'Main Road',
                            'village_area': end_patient.village_area or 'City Center',
                            'city': end_patient.city or 'Local City',
                            'state': end_patient.state or 'Local State',
                            'pincode': end_patient.pincode or '123456',
                        }
                        
                        # Use start_patient as the source_patient for the rest of the logic
                        source_patient = start_patient
                        
                        norm_name = normalize_text(synth_data['name'])
                        norm_guardian = normalize_text(synth_data['guardian_name'])
                        norm_address = normalize_text(synth_data['street'])"""

content = content.replace(old_gen, new_gen)

# Remove the line `guardian_relationship=source_patient.guardian_relationship if ...` and replace with C/O
content = content.replace(
    "guardian_relationship=source_patient.guardian_relationship if source_patient.guardian_relationship != '-' else 'S/O',",
    "guardian_relationship='C/O',"
)

with open(file_path, 'w') as f:
    f.write(content)
print("Updated generator logic")
