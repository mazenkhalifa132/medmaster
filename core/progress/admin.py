from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import ExpressionWrapper, F, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponseRedirect
from django.utils.html import format_html, format_html_join
from uuid import uuid4
from django.template.response import TemplateResponse
from django.urls import path, reverse

from exams.models import Exam, ExamAttempt
from modules.models import Module
from osce.models import OSCEAttempt

from .models import Badge, Rank, StudentBadge, StudentProgress, WeeklyGoal, rank_for_points
from .services import _award_badge


class ModuleByYearSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-year'] = value.instance.year
        return option


class ExamByModuleSelect(forms.SelectMultiple):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-module'] = value.instance.module_id
        return option


class RankAdminForm(forms.ModelForm):
    class Meta:
        model = Rank
        fields = '__all__'
        widgets = {
            # A native color input provides a palette while preserving the
            # hexadecimal value required by the model.
            'color': forms.TextInput(attrs={'type': 'color', 'aria-label': 'Rank color'}),
        }


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    form = RankAdminForm
    list_display = ('name', 'min_points', 'max_points', 'color', 'image_url')
    list_editable = ('min_points', 'max_points', 'color', 'image_url')
    ordering = ('min_points',)

    def get_changelist_form(self, request, **kwargs):
        """Use the color-picker widget for inline edits on the rank list."""
        kwargs['form'] = RankAdminForm
        return super().get_changelist_form(request, **kwargs)


@admin.register(StudentProgress)
class StudentProgressAdmin(admin.ModelAdmin):
    """Admin-only student leaderboard and progress records."""

    list_display = ('student', 'total_points', 'correct_answers', 'incorrect_answers', 'updated_at')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'student__email')
    readonly_fields = (
        'student', 'student_first_name', 'student_last_name', 'student_email',
        'student_phone', 'student_academic_year', 'total_points', 'correct_answers',
        'incorrect_answers', 'total_percentage', 'student_rank', 'given_badges',
        'exam_first_scores', 'updated_at',
    )
    fieldsets = (
        ('Personal information', {
            'fields': ('student', 'student_first_name', 'student_last_name', 'student_email', 'student_phone', 'student_academic_year'),
        }),
        ('Academic information', {
            'fields': ('total_points', 'correct_answers', 'incorrect_answers', 'total_percentage', 'student_rank', 'given_badges', 'updated_at'),
        }),
        ('Exam information', {
            'fields': ('exam_first_scores',),
            'description': 'The first completed attempt is shown for every exam. Exams without a completed attempt are marked as not entered.',
        }),
    )
    change_list_template = 'admin/progress/studentprogress/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # Django checks deletion permissions on every related model before it
        # allows an administrator to delete a user.  Student progress cascades
        # when its student is deleted, so denying this permission made the
        # admin reject student deletion even though the database relationship
        # is configured with CASCADE.
        return self.has_module_permission(request)

    def has_module_permission(self, request):
        return request.user.is_superuser or getattr(request.user, 'role', None) == 'admin'

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    @admin.display(description='First name')
    def student_first_name(self, obj):
        return obj.student.first_name or '—'

    @admin.display(description='Second name')
    def student_last_name(self, obj):
        return obj.student.last_name or '—'

    @admin.display(description='Email')
    def student_email(self, obj):
        return obj.student.email or '—'

    @admin.display(description='Phone number')
    def student_phone(self, obj):
        return obj.student.phone or '—'

    @admin.display(description='Academic year')
    def student_academic_year(self, obj):
        return f'Year {obj.student.academic_year}' if obj.student.academic_year else 'Not assigned'

    @admin.display(description='Total percentage')
    def total_percentage(self, obj):
        answered = obj.correct_answers + obj.incorrect_answers
        return f'{(obj.correct_answers / answered) * 100:.1f}%' if answered else '0.0%'

    @admin.display(description='Rank')
    def student_rank(self, obj):
        rank = obj.rank
        return rank.name if rank else 'Unranked'

    @admin.display(description='Given badges')
    def given_badges(self, obj):
        awards = StudentBadge.objects.filter(student=obj.student).select_related('badge').order_by('-awarded_at', '-pk')
        if not awards:
            return 'No badges awarded'
        return format_html(
            '<ul style="margin: 0; padding-left: 18px;">{}</ul>',
            format_html_join('', '<li><strong>{}</strong> <span style="color: #666;">— {:%b %d, %Y}</span></li>', ((award.badge.name, award.awarded_at) for award in awards)),
        )

    @admin.display(description='First score for each exam')
    def exam_first_scores(self, obj):
        first_attempts = {}
        attempts = ExamAttempt.objects.filter(
            student=obj.student,
            total_questions__gt=0,
        ).select_related('exam').order_by('exam_id', 'submitted_at', 'pk')
        for attempt in attempts:
            first_attempts.setdefault(attempt.exam_id, attempt)

        rows = []
        for exam in Exam.objects.select_related('module').order_by('year', 'module__order', 'order', 'name'):
            attempt = first_attempts.get(exam.pk)
            exam_name = f'Year {exam.year} · {exam.module.name} · {exam.name}'
            if attempt:
                percentage = (attempt.score / attempt.total_questions) * 100 if attempt.total_questions else 0
                result = f'{attempt.score}/{attempt.total_questions} ({percentage:.1f}%)'
                status = format_html(
                    '<span style="color: #15803d; font-weight: 600;">{}</span>', 'Entered'
                )
                date = attempt.submitted_at
            else:
                result = '—'
                status = format_html(
                    '<span style="color: #b91c1c; font-weight: 600;">{}</span>', 'Not entered'
                )
                date = '—'
            rows.append((exam_name, result, status, date))

        if not rows:
            return 'No exams have been created yet.'
        return format_html(
            '<table style="width: 100%; border-collapse: collapse;"><thead><tr><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Exam</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">First score</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">Status</th><th style="text-align:left; padding:8px; border-bottom:1px solid #ddd;">First attempt</th></tr></thead><tbody>{}</tbody></table>',
            format_html_join('', '<tr><td style="padding:8px; border-bottom:1px solid #eee;">{}</td><td style="padding:8px; border-bottom:1px solid #eee;">{}</td><td style="padding:8px; border-bottom:1px solid #eee;">{}</td><td style="padding:8px; border-bottom:1px solid #eee;">{}</td></tr>', rows),
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'student/<int:student_id>/',
                self.admin_site.admin_view(self.student_detail_view),
                name='progress_studentprogress_student_detail',
            ),
            path(
                'leaderboard/',
                self.admin_site.admin_view(self.leaderboard_view),
                name='progress_studentprogress_leaderboard',
            ),
        ]
        return custom_urls + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Use the filterable student-detail screen for progress-list links too."""
        progress = self.get_object(request, object_id)
        if progress is None:
            return super().change_view(request, object_id, form_url, extra_context)
        return HttpResponseRedirect(
            reverse(
                'admin:progress_studentprogress_student_detail', args=(progress.student_id,)
            )
        )

    @staticmethod
    def _first_attempts_for(student):
        first_attempts = {}
        attempts = ExamAttempt.objects.filter(
            student=student,
            total_questions__gt=0,
        ).select_related('exam').order_by('exam_id', 'submitted_at', 'pk')
        for attempt in attempts:
            first_attempts.setdefault(attempt.exam_id, attempt)
        return first_attempts

    def _filtered_exam_rows(self, student, filters):
        first_attempts = self._first_attempts_for(student)
        exams = Exam.objects.select_related('module', 'subject', 'week').order_by(
            'year', 'module__order', 'order', 'name'
        )
        if filters['year'].isdigit():
            exams = exams.filter(year=filters['year'])
        if filters['module'].isdigit():
            exams = exams.filter(module_id=filters['module'])
        if filters['subject'].isdigit():
            exams = exams.filter(subject_id=filters['subject'])
        if filters['week'].isdigit():
            exams = exams.filter(week_id=filters['week'])
        if filters['search']:
            exams = exams.filter(name__icontains=filters['search'])

        rows = []
        for exam in exams:
            attempt = first_attempts.get(exam.pk)
            entered = attempt is not None
            if filters['entered'] == 'yes' and not entered:
                continue
            if filters['entered'] == 'no' and entered:
                continue
            percentage = round((attempt.score / attempt.total_questions) * 100, 1) if entered else None
            if filters['percentage'].isdigit() and (
                percentage is None or percentage < int(filters['percentage'])
            ):
                continue
            rows.append({
                'exam': exam,
                'attempt': attempt,
                'entered': entered,
                'percentage': percentage,
            })
        return rows

    def student_detail_view(self, request, student_id):
        """Open a student's read-only progress record from the leaderboard."""
        if not self.has_view_permission(request):
            raise PermissionDenied

        User = get_user_model()
        try:
            student = User.objects.get(
                pk=student_id, role='student', is_staff=False, is_superuser=False,
            )
        except User.DoesNotExist as exc:
            raise Http404('Student not found.') from exc

        progress, _ = StudentProgress.objects.get_or_create(student=student)
        filters = {
            key: request.GET.get(key, '').strip()
            for key in ('year', 'module', 'subject', 'week', 'entered', 'percentage', 'search')
        }
        modules = list(Module.objects.order_by('year', 'order', 'name'))
        subjects = [
            subject for module in modules
            for subject in module.exam_subjects.all()
        ]
        weeks = [
            week for module in modules
            for week in module.exam_weeks.all()
        ]
        context = {
            **self.admin_site.each_context(request),
            'title': f'Student progress: {student.get_full_name() or student.username}',
            'opts': self.model._meta,
            'student': student,
            'progress': progress,
            'rank': progress.rank,
            'badges': StudentBadge.objects.filter(student=student).select_related('badge').order_by('-awarded_at', '-pk'),
            'exam_rows': self._filtered_exam_rows(student, filters),
            'filters': filters,
            'year_choices': Exam.YEAR_CHOICES,
            'modules': modules,
            'subjects': subjects,
            'weeks': weeks,
            'percentage_choices': (25, 50, 75, 100),
        }
        return TemplateResponse(request, 'admin/progress/studentprogress/student_detail.html', context)

    def leaderboard_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        exam_totals = ExamAttempt.objects.filter(student_id=OuterRef('pk')).values('student').annotate(
            score=Sum('score'), total=Sum('total_questions'),
        )
        osce_totals = OSCEAttempt.objects.filter(student_id=OuterRef('pk')).values('student').annotate(
            score=Sum(ExpressionWrapper(F('mcq_score') + F('practical_score'), output_field=IntegerField())),
            total=Sum(ExpressionWrapper(F('total_questions') + F('practical_total'), output_field=IntegerField())),
        )
        User = get_user_model()
        students = User.objects.filter(
            role='student', is_staff=False, is_superuser=False,
        ).annotate(
            total_points=Coalesce('progress__total_points', Value(0)),
            correct_answers=Coalesce('progress__correct_answers', Value(0)),
            incorrect_answers=Coalesce('progress__incorrect_answers', Value(0)),
            exam_score=Coalesce(Subquery(exam_totals.values('score')[:1], output_field=IntegerField()), Value(0)),
            exam_total=Coalesce(Subquery(exam_totals.values('total')[:1], output_field=IntegerField()), Value(0)),
            osce_score=Coalesce(Subquery(osce_totals.values('score')[:1], output_field=IntegerField()), Value(0)),
            osce_total=Coalesce(Subquery(osce_totals.values('total')[:1], output_field=IntegerField()), Value(0)),
        ).order_by('username')

        leaderboard = []
        for student in students:
            score = student.exam_score + student.osce_score
            total = student.exam_total + student.osce_total
            leaderboard.append({
                'student': student,
                'detail_url': reverse(
                    'admin:progress_studentprogress_student_detail', args=(student.pk,)
                ),
                'score': score,
                'percentage': round((score / total) * 100, 1) if total else 0,
                'total_points': student.total_points,
                'correct_answers': student.correct_answers,
                'incorrect_answers': student.incorrect_answers,
                'rank': rank_for_points(student.total_points),
            })
        leaderboard.sort(key=lambda entry: (-entry['score'], -entry['percentage'], entry['student'].username.lower()))
        for position, entry in enumerate(leaderboard, start=1):
            entry['position'] = position

        context = {
            **self.admin_site.each_context(request),
            'title': 'Full student leaderboard',
            'opts': self.model._meta,
            'leaderboard': leaderboard,
        }
        return TemplateResponse(request, 'admin/progress/studentprogress/leaderboard.html', context)


class BadgeAdminForm(forms.ModelForm):
    exam_year = forms.TypedChoiceField(
        choices=(( '', '---------'), *Exam.YEAR_CHOICES),
        coerce=int,
        required=False,
        label='Year',
    )
    exam_module = forms.ModelChoiceField(
        queryset=Module.objects.all(),
        required=False,
        label='Module',
        widget=ModuleByYearSelect,
    )
    module_year = forms.TypedChoiceField(
        choices=(( '', '---------'), *Exam.YEAR_CHOICES),
        coerce=int,
        required=False,
        label='Year',
    )
    target_module = forms.ModelChoiceField(
        queryset=Module.objects.all(),
        required=False,
        label='Module',
        widget=ModuleByYearSelect,
    )
    module_percentage = forms.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
        label='Required percentage',
        help_text='Combined first-attempt score required across this module’s exams.',
    )

    class Meta:
        model = Badge
        fields = '__all__'
        help_texts = {
            'threshold': (
                'Exam score: enter the required percentage (for example, 80 for 80%). '
                'Daily login streak: enter the required consecutive number of days. '
                'VIP badges are awarded manually and do not use a threshold.'
            ),
        }
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'aria-label': 'Badge color'}),
        }

    class Media:
        js = ('progress/admin/badge_exam_filter.js', 'progress/admin/badge_rule_type.js')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_exams = self.instance.exams.all() if self.instance and self.instance.pk else Exam.objects.none()
        selected_exam = selected_exams.first()
        selected_module = self.instance.module if self.instance and self.instance.pk else None
        exam_year = self.data.get('exam_year') or (selected_exam.year if selected_exam else None)
        exam_module = self.data.get('exam_module') or (selected_exam.module_id if selected_exam else None)
        module_year = self.data.get('module_year') or (selected_module.year if selected_module else None)
        target_module = self.data.get('target_module') or (selected_module.pk if selected_module else None)
        self.fields['exams'].queryset = Exam.objects.select_related('module').all()
        self.fields['exams'].widget = ExamByModuleSelect(choices=self.fields['exams'].choices)
        self.fields['threshold'].required = False
        self.initial.update({
            'exam_year': exam_year,
            'exam_module': exam_module,
            'module_year': module_year,
            'target_module': target_module,
            'module_percentage': self.instance.threshold if selected_module else None,
        })

    def clean(self):
        cleaned_data = super().clean()
        exam_year = cleaned_data.get('exam_year')
        exam_module = cleaned_data.get('exam_module')
        exams = cleaned_data.get('exams')
        rule_type = cleaned_data.get('rule_type')
        if rule_type == Badge.MODULE_PROGRESS:
            module_year = cleaned_data.get('module_year')
            target_module = cleaned_data.get('target_module')
            percentage = cleaned_data.get('module_percentage')
            if not module_year or not target_module or percentage is None:
                raise forms.ValidationError('Choose a year and module, then enter the required percentage.')
            if target_module.year != module_year:
                raise forms.ValidationError('The selected module must belong to the chosen year.')
            cleaned_data['module'] = target_module
            cleaned_data['threshold'] = percentage
            cleaned_data['exams'] = Exam.objects.none()
            self.instance.module = target_module
        elif rule_type == Badge.VIP:
            cleaned_data['threshold'] = 0
            cleaned_data['module'] = None
            cleaned_data['exams'] = Exam.objects.none()
            self.instance.module = None
        return cleaned_data


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    form = BadgeAdminForm
    fieldsets = (
        ('Badge details', {
            'fields': ('name', 'description', 'color', 'image_url', 'xp_reward', 'rule_type', 'is_active'),
        }),
        ('Exam targeting', {
            'fields': ('exam_year', 'exam_module', 'exams'),
            'description': 'Choose a year and module, then select one or more exams this badge should apply to.',
            'classes': ('exam-targeting',),
        }),
        ('Module details', {
            'fields': ('module_year', 'target_module', 'module_percentage'),
            'description': 'Choose a year and module, then the percentage required to earn this badge.',
            'classes': ('module-targeting',),
        }),
        ('Score or login requirement', {
            'fields': ('threshold',),
            'description': 'Enter the required exam percentage or consecutive login days.',
            'classes': ('threshold-targeting',),
        }),
    )
    list_display = ('name', 'rule_type', 'threshold_requirement', 'xp_reward', 'is_active', 'attached_exams', 'module')
    list_filter = ('rule_type', 'is_active')
    list_editable = ('xp_reward', 'is_active')
    search_fields = ('name',)

    @admin.display(description='Requirement')
    def threshold_requirement(self, obj):
        return obj.threshold_requirement

    @admin.display(description='Attached exams')
    def attached_exams(self, obj):
        return ', '.join(obj.exams.values_list('name', flat=True)) or 'All exams'


@admin.register(StudentBadge)
class StudentBadgeAdmin(admin.ModelAdmin):
    """Let staff manually award a configured badge to a selected student."""
    list_display = ('student', 'badge', 'awarded_at')
    list_filter = ('badge', 'awarded_at')
    search_fields = (
        'student__first_name', 'student__last_name', 'student__email',
        'student__phone', 'student__username', 'badge__name',
    )
    autocomplete_fields = ('student', 'badge')
    readonly_fields = ('awarded_at', 'source_key')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'badge')

    def save_model(self, request, obj, form, change):
        if not change:
            award, _ = _award_badge(
                student=obj.student,
                badge=obj.badge,
                source_key=f'manual:{uuid4()}',
            )
            obj.pk = award.pk
            obj.source_key = award.source_key
            obj.awarded_at = award.awarded_at
            return
        super().save_model(request, obj, form, change)


@admin.register(WeeklyGoal)
class WeeklyGoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'goal_type', 'target', 'xp_reward', 'is_active')
    list_filter = ('goal_type', 'is_active')
    list_editable = ('xp_reward', 'is_active')
    search_fields = ('name',)
