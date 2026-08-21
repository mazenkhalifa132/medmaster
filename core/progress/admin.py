from django import forms
from django.contrib import admin

from .models import Badge, Rank, WeeklyGoal


class RankAdminForm(forms.ModelForm):
    class Meta:
        model = Rank
        fields = '__all__'
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'aria-label': 'Rank color'}),
        }


@admin.register(Rank)
class RankAdmin(admin.ModelAdmin):
    form = RankAdminForm
    list_display = ('name', 'min_points', 'max_points', 'color', 'icon_class')
    list_editable = ('min_points', 'max_points', 'color', 'icon_class')
    ordering = ('min_points',)


class BadgeAdminForm(forms.ModelForm):
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


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    form = BadgeAdminForm
    list_display = ('name', 'rule_type', 'threshold_requirement', 'xp_reward', 'is_active')
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
