from django.contrib import admin
from .models import Patient, PatientCompany, Department, DepartmentUnit

class DepartmentUnitInline(admin.TabularInline):
    model = DepartmentUnit
    extra = 1

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'created_at')
    search_fields = ('code', 'name')
    list_filter = ('is_active',)
    inlines = [DepartmentUnitInline]


@admin.register(DepartmentUnit)
class DepartmentUnitAdmin(admin.ModelAdmin):
    list_display = ('unit_name', 'department', 'head_doctor', 'is_active')
    search_fields = ('unit_name', 'head_doctor', 'department__name')
    list_filter = ('department', 'is_active')


@admin.register(PatientCompany)
class PatientCompanyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'contact_person', 'phone_number', 'discount_percentage', 'is_active')
    search_fields = ('code', 'name', 'contact_person', 'phone_number')
    list_filter = ('category', 'is_active')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'title', 'name', 'gender', 'age_years', 'mobile_no', 'department', 'unit_doctor', 'patient_company', 'created_at')
    search_fields = ('patient_id', 'name', 'mobile_no', 'aadhar_card', 'abha_id')
    list_filter = ('gender', 'visit_through', 'category', 'department', 'blood_group', 'created_at')
