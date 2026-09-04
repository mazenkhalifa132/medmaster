from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db.models import ExpressionWrapper, F, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.template.response import TemplateResponse
from django.urls import path

from exams.models import Exam, ExamAttempt
from modules.models import Module
from osce.models import OSCEAttempt

from .models import Badge, Rank, StudentProgress, WeeklyGoal, rank_for_points


class ModuleByYearSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, 'instance'):
            option['attrs']['data-year'] = value.instance.year
        return option


class ExamByModuleSelect(forms.Select):
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
    readonly_fields = ('student', 'total_points', 'correct_answers', 'incorrect_answers', 'updated_at')
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

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'leaderboard/',
                self.admin_site.admin_view(self.leaderboard_view),
                name='progress_studentprogress_leaderboard',
            ),
        ]
        return custom_urls + urls

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
                'Daily login streak: enter the required consecutive number of days.'
            ),
        }
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'aria-label': 'Badge color'}),
        }

    class Media:
        js = ('progress/admin/badge_exam_filter.js', 'progress/admin/badge_rule_type.js')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_exam = self.instance.exam if self.instance and self.instance.pk else None
        selected_module = self.instance.module if self.instance and self.instance.pk else None
        exam_year = self.data.get('exam_year') or (selected_exam.year if selected_exam else None)
        exam_module = self.data.get('exam_module') or (selected_exam.module_id if selected_exam else None)
        module_year = self.data.get('module_year') or (selected_module.year if selected_module else None)
        target_module = self.data.get('target_module') or (selected_module.pk if selected_module else None)
        self.fields['exam'].queryset = Exam.objects.select_related('module').all()
        self.fields['exam'].widget = ExamByModuleSelect(choices=self.fields['exam'].choices)
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
        exam = cleaned_data.get('exam')
        rule_type = cleaned_data.get('rule_type')
        if exam and (not exam_year or not exam_module):
            raise forms.ValidationError('Choose the year and module for the selected exam.')
        if exam and (exam.year != exam_year or exam.module_id != exam_module.pk):
            raise forms.ValidationError('The selected exam must belong to the chosen year and module.')
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
            cleaned_data['exam'] = None
            self.instance.module = target_module
            self.instance.exam = None
        return cleaned_data


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    form = BadgeAdminForm
    fieldsets = (
        ('Badge details', {
            'fields': ('name', 'color', 'image_url', 'xp_reward', 'rule_type', 'is_active'),
        }),
        ('Exam targeting', {
            'fields': ('exam_year', 'exam_module', 'exam'),
            'description': 'Choose a year, then a module, then the exam this badge should apply to.',
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
    list_display = ('name', 'rule_type', 'threshold_requirement', 'xp_reward', 'is_active', 'exam', 'module')
    list_filter = ('rule_type', 'is_active')
    list_editable = ('xp_reward', 'is_active')
    search_fields = ('name',)

    @admin.display(description='Requirement')
    def threshold_requirement(self, obj):
        return obj.threshold_requirement


@admin.register(WeeklyGoal)
class WeeklyGoalAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'goal_type', 'target', 'xp_reward', 'is_active')
    list_filter = ('goal_type', 'is_active')
    list_editable = ('xp_reward', 'is_active')
    search_fields = ('name',)
