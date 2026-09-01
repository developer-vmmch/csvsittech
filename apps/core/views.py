from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import json
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'VMMC ERP Dashboard'
        
        from apps.lab.models import Investigation, InvestigationParameter, AutomationDummyResult, AutoTriggerHistory
        
        # Basic Stats
        context['total_investigations'] = Investigation.objects.count()
        context['total_parameters'] = InvestigationParameter.objects.count()
        context['total_dummy_results'] = AutomationDummyResult.objects.count()
        
        today = timezone.localtime().date()
        context['results_today'] = AutomationDummyResult.objects.filter(created_at__date=today).count()
        
        start_of_month = today.replace(day=1)
        context['monthly_tests'] = AutomationDummyResult.objects.filter(created_at__date__gte=start_of_month).count()

        # Results by investigation (Donut chart data)
        inv_counts = AutomationDummyResult.objects.values(
            'investigation__name', 'investigation__short_name'
        ).annotate(count=Count('id')).order_by('-count')
        
        donut_labels = []
        donut_data = []
        donut_details = []
        
        for item in inv_counts:
            short = item['investigation__short_name']
            name = item['investigation__name']
            label = f"{short} - {name}" if short and short != name else name
            donut_labels.append(label)
            donut_data.append(item['count'])
            donut_details.append({'label': label, 'count': item['count']})
            
        context['donut_labels_json'] = json.dumps(donut_labels)
        context['donut_data_json'] = json.dumps(donut_data)
        context['donut_details'] = donut_details

        # Results Trend (Last 7 Days)
        trend_labels = []
        trend_data = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            trend_labels.append(d.strftime('%d %b'))
            c = AutomationDummyResult.objects.filter(created_at__date=d).count()
            trend_data.append(c)
            
        context['trend_labels_json'] = json.dumps(trend_labels)
        context['trend_data_json'] = json.dumps(trend_data)
        
        context['trend_total'] = sum(trend_data)
        context['trend_avg'] = round(context['trend_total'] / 7, 2)
        if trend_data:
            max_idx = trend_data.index(max(trend_data))
            min_idx = trend_data.index(min(trend_data))
            context['trend_highest'] = trend_data[max_idx]
            context['trend_highest_date'] = (today - timedelta(days=6 - max_idx)).strftime('%d %b %Y')
            context['trend_lowest'] = trend_data[min_idx]
            context['trend_lowest_date'] = (today - timedelta(days=6 - min_idx)).strftime('%d %b %Y')
        else:
            context['trend_highest'] = 0
            context['trend_highest_date'] = '-'
            context['trend_lowest'] = 0
            context['trend_lowest_date'] = '-'

        # Recent Dummy Results (last 5)
        recent = AutomationDummyResult.objects.select_related('investigation').prefetch_related('parameters').order_by('-created_at')[:5]
        recent_list = []
        for r in recent:
            recent_list.append({
                'inv_short': r.investigation.short_name or r.investigation.name[:3],
                'name': r.dummy_name,
                'result_id': r.result_id,
                'created_on': timezone.localtime(r.created_at).strftime('%d-%b-%Y %I:%M %p'),
                'param_count': r.parameters.count(),
                'id': r.id
            })
        context['recent_results'] = recent_list

        # Automation Summary
        context['successful_triggers'] = AutoTriggerHistory.objects.filter(status='Completed').count()
        context['pending_triggers'] = AutoTriggerHistory.objects.filter(status__in=['Pending', 'Running']).count()
        context['failed_triggers'] = AutoTriggerHistory.objects.filter(status='Failed').count()
        last_execution = AutoTriggerHistory.objects.order_by('-last_processed_at').first()
        if last_execution and last_execution.last_processed_at:
            context['last_trigger_run'] = timezone.localtime(last_execution.last_processed_at).strftime('%d-%b-%Y %I:%M %p')
        else:
            context['last_trigger_run'] = '-'

        return context
