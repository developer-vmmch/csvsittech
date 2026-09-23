from django.contrib import admin
from .models import (
    OTRoom, OTProcedure, OTCase, OTStatusHistory,
    OTPreOp, OTSchedule, OTChecklist, OTAnesthesia,
    OTOperation, OTSpecimen, OTDisposition, OTTransfer,
    OTPostOp, OTClosure
)

@admin.register(OTRoom)
class OTRoomAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'location', 'status']
    list_filter = ['status']

@admin.register(OTProcedure)
class OTProcedureAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'avg_duration_min', 'is_active']
    list_filter = ['is_active', 'department']

@admin.register(OTCase)
class OTCaseAdmin(admin.ModelAdmin):
    list_display = ['ot_number', 'patient', 'procedure', 'case_type', 'status', 'created_at']
    list_filter = ['case_type', 'status', 'priority', 'is_mlc', 'is_demo']
    search_fields = ['ot_number', 'patient__name', 'patient__patient_id']
    readonly_fields = ['ot_number', 'created_at', 'updated_at']

@admin.register(OTStatusHistory)
class OTStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['ot_case', 'from_status', 'to_status', 'changed_by', 'changed_at']
    readonly_fields = ['ot_case', 'from_status', 'to_status', 'changed_by', 'changed_at']

admin.site.register(OTPreOp)
admin.site.register(OTSchedule)
admin.site.register(OTChecklist)
admin.site.register(OTAnesthesia)
admin.site.register(OTOperation)
admin.site.register(OTSpecimen)
admin.site.register(OTDisposition)
admin.site.register(OTTransfer)
admin.site.register(OTPostOp)
admin.site.register(OTClosure)
