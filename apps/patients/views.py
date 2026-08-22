from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.core.mixins import MenuAccessRequiredMixin
from django.contrib import messages
from django.db.models import Q
from datetime import datetime
from .models import Patient, PatientCompany, Department, DepartmentUnit
from .forms import PatientRegistrationForm, PatientCompanyForm, DepartmentForm, DepartmentUnitForm

class PatientListView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'patient_list'
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20


class PatientSearchView(LoginRequiredMixin, MenuAccessRequiredMixin, ListView):
    menu_key = 'search_patient'
    model = Patient
    template_name = 'patients/patient_search.html'
    context_object_name = 'patients'
    paginate_by = 30

    def get_queryset(self):
        q_name = self.request.GET.get('q_name', '').strip()
        q_from_date = self.request.GET.get('q_from_date', '').strip()
        q_to_date = self.request.GET.get('q_to_date', '').strip()
        q_mobile = self.request.GET.get('q_mobile', '').strip()
        q_aadhar = self.request.GET.get('q_aadhar', '').strip()
        q_abha = self.request.GET.get('q_abha', '').strip()

        has_search_params = any([q_name, q_from_date, q_to_date, q_mobile, q_aadhar, q_abha])

        if not has_search_params:
            return Patient.objects.none()

        queryset = Patient.objects.all().order_by('-id')

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
            queryset = queryset.filter(Q(abha_id__icontains=q_abha) | Q(patient_id__icontains=q_abha))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q_name'] = self.request.GET.get('q_name', '')
        context['q_from_date'] = self.request.GET.get('q_from_date', '')
        context['q_to_date'] = self.request.GET.get('q_to_date', '')
        context['q_mobile'] = self.request.GET.get('q_mobile', '')
        context['q_aadhar'] = self.request.GET.get('q_aadhar', '')
        context['q_abha'] = self.request.GET.get('q_abha', '')
        context['has_searched'] = any([
            context['q_name'], context['q_from_date'], context['q_to_date'],
            context['q_mobile'], context['q_aadhar'], context['q_abha']
        ])
        return context


class PatientCreateView(LoginRequiredMixin, MenuAccessRequiredMixin, CreateView):
    menu_key = 'add_patient'
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

        # Set default department & unit
        default_dept = Department.objects.filter(code='GENMED').first() or Department.objects.first()
        if default_dept:
            initial['department_obj'] = default_dept.id
            default_unit = default_dept.units.filter(is_active=True).first()
            if default_unit:
                initial['unit_obj'] = default_unit.id
            
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        last_patient = Patient.objects.order_by('-id').first()
        context['last_patient_id'] = last_patient.patient_id if last_patient else '26148626'
        context['reg_date'] = '21/Aug/2026'
        context['reg_time'] = '09:36:17'
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        patient = form.save(commit=False)
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

        if self.request.user.is_authenticated:
            patient.created_by = self.request.user

        patient.save()
        
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


class PatientUpdateView(LoginRequiredMixin, MenuAccessRequiredMixin, UpdateView):
    menu_key = 'patient_list'
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


class PatientDeleteView(LoginRequiredMixin, MenuAccessRequiredMixin, DeleteView):
    menu_key = 'patient_list'
    model = Patient
    success_url = reverse_lazy('patients:list')

    def post(self, request, *args, **kwargs):
        patient = self.get_object()
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
    paginate_by = 20


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
    paginate_by = 20


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
