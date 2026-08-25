from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'ERP Executive Dashboard'
        context['modules'] = [
            {'name': 'User Management', 'status': 'Active', 'icon': 'bi-people', 'badge': 'Core'},
            {'name': 'Inventory & Stocks', 'status': 'Ready', 'icon': 'bi-box-seam', 'badge': 'ERP'},
            {'name': 'Finance & Billing', 'status': 'Configured', 'icon': 'bi-cash-coin', 'badge': 'Finance'},
            {'name': 'Reports & Analytics', 'status': 'Active', 'icon': 'bi-graph-up-arrow', 'badge': 'BI'},
        ]
        
        # Adding counts for the Master Summary Section
        from apps.lab.models import Diagnosis, Investigation, InvestigationParameter
        context['diagnosis_count'] = Diagnosis.objects.count()
        context['investigation_count'] = Investigation.objects.count()
        context['parameter_count'] = InvestigationParameter.objects.count()
        
        return context
