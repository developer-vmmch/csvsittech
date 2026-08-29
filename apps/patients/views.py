from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import MenuAccessRequiredMixin, GranularPermissionRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from .models import Patient, PatientCompany, Department, DepartmentUnit, PatientVisit
from .forms import PatientRegistrationForm, PatientCompanyForm, DepartmentForm, DepartmentUnitForm, PatientVisitForm

from django.contrib.auth import get_user_model

class PatientListView(LoginRequiredMixin, MenuAccessRequiredMixin, GranularPermissionRequiredMixin, ListView):
    menu_key = 'patient_list'
    permission_required = 'patients.patient_list.view'
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 25

    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'excel':
            if not request.user.has_perm_code('patients.patient_list.export'):
                messages.error(request, "Access Denied: You do not have permission to export patients.")
                return redirect('patients:list')
            return self.export_excel(request)
        return super().get(request, *args, **kwargs)

    def export_excel(self, request):
        from openpyxl import Workbook
        from django.http import HttpResponse
        import io

        queryset = self.get_queryset()
        columns_param = request.GET.get('columns', '')
        
        if not columns_param:
            selected_columns = ['Patient ID', 'OP Number', 'Patient Name', 'Gender / Age', 'Department', 'Mobile Number', 'Guardian', 'City / State', 'Registration Date']
        else:
            selected_columns = [c.strip() for c in columns_param.split(',') if c.strip()]
            
        wb = Workbook(write_only=True)
        ws = wb.create_sheet('Patients')
        ws.append(selected_columns)
        
        for p in queryset.iterator(chunk_size=1000):
            row = []
            for col in selected_columns:
                if col == 'Patient ID': row.append(p.patient_id)
                elif col == 'OP Number': row.append(p.op_number or '')
                elif col == 'Patient Title': row.append(p.title)
                elif col == 'First Name': row.append(p.name)
                elif col == 'Last Name': row.append('') 
                elif col == 'Patient Name': row.append(p.name)
                elif col == 'Patient Type': row.append("Auto Trigger" if (p.patient_type == 'D' or p.created_source == 'D') else "Normal Entry")
                elif col == 'Gender': row.append(p.gender)
                elif col == 'Date of Birth': row.append(p.dob.strftime('%Y-%m-%d') if p.dob else '')
                elif col == 'Age' or col == 'Age Display': row.append(p.age_years)
                elif col == 'Gender / Age': row.append(f"{p.gender} / {p.age_years} Y")
                elif col == 'Department': row.append(p.department_obj.name if p.department_obj else (p.department or 'Not Assigned'))
                elif col == 'Mobile Number': row.append(p.mobile_no)
                elif col == 'Alternate Phone': row.append(p.alternate_phone or '')
                elif col == 'Email': row.append(p.email or '')
                elif col == 'Address': row.append(p.street or '')
                elif col == 'City': row.append(p.city)
                elif col == 'State': row.append(p.state)
                elif col == 'City / State': row.append(f"{p.city}, {p.state}")
                elif col == 'Country': row.append(p.country)
                elif col == 'Pincode': row.append(p.pincode or '')
                elif col == 'Blood Group': row.append(p.blood_group or '')
                elif col == 'Marital Status': row.append(p.marital_status or '')
                elif col == 'Guardian Title': row.append(p.guardian_title)
                elif col == 'Guardian Name': row.append(p.guardian_name or '')
                elif col == 'Guardian Relation': row.append(p.guardian_relationship)
                elif col == 'Guardian': 
                    row.append(f"{p.guardian_relationship} {p.guardian_name}".strip() if p.guardian_name else '-')
                elif col == 'Guardian Phone': row.append(p.guardian_phone or '')
                elif col == 'Emergency Contact': row.append('')
                elif col == 'Emergency Phone': row.append(p.emergency_contact_phone or '')
                elif col == 'Registration Date': row.append(p.registration_date.strftime('%Y-%m-%d') if p.registration_date else '')
                else: row.append('')
            ws.append(row)
            
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        today = timezone.localdate().strftime('%Y-%m-%d')
        
        if from_date and to_date:
            filename = f"patients_{from_date}_to_{to_date}.xlsx"
        else:
            filename = f"patients_all_{today}.xlsx"
            
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit():
            return int(page_size)
        return super().get_paginate_by(queryset)

    def get_queryset(self):
        q_search = self.request.GET.get('search', '').strip()
        from_date = self.request.GET.get('from_date', '').strip()
        to_date = self.request.GET.get('to_date', '').strip()
        patient_type = self.request.GET.get('patient_type', 'A').strip().upper()

        queryset = Patient.objects.all().order_by('-id')

        if patient_type in ['O', 'D']:
            queryset = queryset.filter(Q(patient_type=patient_type) | Q(created_source=patient_type))

        if q_search:
            queryset = queryset.filter(
                Q(patient_id__icontains=q_search) |
                Q(name__icontains=q_search) |
                Q(op_number__icontains=q_search)
            )

        if from_date:
            try:
                from_dt = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(registration_date__gte=from_dt)
            except ValueError:
                pass

        if to_date:
            try:
                to_dt = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(registration_date__lte=to_dt)
            except ValueError:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate counts
        total_patients = Patient.objects.count()
        filtered_patients = self.get_queryset().count()
        patient_type = self.request.GET.get('patient_type', 'A').strip().upper()

        context['search'] = self.request.GET.get('search', '')
        context['from_date'] = self.request.GET.get('from_date', '')
        context['to_date'] = self.request.GET.get('to_date', '')
        context['patient_type'] = patient_type
        context['today'] = timezone.localdate().strftime('%Y-%m-%d')
        context['total_patients'] = total_patients
        context['filtered_patients'] = filtered_patients
        context['has_filter'] = bool(context['search'] or context['from_date'] or context['to_date'] or (patient_type and patient_type != 'A'))
        
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('Accept') == 'application/json' or self.request.GET.get('format') == 'json':
            patients = context['patients']
            results = []
            for p in patients:
                results.append({
                    'patient_id': p.patient_id,
                    'op_number': p.op_number,
                    'name': p.name,
                    'gender': p.gender,
                    'age_years': p.age_years,
                    'mobile_no': p.mobile_no,
                    'registration_date': p.registration_date.isoformat() if p.registration_date else None
                })
            return JsonResponse({
                'count': context['filtered_patients'],
                'results': results
            })
        return super().render_to_response(context, **response_kwargs)


class PatientSearchView(LoginRequiredMixin, MenuAccessRequiredMixin, GranularPermissionRequiredMixin, ListView):
    menu_key = 'search_patient'
    permission_required = 'patients.search_patient.view'
    model = Patient
    template_name = 'patients/patient_search.html'
    context_object_name = 'patients'
    paginate_by = 25

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit() and int(page_size) in [10, 25, 50, 100]:
            return int(page_size)
        return super().get_paginate_by(queryset)

    def get_queryset(self):
        try:
            q_name = self.request.GET.get('q_name', '').strip()
            q_from_date = self.request.GET.get('q_from_date', '').strip()
            q_to_date = self.request.GET.get('q_to_date', '').strip()
            q_mobile = self.request.GET.get('q_mobile', '').strip()
            q_aadhar = self.request.GET.get('q_aadhar', '').strip()
            q_abha = self.request.GET.get('q_abha', '').strip()
            q_department = self.request.GET.get('q_department', '').strip()
            q_user = self.request.GET.get('q_user', '').strip()
            q_entry_type = self.request.GET.get('q_entry_type', '').strip().upper()

            has_search_params = any([q_name, q_from_date, q_to_date, q_mobile, q_aadhar, q_abha, q_department, q_user, (q_entry_type and q_entry_type != 'A')])

            if not has_search_params:
                return Patient.objects.none()

            queryset = Patient.objects.all().order_by('-id')

            if q_entry_type in ['O', 'D']:
                queryset = queryset.filter(Q(patient_type=q_entry_type) | Q(created_source=q_entry_type))

            if q_name:
                queryset = queryset.filter(name__icontains=q_name)

            if q_from_date:
                try:
                    from_dt = datetime.strptime(q_from_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date__gte=from_dt)
                except ValueError:
                    pass

            if q_to_date:
                try:
                    to_dt = datetime.strptime(q_to_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(created_at__date__lte=to_dt)
                except ValueError:
                    pass

            if q_mobile:
                queryset = queryset.filter(mobile_no__icontains=q_mobile)

            if q_aadhar:
                queryset = queryset.filter(aadhar_card__icontains=q_aadhar)

            if q_abha:
                queryset = queryset.filter(Q(abha_id__icontains=q_abha) | Q(patient_id__icontains=q_abha) | Q(op_number__icontains=q_abha))

            if q_department:
                if q_department.isdigit():
                    queryset = queryset.filter(department_obj_id=int(q_department))
                else:
                    queryset = queryset.filter(department__icontains=q_department)

            if q_user:
                if q_user == 'system':
                    queryset = queryset.filter(created_by__isnull=True)
                elif q_user.isdigit():
                    queryset = queryset.filter(created_by_id=int(q_user))

            return queryset
        except Exception as e:
            return Patient.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        context['q_name'] = self.request.GET.get('q_name', '')
        context['q_from_date'] = self.request.GET.get('q_from_date', '')
        context['q_to_date'] = self.request.GET.get('q_to_date', '')
        context['q_mobile'] = self.request.GET.get('q_mobile', '')
        context['q_aadhar'] = self.request.GET.get('q_aadhar', '')
        context['q_abha'] = self.request.GET.get('q_abha', '')
        context['q_department'] = self.request.GET.get('q_department', '')
        context['q_user'] = self.request.GET.get('q_user', '')
        context['q_entry_type'] = self.request.GET.get('q_entry_type', 'A').upper()

        Department.seed_defaults()
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        context['users_list'] = User.objects.all().order_by('username')

        context['has_searched'] = any([
            context['q_name'], context['q_from_date'], context['q_to_date'],
            context['q_mobile'], context['q_aadhar'], context['q_abha'],
            context['q_department'], context['q_user'],
            (context['q_entry_type'] and context['q_entry_type'] != 'A')
        ])
        return context


class PatientCreateView(LoginRequiredMixin, MenuAccessRequiredMixin, GranularPermissionRequiredMixin, CreateView):
    menu_key = 'add_patient'
    permission_required = 'patients.patient_list.create'
    model = Patient
    form_class = PatientRegistrationForm
    template_name = 'patients/patient_form.html'
    success_url = reverse_lazy('patients:list')

    def get_initial(self):
        initial = super().get_initial()
        PatientCompany.seed_defaults()
        Department.seed_defaults()

        initial['country'] = 'India'
        initial['state'] = 'Puducherry'
        initial['city'] = 'Karaikal'
        initial['visit_through'] = 'OP'
        initial['category'] = 'CONSULTATION'
        
        # Set default company
        default_company = PatientCompany.objects.filter(code='IND-001').first() or PatientCompany.objects.first()
        if default_company:
            initial['patient_company'] = default_company.id

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        last_patient = Patient.objects.order_by('-id').first()
        context['last_patient_id'] = last_patient.patient_id if last_patient else '26148626'
        context['reg_date'] = timezone.now().strftime('%d/%b/%Y')
        context['reg_time'] = timezone.now().strftime('%H:%M:%S')
        context['is_edit'] = False
        return context

    def post(self, request, *args, **kwargs):
        if 'edit_action' in request.POST:
            # User clicked Edit from the review screen, return to form with existing POST data
            form = self.get_form()
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        patient = form.save(commit=False)
        
        # If not confirmed yet, render the review screen
        if 'confirm_save' not in self.request.POST:
            context = self.get_context_data(form=form)
            # Create a mock patient for the review screen to display
            if patient.department_obj:
                patient.department = patient.department_obj.name
            if patient.unit_obj:
                patient.unit_doctor = patient.unit_obj.unit_name
            if patient.patient_company:
                patient.company_name = patient.patient_company.name
            
            patient.patient_id = "Auto-Generated"
            patient.created_at = timezone.now()
            context['patient'] = patient
            
            # Re-render with a different template (the review template)
            self.template_name = 'patients/patient_registration_review.html'
            return self.render_to_response(context)
        if not patient.patient_id:
            patient.patient_id = Patient.generate_next_patient_id()

        if patient.patient_company:
            patient.company_name = patient.patient_company.name
        else:
            patient.company_name = "INDIVIDUAL"

        if patient.department_obj:
            patient.department = patient.department_obj.name
        if patient.unit_obj:
            patient.unit_doctor = patient.unit_obj.unit_name

        if patient.visit_through == 'IP' and not patient.ipno:
            patient.ipno = Patient.generate_next_ipno()

        patient.save()

        # Automatically create Visit #1 for initial patient registration
        PatientVisit.objects.create(
            patient=patient,
            visit_no=1,
            visit_date=patient.created_at or timezone.now(),
            department_obj=patient.department_obj,
            department=patient.department,
            unit_obj=patient.unit_obj,
            unit_doctor=patient.unit_doctor,
            visit_type=patient.visit_through,
            category=patient.category,
            ipno=patient.ipno,
            clinical_notes=patient.complaint,
            created_by=self.request.user if self.request.user.is_authenticated else None
        )
        
        print_url = reverse('patients:print', kwargs={'pk': patient.pk})
        msg = (
            f'Patient <strong>{patient.name}</strong> (ID: <strong>{patient.patient_id}</strong>) registered successfully! '
            f'<a href="{print_url}" target="_blank" style="margin-left: 12px; background: #0284c7; color: #ffffff; padding: 4px 12px; border-radius: 4px; text-decoration: none; font-weight: 600; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 5px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">'
            f'<i class="bi bi-printer-fill"></i> Print OP Slip</a>'
        )
        messages.success(self.request, msg)
        
        # If user clicked Print or Print OP, redirect directly to print slip page
        if 'print_op' in self.request.POST or 'print' in self.request.POST:
            return redirect('patients:print', pk=patient.pk)

        # Default Save action: Automatically reset form for registering the next patient
        return redirect('patients:add')


class PatientUpdateView(LoginRequiredMixin, MenuAccessRequiredMixin, GranularPermissionRequiredMixin, UpdateView):
    menu_key = 'patient_list'
    permission_required = 'patients.patient_list.update'
    model = Patient
    form_class = PatientRegistrationForm
    template_name = 'patients/patient_form.html'
    success_url = reverse_lazy('patients:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        patient = form.save(commit=False)
        if patient.patient_company:
            patient.company_name = patient.patient_company.name
        else:
            patient.company_name = "INDIVIDUAL"

        if patient.department_obj:
            patient.department = patient.department_obj.name
        if patient.unit_obj:
            patient.unit_doctor = patient.unit_obj.unit_name

        patient.save()
        messages.success(self.request, f"Patient record '{patient.name}' (ID: {patient.patient_id}) updated successfully!")
        return redirect('patients:list')


class PatientPrintView(LoginRequiredMixin, MenuAccessRequiredMixin, DetailView):
    menu_key = 'patient_list'
    model = Patient
    template_name = 'patients/patient_print.html'
    context_object_name = 'patient'


class PatientDeleteView(LoginRequiredMixin, MenuAccessRequiredMixin, GranularPermissionRequiredMixin, DeleteView):
    menu_key = 'patient_list'
    permission_required = 'patients.patient_list.delete'
    model = Patient
    success_url = reverse_lazy('patients:list')

    def post(self, request, *args, **kwargs):
        patient = self.get_object()
        if patient.patient_type == 'D' or patient.created_source == 'D':
            messages.error(request, "Auto Trigger generated patients cannot be deleted.")
            return redirect('patients:list')
        messages.success(request, f"Patient record '{patient.name}' ({patient.patient_id}) deleted successfully.")
        return super().post(request, *args, **kwargs)


def get_department_units(request):
    """API endpoint to get units mapped to a department for dynamic dropdowns"""
    department_id = request.GET.get('department_id')
    units = []
    if department_id:
        units_qs = DepartmentUnit.objects.filter(department_id=department_id, is_active=True).values('id', 'unit_name')
        units = list(units_qs)
    return JsonResponse({'units': units})


class DepartmentListView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'department_list'
    model = Department
    template_name = 'patients/department_list.html'
    context_object_name = 'departments'
    paginate_by = 25
    
    def get_queryset(self):
        return Department.objects.filter(is_active=True)


class DepartmentCreateView(LoginRequiredMixin, MenuAccessRequiredMixin, CreateView):
    menu_key = 'add_department'
    model = Department
    form_class = DepartmentForm
    template_name = 'patients/department_form.html'
    success_url = reverse_lazy('patients:department_list')

    def form_valid(self, form):
        dept = form.save()
        messages.success(self.request, f"Department '{dept.name}' ({dept.code}) created successfully!")
        return super().form_valid(form)


class DepartmentUpdateView(LoginRequiredMixin, MenuAccessRequiredMixin, UpdateView):
    menu_key = 'department_list'
    model = Department
    form_class = DepartmentForm
    template_name = 'patients/department_form.html'
    
    def get_success_url(self):
        return reverse_lazy('patients:department_edit', kwargs={'pk': self.object.pk})
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = self.object.units.all()
        return context

    def form_valid(self, form):
        dept = form.save()
        messages.success(self.request, f"Department '{dept.name}' ({dept.code}) updated successfully!")
        return super().form_valid(form)


class DepartmentDeleteView(LoginRequiredMixin, MenuAccessRequiredMixin, DeleteView):
    menu_key = 'add_department'
    model = Department
    success_url = reverse_lazy('patients:department_list')

    def post(self, request, *args, **kwargs):
        dept = self.get_object()
        messages.success(request, f"Department '{dept.name}' ({dept.code}) deleted successfully.")
        return super().post(request, *args, **kwargs)


class DepartmentUnitCreateView(LoginRequiredMixin, MenuAccessRequiredMixin, CreateView):
    menu_key = 'add_department'
    model = DepartmentUnit
    form_class = DepartmentUnitForm
    template_name = 'patients/unit_form.html'
    success_url = reverse_lazy('patients:department_list')

    def form_valid(self, form):
        unit = form.save()
        messages.success(self.request, f"Unit/Doctor '{unit.unit_name}' mapped to '{unit.department.name}' successfully!")
        return super().form_valid(form)

class DepartmentUnitUpdateView(LoginRequiredMixin, MenuAccessRequiredMixin, UpdateView):
    menu_key = 'add_department'
    model = DepartmentUnit
    form_class = DepartmentUnitForm
    template_name = 'patients/unit_form.html'
    
    def get_success_url(self):
        return reverse_lazy('patients:department_edit', kwargs={'pk': self.object.department.pk})

    def form_valid(self, form):
        unit = form.save()
        messages.success(self.request, f"Unit '{unit.unit_name}' updated successfully!")
        return super().form_valid(form)



class DepartmentUnitDeleteView(LoginRequiredMixin, MenuAccessRequiredMixin, DeleteView):
    menu_key = 'add_department'
    model = DepartmentUnit
    success_url = reverse_lazy('patients:department_list')

    def post(self, request, *args, **kwargs):
        unit = self.get_object()
        messages.success(request, f"Unit '{unit.unit_name}' deleted successfully.")
        return super().post(request, *args, **kwargs)


class PatientCompanyListView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'patient_companies'
    model = PatientCompany
    template_name = 'patients/company_list.html'
    context_object_name = 'companies'
    paginate_by = 25


class PatientCompanyCreateView(LoginRequiredMixin, MenuAccessRequiredMixin, CreateView):
    menu_key = 'add_company'
    model = PatientCompany
    form_class = PatientCompanyForm
    template_name = 'patients/company_form.html'
    success_url = reverse_lazy('patients:company_list')

    def form_valid(self, form):
        company = form.save()
        messages.success(self.request, f"Patient Company '{company.name}' ({company.code}) created successfully!")
        return super().form_valid(form)


class PatientCompanyDeleteView(LoginRequiredMixin, MenuAccessRequiredMixin, DeleteView):
    menu_key = 'add_company'
    model = PatientCompany
    success_url = reverse_lazy('patients:company_list')

    def post(self, request, *args, **kwargs):
        company = self.get_object()
        messages.success(request, f"Patient Company '{company.name}' ({company.code}) deleted successfully.")
        return super().post(request, *args, **kwargs)


class OPCensusView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    menu_key = 'op_census'
    template_name = 'patients/op_census.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        selected_date_str = self.request.GET.get('census_date', '').strip()
        if selected_date_str:
            try:
                census_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            except ValueError:
                census_date = datetime.now().date()
        else:
            census_date = datetime.now().date()

        dept_id = self.request.GET.get('department', '').strip()
        category = self.request.GET.get('category', '').strip()

        qs = Patient.objects.filter(created_at__date=census_date).order_by('-id')

        if dept_id:
            qs = qs.filter(Q(department_obj_id=dept_id) | Q(department__iexact=dept_id))

        if category:
            qs = qs.filter(category=category)

        total_op = qs.count()
        male_count = qs.filter(Q(gender__iexact='male') | Q(gender__iexact='m')).count()
        female_count = qs.filter(Q(gender__iexact='female') | Q(gender__iexact='f')).count()
        other_count = qs.filter(Q(gender__iexact='other') | Q(gender__iexact='o')).count()
        child_count = qs.filter(age_years__lt=12).count()
        consultation_count = qs.filter(category='CONSULTATION').count()
        revisit_count = qs.filter(category='RE_CONSULTATION').count()
        emergency_count = qs.filter(category='EMERGENCY').count()

        # Date-Based Census Metrics: New OP, Review OP, IP Admissions, Discharged Patients
        new_op_count = total_op  # Matches total OP registrations on census_date & sum of department table

        review_op_qs = PatientVisit.objects.filter(visit_date__date=census_date, visit_type='OP').exclude(visit_no=1)
        ip_admissions_qs = PatientVisit.objects.filter(Q(visit_date__date=census_date, visit_type='IP') | Q(patient__created_at__date=census_date, patient__visit_through='IP')).distinct()
        discharged_qs = PatientVisit.objects.filter(discharge_date=census_date)

        if dept_id:
            if dept_id.isdigit():
                review_op_qs = review_op_qs.filter(department_obj_id=int(dept_id))
                ip_admissions_qs = ip_admissions_qs.filter(department_obj_id=int(dept_id))
                discharged_qs = discharged_qs.filter(department_obj_id=int(dept_id))
            else:
                review_op_qs = review_op_qs.filter(department__icontains=dept_id)
                ip_admissions_qs = ip_admissions_qs.filter(department__icontains=dept_id)
                discharged_qs = discharged_qs.filter(department__icontains=dept_id)

        review_op_count = review_op_qs.count()
        ip_admissions_count = ip_admissions_qs.count()
        discharged_count = discharged_qs.count()

        departments = Department.objects.filter(is_active=True)
        dept_census = []
        for d in departments:
            d_qs = qs.filter(Q(department_obj=d) | Q(department__iexact=d.name))
            d_count = d_qs.count()
            if d_count > 0:
                d_m = d_qs.filter(Q(gender__iexact='male') | Q(gender__iexact='m')).count()
                d_f = d_qs.filter(Q(gender__iexact='female') | Q(gender__iexact='f')).count()
                d_o = d_qs.filter(Q(gender__iexact='other') | Q(gender__iexact='o')).count()
                d_child = d_qs.filter(age_years__lt=12).count()
                d_pct = round((d_count / total_op * 100), 1) if total_op > 0 else 0
                
                dept_census.append({
                    'dept': d,
                    'total': d_count,
                    'male': d_m,
                    'female': d_f,
                    'other': d_o,
                    'child': d_child,
                    'percentage': d_pct,
                    'unit_count': d.units.filter(is_active=True).count(),
                })

        context['census_date'] = census_date.strftime('%Y-%m-%d')
        context['display_date'] = census_date.strftime('%A, %d %B %Y')
        context['selected_dept'] = dept_id
        context['selected_category'] = category
        context['departments'] = departments
        context['categories'] = Patient.CategoryChoices.choices
        context['patients'] = qs
        context['total_op'] = total_op
        context['new_op_count'] = new_op_count
        context['review_op_count'] = review_op_count
        context['ip_admissions_count'] = ip_admissions_count
        context['discharged_count'] = discharged_count
        context['male_count'] = male_count
        context['female_count'] = female_count
        context['other_count'] = other_count
        context['child_count'] = child_count
        context['consultation_count'] = consultation_count
        context['revisit_count'] = revisit_count
        context['emergency_count'] = emergency_count
        context['dept_census'] = dept_census

        # User / Counter Staff OP Registration Breakdown (Only show users with count > 0)
        from django.contrib.auth import get_user_model
        User = get_user_model()

        users_census = []
        all_users = User.objects.filter(is_active=True)
        for u in all_users:
            u_qs = qs.filter(created_by=u)
            u_count = u_qs.count()
            if u_count > 0:
                u_m = u_qs.filter(Q(gender__iexact='male') | Q(gender__iexact='m')).count()
                u_f = u_qs.filter(Q(gender__iexact='female') | Q(gender__iexact='f')).count()
                u_o = u_qs.filter(Q(gender__iexact='other') | Q(gender__iexact='o')).count()
                u_child = u_qs.filter(age_years__lt=12).count()
                u_pct = round((u_count / total_op * 100), 1) if total_op > 0 else 0

                users_census.append({
                    'user': u,
                    'display_name': u.get_full_name() or u.username,
                    'username': u.username,
                    'employee_id': u.employee_id or '--',
                    'role_display': u.get_role_display(),
                    'department': u.department or '--',
                    'total': u_count,
                    'male': u_m,
                    'female': u_f,
                    'other': u_o,
                    'child': u_child,
                    'percentage': u_pct,
                })

        unassigned_qs = qs.filter(created_by__isnull=True)
        unassigned_count = unassigned_qs.count()
        if unassigned_count > 0:
            u_m = unassigned_qs.filter(Q(gender__iexact='male') | Q(gender__iexact='m')).count()
            u_f = unassigned_qs.filter(Q(gender__iexact='female') | Q(gender__iexact='f')).count()
            u_o = unassigned_qs.filter(Q(gender__iexact='other') | Q(gender__iexact='o')).count()
            u_child = unassigned_qs.filter(age_years__lt=12).count()
            u_pct = round((unassigned_count / total_op * 100), 1) if total_op > 0 else 0
            users_census.append({
                'user': None,
                'display_name': 'System / Initial OP Registrations',
                'username': 'system',
                'employee_id': '--',
                'role_display': 'System Entry',
                'department': '--',
                'total': unassigned_count,
                'male': u_m,
                'female': u_f,
                'other': u_o,
                'child': u_child,
                'percentage': u_pct,
            })

        users_census.sort(key=lambda x: x['total'], reverse=True)
        context['users_census'] = users_census

        return context


class PatientReviewView(LoginRequiredMixin, MenuAccessRequiredMixin, TemplateView):
    menu_key = 'review'
    template_name = 'patients/patient_review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_id = self.request.GET.get('patient_id', '').strip()
        patient = None

        if search_id:
            patient = Patient.objects.filter(
                Q(patient_id__iexact=search_id) | Q(ipno__iexact=search_id)
            ).first()
            if not patient:
                messages.warning(self.request, f"No patient record found for ID / IPNO '{search_id}'.")

        context['patient'] = patient
        context['search_id'] = search_id
        context['all_patients'] = Patient.objects.all().order_by('-id')[:50]
        context['now'] = timezone.now()

        if patient:
            # Ensure at least Visit #1 exists for legacy patient records
            if not patient.visits.exists():
                PatientVisit.objects.create(
                    patient=patient,
                    visit_no=1,
                    visit_date=patient.created_at or timezone.now(),
                    department_obj=patient.department_obj,
                    department=patient.department,
                    unit_obj=patient.unit_obj,
                    unit_doctor=patient.unit_doctor,
                    visit_type=patient.visit_through,
                    category=patient.category,
                    ipno=patient.ipno,
                    clinical_notes=patient.complaint,
                    created_by=patient.created_by
                )

            context['visits'] = patient.visits.all().order_by('-visit_no')
            context['last_visit'] = patient.visits.order_by('-visit_no').first()
            next_ip = Patient.generate_next_ipno()
            context['next_ipno'] = next_ip
            context['visit_form'] = PatientVisitForm(initial={
                'department_obj': patient.department_obj,
                'unit_obj': patient.unit_obj,
                'visit_type': 'OP',
                'category': 'RE_CONSULTATION',
                'ipno': '',
            })

        return context

    def post(self, request, *args, **kwargs):
        patient_id = request.POST.get('patient_id_hidden') or request.POST.get('patient_id')
        patient = get_object_or_404(Patient, pk=patient_id)

        if request.POST.get('action') == 'update_centre':
            new_centre = request.POST.get('centre')
            if new_centre in [c[0] for c in Patient.CentreChoices.choices]:
                patient.centre = new_centre
                patient.save()
                messages.success(request, f"Patient centre updated to '{patient.get_centre_display()}'!")
                return redirect(f"{reverse('patients:review')}?patient_id={patient.patient_id}")

        form = PatientVisitForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.patient = patient

            last_visit = patient.visits.order_by('-visit_no').first()
            visit.visit_no = (last_visit.visit_no + 1) if last_visit else 1

            if visit.department_obj:
                visit.department = visit.department_obj.name
            if visit.unit_obj:
                visit.unit_doctor = visit.unit_obj.unit_name

            # Assign IP Number ONLY when visit_type is IP
            if visit.visit_type == 'IP':
                if not visit.ipno or visit.ipno.strip() == '':
                    visit.ipno = Patient.generate_next_ipno()
            else:
                visit.ipno = ''

            if request.user.is_authenticated:
                visit.created_by = request.user

            visit.save()

            # Update latest patient metadata
            patient.department_obj = visit.department_obj
            patient.department = visit.department
            patient.unit_obj = visit.unit_obj
            patient.unit_doctor = visit.unit_doctor
            if visit.centre:
                patient.centre = visit.centre
            if visit.visit_type:
                patient.visit_through = visit.visit_type
            if visit.ipno:
                patient.ipno = visit.ipno
            patient.save()

            messages.success(request, f"New Visit #{visit.visit_no} recorded successfully for patient '{patient.name}' ({patient.patient_id})!")
            return redirect(f"{reverse('patients:review')}?patient_id={patient.patient_id}")
        else:
            messages.error(request, "Failed to log visit. Please select required Department and Doctor.")
            return redirect(f"{reverse('patients:review')}?patient_id={patient.patient_id}")


class PatientMedicalHistoryPrintView(LoginRequiredMixin, MenuAccessRequiredMixin, DetailView):
    menu_key = 'review'
    model = Patient
    template_name = 'patients/medical_history_print.html'
    context_object_name = 'patient'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['visits'] = self.object.visits.all().order_by('-visit_no')
        context['last_visit'] = context['visits'].first()
        context['now'] = timezone.now()
        return context


class PatientReviewReportView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'review_report'
    model = PatientVisit
    template_name = 'patients/review_report.html'
    context_object_name = 'visits'
    paginate_by = 25

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit() and int(page_size) in [10, 25, 50, 100]:
            return int(page_size)
        return super().get_paginate_by(queryset)

    def get_queryset(self):
        queryset = PatientVisit.objects.select_related('patient', 'department_obj', 'unit_obj', 'created_by').order_by('-id')

        q_patient = self.request.GET.get('q_patient', '').strip()
        q_from_date = self.request.GET.get('q_from_date', '').strip()
        q_to_date = self.request.GET.get('q_to_date', '').strip()
        q_department = self.request.GET.get('q_department', '').strip()
        q_visit_type = self.request.GET.get('q_visit_type', '').strip()
        q_centre = self.request.GET.get('q_centre', '').strip()
        q_user = self.request.GET.get('q_user', '').strip()

        if q_patient:
            queryset = queryset.filter(
                Q(patient__patient_id__icontains=q_patient) |
                Q(patient__name__icontains=q_patient) |
                Q(ipno__icontains=q_patient)
            )

        if q_from_date:
            try:
                from_dt = datetime.strptime(q_from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(visit_date__date__gte=from_dt)
            except ValueError:
                pass

        if q_to_date:
            try:
                to_dt = datetime.strptime(q_to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(visit_date__date__lte=to_dt)
            except ValueError:
                pass

        if q_department:
            if q_department.isdigit():
                queryset = queryset.filter(department_obj_id=int(q_department))
            else:
                queryset = queryset.filter(department__icontains=q_department)

        if q_visit_type:
            queryset = queryset.filter(visit_type=q_visit_type)

        if q_centre:
            queryset = queryset.filter(Q(centre=q_centre) | Q(patient__centre=q_centre))

        if q_user:
            if q_user == 'system':
                queryset = queryset.filter(created_by__isnull=True)
            elif q_user.isdigit():
                queryset = queryset.filter(created_by_id=int(q_user))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        qs = self.get_queryset()

        context['q_patient'] = self.request.GET.get('q_patient', '')
        context['q_from_date'] = self.request.GET.get('q_from_date', '')
        context['q_to_date'] = self.request.GET.get('q_to_date', '')
        context['q_department'] = self.request.GET.get('q_department', '')
        context['q_visit_type'] = self.request.GET.get('q_visit_type', '')
        context['q_centre'] = self.request.GET.get('q_centre', '')
        context['q_user'] = self.request.GET.get('q_user', '')

        # KPI Metrics
        context['total_visits'] = qs.count()
        context['op_visits_count'] = qs.filter(visit_type='OP').count()
        context['ip_visits_count'] = qs.filter(visit_type='IP').count()
        context['unique_patients_count'] = qs.values('patient').distinct().count()

        Department.seed_defaults()
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        context['users_list'] = User.objects.all().order_by('username')
        context['centre_choices'] = Patient.CentreChoices.choices

        context['has_filters'] = any([
            context['q_patient'], context['q_from_date'], context['q_to_date'],
            context['q_department'], context['q_visit_type'], context['q_centre'], context['q_user']
        ])
        return context
