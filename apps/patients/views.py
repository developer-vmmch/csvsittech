from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from datetime import datetime
from .models import Patient, PatientCompany, Department, DepartmentUnit
from .forms import PatientRegistrationForm, PatientCompanyForm, DepartmentForm, DepartmentUnitForm

class PatientListView(LoginRequiredMixin, ListView):
    model = Patient
    template_name = 'patients/patient_list.html'
    context_object_name = 'patients'
    paginate_by = 20


class PatientSearchView(LoginRequiredMixin, ListView):
    model = Patient
    template_name = 'patients/patient_search.html'
    context_object_name = 'patients'
    paginate_by = 30

    def get_queryset(self):
        queryset = Patient.objects.all().order_by('-id')
        
        q_name = self.request.GET.get('q_name', '').strip()
        q_from_date = self.request.GET.get('q_from_date', '').strip()
        q_to_date = self.request.GET.get('q_to_date', '').strip()
        q_mobile = self.request.GET.get('q_mobile', '').strip()
        q_aadhar = self.request.GET.get('q_aadhar', '').strip()
        q_abha = self.request.GET.get('q_abha', '').strip()

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
        context['has_filters'] = any([
            context['q_name'], context['q_from_date'], context['q_to_date'],
            context['q_mobile'], context['q_aadhar'], context['q_abha']
        ])
        return context


class PatientCreateView(LoginRequiredMixin, CreateView):
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

        patient.save()
        messages.success(self.request, f"Patient {patient.name} (ID: {patient.patient_id}) registered successfully!")
        
        # Automatically redirect directly to the Print OP Slip page for this patient!
        return redirect('patients:print', pk=patient.pk)


class PatientUpdateView(LoginRequiredMixin, UpdateView):
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


class PatientPrintView(LoginRequiredMixin, DetailView):
    model = Patient
    template_name = 'patients/patient_print.html'
    context_object_name = 'patient'


class PatientDeleteView(LoginRequiredMixin, DeleteView):
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


class DepartmentListView(LoginRequiredMixin, ListView):
    model = Department
    template_name = 'patients/department_list.html'
    context_object_name = 'departments'
    paginate_by = 20


class DepartmentCreateView(LoginRequiredMixin, CreateView):
    model = Department
    form_class = DepartmentForm
    template_name = 'patients/department_form.html'
    success_url = reverse_lazy('patients:department_list')

    def form_valid(self, form):
        dept = form.save()
        messages.success(self.request, f"Department '{dept.name}' ({dept.code}) created successfully!")
        return super().form_valid(form)


class DepartmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Department
    success_url = reverse_lazy('patients:department_list')

    def post(self, request, *args, **kwargs):
        dept = self.get_object()
        messages.success(request, f"Department '{dept.name}' ({dept.code}) deleted successfully.")
        return super().post(request, *args, **kwargs)


class DepartmentUnitCreateView(LoginRequiredMixin, CreateView):
    model = DepartmentUnit
    form_class = DepartmentUnitForm
    template_name = 'patients/unit_form.html'
    success_url = reverse_lazy('patients:department_list')

    def form_valid(self, form):
        unit = form.save()
        messages.success(self.request, f"Unit/Doctor '{unit.unit_name}' mapped to '{unit.department.name}' successfully!")
        return super().form_valid(form)


class DepartmentUnitDeleteView(LoginRequiredMixin, DeleteView):
    model = DepartmentUnit
    success_url = reverse_lazy('patients:department_list')

    def post(self, request, *args, **kwargs):
        unit = self.get_object()
        messages.success(request, f"Unit '{unit.unit_name}' deleted successfully.")
        return super().post(request, *args, **kwargs)


class PatientCompanyListView(LoginRequiredMixin, ListView):
    model = PatientCompany
    template_name = 'patients/company_list.html'
    context_object_name = 'companies'
    paginate_by = 20


class PatientCompanyCreateView(LoginRequiredMixin, CreateView):
    model = PatientCompany
    form_class = PatientCompanyForm
    template_name = 'patients/company_form.html'
    success_url = reverse_lazy('patients:company_list')

    def form_valid(self, form):
        company = form.save()
        messages.success(self.request, f"Patient Company '{company.name}' ({company.code}) created successfully!")
        return super().form_valid(form)


class PatientCompanyDeleteView(LoginRequiredMixin, DeleteView):
    model = PatientCompany
    success_url = reverse_lazy('patients:company_list')

    def post(self, request, *args, **kwargs):
        company = self.get_object()
        messages.success(request, f"Patient Company '{company.name}' ({company.code}) deleted successfully.")
        return super().post(request, *args, **kwargs)
