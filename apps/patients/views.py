
from django.utils import timezone
from datetime import timedelta

def get_default_date_range(request, from_param='from_date', to_param='to_param'):
    from_raw = request.GET.get(from_param)
    to_raw = request.GET.get(to_param)
    
    if from_raw is None:
        from_date = (timezone.localdate() - timedelta(days=6)).strftime('%Y-%m-%d')
    else:
        from_date = from_raw.strip()
        
    if to_raw is None:
        to_date = timezone.localdate().strftime('%Y-%m-%d')
    else:
        to_date = to_raw.strip()
        
    return from_date, to_date

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from apps.core.mixins import MenuAccessRequiredMixin, GranularPermissionRequiredMixin
from django.db.models import Q, Count
import csv
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime
from .models import Patient, PatientCompany, Department, DepartmentUnit, PatientVisit, BranchTransferRequest
from .forms import PatientRegistrationForm, PatientCompanyForm, DepartmentForm, DepartmentUnitForm, PatientVisitForm, BranchTransferRequestForm

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
                elif col == 'IP Department': row.append(p.active_ip_admission.department if p.active_ip_admission else (p.department if p.is_admitted_inpatient else ''))
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
                elif col == 'Registration Date': 
                    if p.registration_date:
                        date_str = p.registration_date.strftime('%Y-%m-%d')
                        if p.created_at:
                            time_str = timezone.localtime(p.created_at).strftime('%I:%M %p')
                            row.append(f"{date_str} ({time_str})")
                        else:
                            row.append(date_str)
                    else:
                        row.append('')
                else: row.append('')
            ws.append(row)
            
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        from_date, to_date = get_default_date_range(request, 'from_date', 'to_date')
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
        from_date, to_date = get_default_date_range(self.request, 'from_date', 'to_date')
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
            
        q_department = self.request.GET.get('department', '').strip()
        if q_department:
            queryset = queryset.filter(Q(department__iexact=q_department) | Q(department_obj__name__iexact=q_department))

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
        context['from_date'], context['to_date'] = get_default_date_range(self.request, 'from_date', 'to_date')
        context['patient_type'] = patient_type
        context['department'] = self.request.GET.get('department', '').strip()
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        context['today'] = timezone.localdate().strftime('%Y-%m-%d')
        context['total_patients'] = total_patients
        context['filtered_patients'] = filtered_patients
        context['has_filter'] = bool(context['search'] or context['from_date'] or context['to_date'] or (patient_type and patient_type != 'A') or context['department'])
        
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
            q_from_date, q_to_date = get_default_date_range(self.request, 'q_from_date', 'q_to_date')
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
                    queryset = queryset.filter(registration_date__gte=from_dt)
                except ValueError:
                    pass

            if q_to_date:
                try:
                    to_dt = datetime.strptime(q_to_date, '%Y-%m-%d').date()
                    queryset = queryset.filter(registration_date__lte=to_dt)
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
        context['q_from_date'], context['q_to_date'] = get_default_date_range(self.request, 'q_from_date', 'q_to_date')
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
        
        is_emer = False
        cat = str(patient.category or '').upper()
        if cat in ['EMERGENCY', 'CASUALTY']:
            is_emer = True
        elif patient.department_obj and any(term in patient.department_obj.name.upper() for term in ['EMERGENCY', 'CASUALTY']):
            is_emer = True
        elif patient.department and any(term in str(patient.department).upper() for term in ['EMERGENCY', 'CASUALTY']):
            is_emer = True

        if not patient.patient_id:
            patient.patient_id = Patient.generate_next_patient_id(is_emergency=is_emer)
        elif is_emer and not str(patient.patient_id).upper().startswith('E'):
            patient.patient_id = f"E{patient.patient_id}"

        if patient.patient_company:
            patient.company_name = patient.patient_company.name
        else:
            patient.company_name = "INDIVIDUAL"

        if patient.department_obj:
            patient.department = patient.department_obj.name
        if patient.unit_obj:
            patient.unit_doctor = patient.unit_obj.unit_name

        if patient.visit_through == 'IP' and not patient.ipno:
            patient.ipno = Patient.generate_next_ipno(is_emergency=is_emer)
        elif patient.visit_through == 'IP' and is_emer and not str(patient.ipno).upper().startswith('E'):
            patient.ipno = f"E{patient.ipno}"

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
        
        messages.success(
            self.request,
            f'Patient <strong>{patient.name}</strong> (ID: <strong>{patient.patient_id}</strong>) registered successfully!'
        )
        
        # Redirect directly to the print preview page
        return redirect('patients:print', pk=patient.pk)


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

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('Accept') == 'application/json' or self.request.GET.get('format') == 'json':
            departments = self.get_queryset()
            results = [{
                'id': d.id,
                'name': d.name,
                'code': d.code,
                'status': 'Active' if d.is_active else 'Inactive'
            } for d in departments]
            return JsonResponse({'departments': results})
        return super().render_to_response(context, **response_kwargs)


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

        qs = Patient.objects.filter(registration_date=census_date).order_by('-id')

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
        ip_admissions_qs = PatientVisit.objects.filter(Q(visit_date__date=census_date, visit_type='IP') | Q(patient__registration_date=census_date, patient__visit_through='IP')).distinct()
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
            is_emergency = (
                str(patient.patient_id or '').upper().startswith('E') or 
                patient.category in ['EMERGENCY', 'CASUALTY'] or
                (patient.department_obj and any(k in patient.department_obj.name.upper() for k in ['EMERGENCY', 'CASUALTY'])) or
                (patient.department and any(k in str(patient.department).upper() for k in ['EMERGENCY', 'CASUALTY']))
            )
            context['is_emergency_patient'] = is_emergency
            context['active_ip_admission'] = patient.active_ip_admission
            context['is_admitted_inpatient'] = patient.is_admitted_inpatient

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
                    visit_type='IP' if is_emergency else patient.visit_through,
                    category=patient.category,
                    ipno=patient.ipno if (patient.visit_through == 'IP' or is_emergency) else '',
                    clinical_notes=patient.complaint,
                    created_by=patient.created_by
                )

            context['visits'] = patient.visits.all().order_by('-visit_no')
            context['last_visit'] = patient.visits.order_by('-visit_no').first()
            context['branch_transfers'] = BranchTransferRequest.objects.filter(patient=patient).select_related(
                'from_department', 'to_department', 'to_unit', 'requested_by', 'reviewed_by', 'cancelled_by'
            ).order_by('-requested_at')
            next_ip = Patient.generate_next_ipno(is_emergency=is_emergency)
            context['next_ipno'] = next_ip
            
            emer_dept = Department.objects.filter(is_active=True).filter(
                Q(name__icontains='EMERGENCY') | Q(name__icontains='CASUALTY') | Q(code__icontains='EMR')
            ).first() if is_emergency else None

            context['visit_form'] = PatientVisitForm(patient=patient, initial={
                'department_obj': emer_dept or patient.department_obj,
                'unit_obj': (emer_dept.units.first() if (emer_dept and emer_dept.units.exists()) else patient.unit_obj),
                'visit_type': 'IP' if is_emergency else 'OP',
                'category': 'EMERGENCY' if is_emergency else 'RE_CONSULTATION',
                'ipno': next_ip if is_emergency else '',
            })

        return context

    def post(self, request, *args, **kwargs):
        from django.db import transaction
        patient_id = request.POST.get('patient_id_hidden') or request.POST.get('patient_id')
        patient = get_object_or_404(Patient, pk=patient_id)

        is_emergency = (
            str(patient.patient_id or '').upper().startswith('E') or 
            patient.category in ['EMERGENCY', 'CASUALTY'] or
            (patient.department_obj and any(k in patient.department_obj.name.upper() for k in ['EMERGENCY', 'CASUALTY'])) or
            (patient.department and any(k in str(patient.department).upper() for k in ['EMERGENCY', 'CASUALTY']))
        )

        if request.POST.get('action') == 'discharge_patient':
            active_ip = patient.active_ip_admission
            if active_ip:
                active_ip.discharge()
                messages.success(request, f"Patient '{patient.name}' (IP #{active_ip.ipno or active_ip.visit_no}) has been successfully discharged.")
            else:
                messages.info(request, f"Patient '{patient.name}' does not have an active inpatient admission.")
            return redirect(f"{reverse('patients:review')}?patient_id={patient.patient_id}")

        if request.POST.get('action') == 'update_centre':
            new_centre = request.POST.get('centre')
            if new_centre in [c[0] for c in Patient.CentreChoices.choices]:
                patient.centre = new_centre
                patient.save()
                messages.success(request, f"Patient centre updated to '{patient.get_centre_display()}'!")
                return redirect(f"{reverse('patients:review')}?patient_id={patient.patient_id}")

        # Strict active IP check: Prevent any new visit while already admitted as Inpatient
        if patient.is_admitted_inpatient:
            messages.error(request, "The patient is already admitted as an inpatient.")
            return redirect(f"{reverse('patients:review')}?patient_id={patient.patient_id}")

        form = PatientVisitForm(request.POST, patient=patient)
        if form.is_valid():
            with transaction.atomic():
                visit = form.save(commit=False)
                visit.patient = patient

                last_visit = patient.visits.order_by('-visit_no').first()
                visit.visit_no = (last_visit.visit_no + 1) if last_visit else 1

                if is_emergency:
                    visit.visit_type = 'IP'
                    if not visit.category or visit.category not in ['EMERGENCY', 'CASUALTY']:
                        visit.category = 'EMERGENCY'

                if visit.department_obj:
                    visit.department = visit.department_obj.name
                if visit.unit_obj:
                    visit.unit_doctor = visit.unit_obj.unit_name

                # Assign IP Number ONLY when visit_type is IP (Manual entry or Auto-generated on save)
                if visit.visit_type == 'IP' or is_emergency:
                    raw_ip = (visit.ipno or '').strip()
                    if not raw_ip or 'AUTO' in raw_ip.upper():
                        visit.ipno = Patient.generate_next_ipno(is_emergency=is_emergency)
                    else:
                        if is_emergency and not raw_ip.upper().startswith('E'):
                            visit.ipno = f"E{raw_ip}"
                        else:
                            visit.ipno = raw_ip
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
        # Sort history by actual visit date/time ascending: oldest visit -> newest visit
        context['visits'] = self.object.visits.all().order_by('visit_date', 'visit_no')
        context['last_visit'] = context['visits'].last()
        context['branch_transfers'] = BranchTransferRequest.objects.filter(patient=self.object).select_related(
            'from_department', 'to_department', 'to_unit', 'requested_by', 'reviewed_by', 'cancelled_by'
        ).order_by('-requested_at')
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
        # Include all Review / Re-Consultation visits (visit_no > 1, or category RE_CONSULTATION, or visit_type REVIEW)
        queryset = PatientVisit.objects.filter(
            Q(visit_no__gt=1) | Q(visit_type='REVIEW') | Q(category='RE_CONSULTATION')
        ).select_related('patient', 'department_obj', 'unit_obj', 'created_by').order_by('-id')

        q_patient = self.request.GET.get('q_patient', '').strip()
        q_from_date, q_to_date = get_default_date_range(self.request, 'q_from_date', 'q_to_date')
        q_department = self.request.GET.get('q_department', '').strip()
        q_patient_type = self.request.GET.get('q_patient_type', '').strip()
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

        if q_patient_type:
            queryset = queryset.filter(patient__patient_type=q_patient_type)

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
        context['q_from_date'], context['q_to_date'] = get_default_date_range(self.request, 'q_from_date', 'q_to_date')
        context['q_department'] = self.request.GET.get('q_department', '')
        context['q_patient_type'] = self.request.GET.get('q_patient_type', '')
        context['q_centre'] = self.request.GET.get('q_centre', '')
        context['q_user'] = self.request.GET.get('q_user', '')

        # KPI Metrics
        context['total_visits'] = qs.count()
        context['d_type_count'] = qs.filter(patient__patient_type='D').count()
        context['o_type_count'] = qs.filter(patient__patient_type='O').count()
        context['unique_patients_count'] = qs.values('patient').distinct().count()

        Department.seed_defaults()
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        context['users_list'] = User.objects.all().order_by('username')
        context['centre_choices'] = Patient.CentreChoices.choices

        context['has_filters'] = any([
            context['q_patient'], context['q_from_date'], context['q_to_date'],
            context['q_department'], context['q_patient_type'], context['q_centre'], context['q_user']
        ])
        return context


class PatientDischargeView(LoginRequiredMixin, MenuAccessRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    menu_key = 'discharge'
    permission_required = 'patients.discharge.view'
    template_name = 'patients/patient_discharge.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        
        tab = self.request.GET.get('tab', 'active')
        context['current_tab'] = tab
        
        search_query = self.request.GET.get('q', '').strip()
        dept_id = self.request.GET.get('dept', '')
        from_date_raw, to_date_raw = get_default_date_range(self.request, 'from_date', 'to_date')
        
        context['search_query'] = search_query
        context['selected_dept'] = dept_id
        context['from_date'] = from_date_raw
        context['to_date'] = to_date_raw
        context['today'] = today

        # Base active admissions
        active_qs = PatientVisit.objects.filter(
            Q(visit_type=Patient.VisitChoices.IP) | (Q(ipno__isnull=False) & ~Q(ipno='')),
            discharge_date__isnull=True
        ).select_related('patient', 'department_obj', 'unit_obj').order_by('-visit_date')

        # Base discharged admissions
        discharged_qs = PatientVisit.objects.filter(
            discharge_date__isnull=False
        ).select_related('patient', 'department_obj', 'unit_obj').order_by('-discharge_date', '-visit_date')

        # Filter by search
        if search_query:
            active_qs = active_qs.filter(
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__name__icontains=search_query) |
                Q(ipno__icontains=search_query) |
                Q(patient__mobile_no__icontains=search_query)
            )
            discharged_qs = discharged_qs.filter(
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__name__icontains=search_query) |
                Q(ipno__icontains=search_query) |
                Q(patient__mobile_no__icontains=search_query)
            )

        # Filter by department
        if dept_id:
            try:
                active_qs = active_qs.filter(department_obj_id=int(dept_id))
                discharged_qs = discharged_qs.filter(department_obj_id=int(dept_id))
            except (ValueError, TypeError):
                active_qs = active_qs.filter(department__icontains=dept_id)
                discharged_qs = discharged_qs.filter(department__icontains=dept_id)

        # Filter discharged by date range
        if from_date_raw:
            try:
                f_date = datetime.strptime(from_date_raw, '%Y-%m-%d').date()
                discharged_qs = discharged_qs.filter(discharge_date__gte=f_date)
            except ValueError:
                pass
        if to_date_raw:
            try:
                t_date = datetime.strptime(to_date_raw, '%Y-%m-%d').date()
                discharged_qs = discharged_qs.filter(discharge_date__lte=t_date)
            except ValueError:
                pass

        # Metrics
        context['active_count'] = PatientVisit.objects.filter(
            Q(visit_type=Patient.VisitChoices.IP) | (Q(ipno__isnull=False) & ~Q(ipno='')),
            discharge_date__isnull=True
        ).count()
        context['discharged_today_count'] = PatientVisit.objects.filter(discharge_date=today).count()
        context['total_discharged_count'] = PatientVisit.objects.filter(discharge_date__isnull=False).count()

        # Selected patient for instant discharge modal/form
        select_patient_id = self.request.GET.get('patient_id')
        select_ipno = self.request.GET.get('ipno')
        select_visit_id = self.request.GET.get('visit_id')

        selected_visit = None
        if select_visit_id:
            selected_visit = PatientVisit.objects.filter(pk=select_visit_id, discharge_date__isnull=True).first()
        elif select_patient_id:
            p = Patient.objects.filter(patient_id__iexact=select_patient_id.strip()).first()
            if p:
                selected_visit = p.active_ip_admission
        elif select_ipno:
            selected_visit = PatientVisit.objects.filter(ipno__iexact=select_ipno.strip(), discharge_date__isnull=True).first()

        context['selected_visit'] = selected_visit
        context['active_admissions'] = active_qs[:100]
        context['discharged_admissions'] = discharged_qs[:100]
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')

        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'discharge')
        visit_id = request.POST.get('visit_id')
        visit = get_object_or_404(PatientVisit, pk=visit_id)

        if action == 'discharge':
            discharge_date_str = request.POST.get('discharge_date', '').strip()
            discharge_type = request.POST.get('discharge_type', 'Normal / Improved').strip()
            discharge_notes = request.POST.get('discharge_notes', '').strip()

            discharge_date = None
            if discharge_date_str:
                try:
                    discharge_date = datetime.strptime(discharge_date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        discharge_date = datetime.strptime(discharge_date_str, '%d/%m/%Y').date()
                    except ValueError:
                        discharge_date = timezone.localdate()
            else:
                discharge_date = timezone.localdate()

            visit.discharge(
                discharge_date=discharge_date,
                discharge_type=discharge_type,
                discharge_notes=discharge_notes
            )
            messages.success(
                request,
                f"Patient '{visit.patient.name}' (IP #{visit.ipno or visit.visit_no}) has been successfully discharged on {discharge_date.strftime('%d/%m/%Y')}."
            )
            return redirect(f"{reverse('patients:discharge')}?tab=discharged&highlight={visit.id}")

        elif action == 'cancel_discharge':
            visit.discharge_date = None
            visit.discharge_type = None
            visit.discharge_notes = None
            visit.save(update_fields=['discharge_date', 'discharge_type', 'discharge_notes'])
            messages.warning(
                request,
                f"Discharge for patient '{visit.patient.name}' (IP #{visit.ipno or visit.visit_no}) has been reopened/cancelled."
            )
            return redirect(f"{reverse('patients:discharge')}?tab=active")

        return redirect('patients:discharge')


class PatientDischargeSlipView(LoginRequiredMixin, DetailView):
    model = PatientVisit
    template_name = 'patients/discharge_slip.html'
    context_object_name = 'visit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['patient'] = self.object.patient
        context['now'] = timezone.now()
        return context


class BranchTransferListView(LoginRequiredMixin, MenuAccessRequiredMixin, GranularPermissionRequiredMixin, TemplateView):
    menu_key = 'branch_transfer'
    permission_required = 'ward.branch_transfer.view'
    template_name = 'patients/branch_transfer.html'

    def get_user_department_obj(self, user):
        """Finds matching Department object for the logged-in user if available."""
        if not user or not user.department:
            return None
        dept_str = str(user.department).strip()
        return Department.objects.filter(
            Q(name__iexact=dept_str) | Q(code__iexact=dept_str)
        ).first()

    def user_can_approve_transfer(self, user, transfer_req):
        """
        Returns True if the user is authorized to approve/reject the transfer request.
        Only staff belonging to the destination department (or system administrators) can approve/reject.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user, 'role', '') == 'ADMIN':
            return True
        user_dept = self.get_user_department_obj(user)
        if user_dept and user_dept.id == transfer_req.to_department_id:
            return True
        if user.department and str(user.department).strip().lower() in [
            transfer_req.to_department.name.lower(),
            transfer_req.to_department.code.lower()
        ]:
            return True
        return False

    def user_can_cancel_transfer(self, user, transfer_req):
        """
        Returns True if the user is authorized to cancel the transfer request.
        Only the requester, staff from the originating department, or system administrators can cancel.
        """
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user, 'role', '') == 'ADMIN':
            return True
        if transfer_req.requested_by == user:
            return True
        user_dept = self.get_user_department_obj(user)
        if user_dept and user_dept.id == transfer_req.from_department_id:
            return True
        if user.department and str(user.department).strip().lower() in [
            transfer_req.from_department.name.lower(),
            transfer_req.from_department.code.lower()
        ]:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_dept = self.get_user_department_obj(user)

        tab = self.request.GET.get('tab', 'all')
        context['current_tab'] = tab
        
        search_query = self.request.GET.get('q', '').strip()
        from_dept_id = self.request.GET.get('from_dept', '').strip()
        to_dept_id = self.request.GET.get('to_dept', '').strip()
        status_filter = self.request.GET.get('status', '').strip()
        from_date_raw = self.request.GET.get('from_date', '').strip()
        to_date_raw = self.request.GET.get('to_date', '').strip()

        context['search_query'] = search_query
        context['selected_from_dept'] = from_dept_id
        context['selected_to_dept'] = to_dept_id
        context['selected_status'] = status_filter
        context['from_date'] = from_date_raw
        context['to_date'] = to_date_raw
        context['user_dept'] = user_dept

        # Base QuerySet
        qs = BranchTransferRequest.objects.select_related(
            'patient', 'admission', 'from_department', 'to_department', 'to_unit', 'requested_by', 'reviewed_by', 'cancelled_by'
        ).order_by('-created_at')

        # Global search filter
        if search_query:
            qs = qs.filter(
                Q(transfer_request_number__icontains=search_query) |
                Q(patient__patient_id__icontains=search_query) |
                Q(patient__name__icontains=search_query) |
                Q(admission__ipno__icontains=search_query)
            )

        if from_dept_id:
            try:
                qs = qs.filter(from_department_id=int(from_dept_id))
            except ValueError:
                pass

        if to_dept_id:
            try:
                qs = qs.filter(to_department_id=int(to_dept_id))
            except ValueError:
                pass

        if status_filter:
            qs = qs.filter(status=status_filter)

        if from_date_raw:
            try:
                f_date = datetime.strptime(from_date_raw, '%Y-%m-%d').date()
                qs = qs.filter(requested_at__date__gte=f_date)
            except ValueError:
                pass

        if to_date_raw:
            try:
                t_date = datetime.strptime(to_date_raw, '%Y-%m-%d').date()
                qs = qs.filter(requested_at__date__lte=t_date)
            except ValueError:
                pass

        # Tab-specific querysets
        if tab == 'incoming':
            if user_dept:
                tab_qs = qs.filter(to_department=user_dept)
            else:
                tab_qs = qs
        elif tab == 'outgoing':
            if user_dept:
                tab_qs = qs.filter(from_department=user_dept)
            else:
                tab_qs = qs
        elif tab == 'pending':
            tab_qs = qs.filter(status=BranchTransferRequest.StatusChoices.PENDING)
        elif tab == 'history':
            tab_qs = qs.filter(status__in=[
                BranchTransferRequest.StatusChoices.ACCEPTED,
                BranchTransferRequest.StatusChoices.REJECTED,
                BranchTransferRequest.StatusChoices.CANCELLED
            ])
        else: # 'all'
            tab_qs = qs

        context['transfer_requests'] = tab_qs[:150]

        # KPI Metrics
        all_unfiltered = BranchTransferRequest.objects.all()
        context['kpi_total'] = all_unfiltered.count()
        context['kpi_pending'] = all_unfiltered.filter(status=BranchTransferRequest.StatusChoices.PENDING).count()
        context['kpi_accepted'] = all_unfiltered.filter(status=BranchTransferRequest.StatusChoices.ACCEPTED).count()
        context['kpi_rejected'] = all_unfiltered.filter(status=BranchTransferRequest.StatusChoices.REJECTED).count()

        if user_dept:
            context['kpi_incoming_pending'] = all_unfiltered.filter(to_department=user_dept, status=BranchTransferRequest.StatusChoices.PENDING).count()
            context['kpi_outgoing_pending'] = all_unfiltered.filter(from_department=user_dept, status=BranchTransferRequest.StatusChoices.PENDING).count()
        else:
            context['kpi_incoming_pending'] = context['kpi_pending']
            context['kpi_outgoing_pending'] = context['kpi_pending']

        Department.seed_defaults()
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        context['status_choices'] = BranchTransferRequest.StatusChoices.choices
        context['new_request_form'] = BranchTransferRequestForm()

        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'create_request')

        if action == 'create_request':
            form = BranchTransferRequestForm(request.POST, requested_by=request.user)
            if form.is_valid():
                transfer_req = form.save(commit=False)
                transfer_req.patient = form.patient_instance
                transfer_req.admission = form.active_admission
                transfer_req.from_department = form.from_department_instance
                transfer_req.requested_by = request.user
                transfer_req.status = BranchTransferRequest.StatusChoices.PENDING
                transfer_req.save()

                messages.success(
                    request,
                    f"Branch transfer request '{transfer_req.transfer_request_number}' for patient '{transfer_req.patient.name}' submitted successfully. "
                    f"The patient will remain in '{transfer_req.from_department.name}' until the destination department ({transfer_req.to_department.name}) accepts the request."
                )
                return redirect(f"{reverse('patients:branch_transfer')}?tab=outgoing&highlight={transfer_req.id}")
            else:
                for field, errors in form.errors.items():
                    for err in errors:
                        messages.error(request, f"{err}")
                return redirect(f"{reverse('patients:branch_transfer')}?tab=all")

        elif action == 'accept_request':
            req_id = request.POST.get('transfer_request_id')
            transfer_req = get_object_or_404(BranchTransferRequest, pk=req_id)

            if transfer_req.status != BranchTransferRequest.StatusChoices.PENDING:
                messages.error(request, "This transfer request has already been processed and cannot be modified.")
                return redirect('patients:branch_transfer')

            if not self.user_can_approve_transfer(request.user, transfer_req):
                messages.error(
                    request,
                    f"Permission Denied: Only staff from destination department '{transfer_req.to_department.name}' can accept this transfer request."
                )
                return redirect('patients:branch_transfer')

            review_notes = request.POST.get('review_notes', '').strip()
            to_unit_id = request.POST.get('to_unit', '').strip()
            to_unit = DepartmentUnit.objects.filter(pk=to_unit_id).first() if to_unit_id else None

            try:
                transfer_req.accept(reviewed_by=request.user, review_notes=review_notes, to_unit=to_unit)
                messages.success(
                    request,
                    f"Branch transfer request '{transfer_req.transfer_request_number}' accepted successfully. "
                    f"Patient '{transfer_req.patient.name}' has been transferred to {transfer_req.to_department.name}."
                )
            except Exception as e:
                messages.error(request, f"Failed to accept transfer: {str(e)}")

            return redirect(f"{reverse('patients:branch_transfer')}?tab=history&highlight={transfer_req.id}")

        elif action == 'reject_request':
            req_id = request.POST.get('transfer_request_id')
            transfer_req = get_object_or_404(BranchTransferRequest, pk=req_id)

            if transfer_req.status != BranchTransferRequest.StatusChoices.PENDING:
                messages.error(request, "This transfer request has already been processed and cannot be modified.")
                return redirect('patients:branch_transfer')

            if not self.user_can_approve_transfer(request.user, transfer_req):
                messages.error(
                    request,
                    f"Permission Denied: Only staff from destination department '{transfer_req.to_department.name}' can reject this transfer request."
                )
                return redirect('patients:branch_transfer')

            rejection_reason = request.POST.get('rejection_reason', '').strip()
            if not rejection_reason:
                messages.error(request, "Rejection reason is mandatory.")
                return redirect('patients:branch_transfer')

            try:
                transfer_req.reject(reviewed_by=request.user, rejection_reason=rejection_reason)
                messages.warning(
                    request,
                    f"Branch transfer request '{transfer_req.transfer_request_number}' rejected. "
                    f"The patient remains in {transfer_req.from_department.name}."
                )
            except Exception as e:
                messages.error(request, f"Failed to reject transfer: {str(e)}")

            return redirect(f"{reverse('patients:branch_transfer')}?tab=history&highlight={transfer_req.id}")

        elif action == 'cancel_request':
            req_id = request.POST.get('transfer_request_id')
            transfer_req = get_object_or_404(BranchTransferRequest, pk=req_id)

            if transfer_req.status != BranchTransferRequest.StatusChoices.PENDING:
                messages.error(request, "Only pending transfer requests can be cancelled.")
                return redirect('patients:branch_transfer')

            if not self.user_can_cancel_transfer(request.user, transfer_req):
                messages.error(
                    request,
                    f"Permission Denied: Only the requesting user or staff from '{transfer_req.from_department.name}' can cancel this request."
                )
                return redirect('patients:branch_transfer')

            cancellation_reason = request.POST.get('cancellation_reason', '').strip()
            try:
                transfer_req.cancel(cancelled_by=request.user, cancellation_reason=cancellation_reason)
                messages.info(
                    request,
                    f"Branch transfer request '{transfer_req.transfer_request_number}' has been cancelled."
                )
            except Exception as e:
                messages.error(request, f"Failed to cancel transfer: {str(e)}")

            return redirect('patients:branch_transfer')

        return redirect('patients:branch_transfer')


def api_patient_active_admission(request):
    """
    JSON API for Branch Transfer New Request modal.
    Looks up patient by patient_id or active IP Number.
    """
    q = (request.GET.get('q') or request.GET.get('patient_id') or '').strip()
    if not q:
        return JsonResponse({'exists': False, 'message': 'Please enter a Patient ID or IP Number.'})

    patient = Patient.objects.filter(
        Q(patient_id__iexact=q) | Q(visits__ipno__iexact=q)
    ).distinct().first()

    if not patient:
        return JsonResponse({'exists': False, 'message': f"No patient found matching '{q}'."})

    is_admitted = patient.is_admitted_inpatient
    active_admission = patient.active_ip_admission

    has_pending = BranchTransferRequest.objects.filter(
        patient=patient,
        status=BranchTransferRequest.StatusChoices.PENDING
    ).first()

    data = {
        'exists': True,
        'patient_id': patient.patient_id,
        'name': f"{patient.title} {patient.name}".strip(),
        'age_gender': f"{patient.age_years}Y / {patient.get_gender_display()}",
        'gender': patient.gender,
        'is_admitted': is_admitted,
        'has_pending_transfer': bool(has_pending),
        'pending_transfer_number': has_pending.transfer_request_number if has_pending else None,
    }

    if active_admission:
        data.update({
            'admission_id': active_admission.id,
            'ipno': active_admission.ipno or str(active_admission.visit_no),
            'admission_date': active_admission.visit_date.strftime('%d/%b/%Y %H:%M'),
            'current_dept_id': active_admission.department_obj_id or (patient.department_obj_id if patient.department_obj else None),
            'current_dept_name': active_admission.department or (patient.department_obj.name if patient.department_obj else 'GENERAL MEDICINE'),
            'current_doctor': active_admission.unit_doctor or (patient.unit_obj.unit_name if patient.unit_obj else '--'),
            'ward': active_admission.ward or 'General Ward',
            'bed': active_admission.bed or '--',
        })

    return JsonResponse(data)


class BranchTransferReportView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'ward'
    model = BranchTransferRequest
    template_name = 'patients/branch_transfer_report.html'
    context_object_name = 'transfers'
    paginate_by = 50

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit() and int(page_size) in [10, 25, 50, 100, 200]:
            return int(page_size)
        return super().get_paginate_by(queryset)

    def get_queryset(self):
        queryset = BranchTransferRequest.objects.select_related(
            'patient', 'admission', 'from_department', 'to_department', 'to_unit',
            'requested_by', 'reviewed_by', 'cancelled_by'
        ).order_by('-requested_at')

        q_search = self.request.GET.get('q_search', '').strip()
        q_from_date, q_to_date = get_default_date_range(self.request, 'q_from_date', 'q_to_date')
        q_from_dept = self.request.GET.get('q_from_dept', '').strip()
        q_to_dept = self.request.GET.get('q_to_dept', '').strip()
        q_status = self.request.GET.get('q_status', '').strip()
        q_user = self.request.GET.get('q_user', '').strip()

        if q_search:
            queryset = queryset.filter(
                Q(transfer_request_number__icontains=q_search) |
                Q(patient__patient_id__icontains=q_search) |
                Q(patient__name__icontains=q_search) |
                Q(admission__ipno__icontains=q_search)
            )

        if q_from_date:
            try:
                from_dt = datetime.strptime(q_from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(requested_at__date__gte=from_dt)
            except ValueError:
                pass

        if q_to_date:
            try:
                to_dt = datetime.strptime(q_to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(requested_at__date__lte=to_dt)
            except ValueError:
                pass

        if q_from_dept:
            try:
                queryset = queryset.filter(from_department_id=int(q_from_dept))
            except ValueError:
                pass

        if q_to_dept:
            try:
                queryset = queryset.filter(to_department_id=int(q_to_dept))
            except ValueError:
                pass

        if q_status:
            queryset = queryset.filter(status=q_status)

        if q_user:
            try:
                user_id = int(q_user)
                queryset = queryset.filter(Q(requested_by_id=user_id) | Q(reviewed_by_id=user_id))
            except ValueError:
                pass

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        Department.seed_defaults()

        q_from_date, q_to_date = get_default_date_range(self.request, 'q_from_date', 'q_to_date')

        # Filtered queryset for aggregates (without pagination limit)
        filtered_qs = self.get_queryset()

        context['total_transfers'] = filtered_qs.count()
        context['pending_count'] = filtered_qs.filter(status=BranchTransferRequest.StatusChoices.PENDING).count()
        context['accepted_count'] = filtered_qs.filter(status=BranchTransferRequest.StatusChoices.ACCEPTED).count()
        context['rejected_count'] = filtered_qs.filter(status=BranchTransferRequest.StatusChoices.REJECTED).count()
        context['cancelled_count'] = filtered_qs.filter(status=BranchTransferRequest.StatusChoices.CANCELLED).count()
        context['unique_patients_count'] = filtered_qs.values('patient').distinct().count()

        # Top transfer pathways / routes
        top_routes = (
            filtered_qs.values('from_department__name', 'to_department__name')
            .annotate(route_count=Count('id'))
            .order_by('-route_count')[:5]
        )
        context['top_routes'] = top_routes

        # Filter dropdown data
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        context['status_choices'] = BranchTransferRequest.StatusChoices.choices
        context['users_list'] = User.objects.filter(is_active=True).order_by('username')

        # Pass active filter values to context
        context['q_search'] = self.request.GET.get('q_search', '')
        context['q_from_date'] = q_from_date
        context['q_to_date'] = q_to_date
        context['q_from_dept'] = self.request.GET.get('q_from_dept', '')
        context['q_to_dept'] = self.request.GET.get('q_to_dept', '')
        context['q_status'] = self.request.GET.get('q_status', '')
        context['q_user'] = self.request.GET.get('q_user', '')
        context['page_size'] = self.get_paginate_by(filtered_qs)

        # Check if custom filter is active
        context['has_filters'] = bool(
            self.request.GET.get('q_search') or
            self.request.GET.get('q_from_dept') or
            self.request.GET.get('q_to_dept') or
            self.request.GET.get('q_status') or
            self.request.GET.get('q_user') or
            self.request.GET.get('q_from_date') or
            self.request.GET.get('q_to_date')
        )
        context['now'] = timezone.now()
        return context


@login_required
def export_branch_transfers_csv(request):
    """
    Exports filtered branch transfer records to CSV.
    """
    queryset = BranchTransferRequest.objects.select_related(
        'patient', 'admission', 'from_department', 'to_department', 'to_unit',
        'requested_by', 'reviewed_by', 'cancelled_by'
    ).order_by('-requested_at')

    q_search = request.GET.get('q_search', '').strip()
    q_from_date, q_to_date = get_default_date_range(request, 'q_from_date', 'q_to_date')
    q_from_dept = request.GET.get('q_from_dept', '').strip()
    q_to_dept = request.GET.get('q_to_dept', '').strip()
    q_status = request.GET.get('q_status', '').strip()
    q_user = request.GET.get('q_user', '').strip()

    if q_search:
        queryset = queryset.filter(
            Q(transfer_request_number__icontains=q_search) |
            Q(patient__patient_id__icontains=q_search) |
            Q(patient__name__icontains=q_search) |
            Q(admission__ipno__icontains=q_search)
        )

    if q_from_date:
        try:
            from_dt = datetime.strptime(q_from_date, '%Y-%m-%d').date()
            queryset = queryset.filter(requested_at__date__gte=from_dt)
        except ValueError:
            pass

    if q_to_date:
        try:
            to_dt = datetime.strptime(q_to_date, '%Y-%m-%d').date()
            queryset = queryset.filter(requested_at__date__lte=to_dt)
        except ValueError:
            pass

    if q_from_dept:
        try:
            queryset = queryset.filter(from_department_id=int(q_from_dept))
        except ValueError:
            pass

    if q_to_dept:
        try:
            queryset = queryset.filter(to_department_id=int(q_to_dept))
        except ValueError:
            pass

    if q_status:
        queryset = queryset.filter(status=q_status)

    if q_user:
        try:
            user_id = int(q_user)
            queryset = queryset.filter(Q(requested_by_id=user_id) | Q(reviewed_by_id=user_id))
        except ValueError:
            pass

    response = HttpResponse(content_type='text/csv')
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="branch_transfer_report_{timestamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Transfer Request #',
        'Request Date & Time',
        'Patient ID / UHID',
        'Patient Name',
        'Age',
        'Gender',
        'IP Number',
        'Originating Department',
        'Destination Department',
        'Destination Unit / Doctor',
        'Status',
        'Requested By',
        'Reviewed / Approved By',
        'Reviewed Date & Time',
        'Transfer Reason',
        'Review / Rejection / Approval Notes',
        'Cancellation Reason'
    ])

    for r in queryset:
        writer.writerow([
            r.transfer_request_number,
            r.requested_at.strftime('%Y-%m-%d %H:%M:%S') if r.requested_at else '',
            r.patient.patient_id if r.patient else '',
            f"{r.patient.title} {r.patient.name}" if r.patient else '',
            r.patient.age_years if r.patient else '',
            r.patient.gender if r.patient else '',
            r.admission.ipno if r.admission and r.admission.ipno else (r.patient.ipno if r.patient else ''),
            r.from_department.name if r.from_department else '',
            r.to_department.name if r.to_department else '',
            r.to_unit.unit_name if r.to_unit else '',
            r.get_status_display(),
            r.requested_by.username if r.requested_by else '',
            r.reviewed_by.username if r.reviewed_by else '',
            r.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if r.reviewed_at else '',
            r.transfer_reason or '',
            r.review_notes or '',
            r.cancellation_reason or ''
        ])

    return response



