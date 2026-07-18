from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from modules.models import Module


@login_required(login_url='auth')
def home(request):
    modules_by_year = {year: [] for year in range(1, 6)}
    modules = Module.objects.filter(is_active=True).annotate(
        total_exams=Count('exams', filter=Q(exams__is_active=True), distinct=True),
        completed_exams=Count(
            'exams',
            filter=Q(
                exams__is_active=True,
                exams__attempts__student=request.user,
                exams__attempts__total_questions__gt=0,
            ),
            distinct=True,
        ),
        last_access=Max(
            'exams__attempts__submitted_at',
            filter=Q(exams__attempts__student=request.user),
        ),
    ).order_by('year', 'order', 'name')
    for module in modules:
        section_count = sum((
            module.has_lessons,
            module.has_videos,
            module.has_files,
            module.has_text,
            module.has_exams,
            module.has_osce,
        ))
        progress = round((module.completed_exams / module.total_exams) * 100) if module.total_exams else 0
        if module.total_exams and module.completed_exams == module.total_exams:
            status, status_class = 'Completed', 'status-completed'
        elif module.last_access:
            status, status_class = 'In Progress', 'status-progress'
        else:
            status, status_class = 'Not Started', 'status-not-started'

        if not module.last_access:
            last_access = '-'
        else:
            days_since_access = (timezone.localdate() - timezone.localdate(module.last_access)).days
            if days_since_access == 0:
                last_access = 'Today'
            elif days_since_access == 1:
                last_access = 'Yesterday'
            else:
                last_access = f'{days_since_access} days ago'
        modules_by_year[module.year].append({
            'id': module.pk,
            'name': module.name,
            'url': reverse('module-detail', args=[module.pk]),
            'icon': module.icon_class or 'bx-book',
            'bg': module.bg_color,
            'color': module.color,
            'btnColor': module.btn_color,
            'sections': section_count,
            'description': module.description,
            'progress': progress,
            'status': status,
            'statusClass': status_class,
            'lastAccess': last_access,
        })

    years = [
        {
            'number': year,
            'module_count': len(modules_by_year[year]),
            'courses': modules_by_year[year],
        }
        for year in range(1, 6)
    ]
    return render(request, 'dashboard/home.html', {
        'active_page': 'dashboard',
        'years': years,
        'modules_by_year': modules_by_year,
    })
