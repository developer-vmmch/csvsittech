from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('ERP Profile Info', {'fields': ('role', 'department', 'phone_number', 'employee_id')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('ERP Profile Info', {'fields': ('role', 'department', 'phone_number', 'employee_id')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_staff')
    list_filter = ('role', 'department', 'is_staff', 'is_superuser', 'is_active')
