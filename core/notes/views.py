from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from modules.models import Module

from .models import Note


@login_required(login_url='auth')
@require_POST
def create_note(request):
    year = request.POST.get('year', '').strip()
    module = Module.objects.filter(
        pk=request.POST.get('module'),
        year=year if year.isdigit() else None,
        is_active=True,
    ).first()
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()

    if not year.isdigit() or int(year) not in range(1, 6):
        messages.error(request, 'Choose a valid academic year.')
    elif not module:
        messages.error(request, 'Choose a module from the selected academic year.')
    elif not title or not content:
        messages.error(request, 'A note needs both a title and content.')
    else:
        Note.objects.create(
            student=request.user,
            year=int(year),
            module=module,
            title=title,
            content=content,
        )
        messages.success(request, 'Note saved.')

    return redirect(f'{reverse("home")}#notes')


@login_required(login_url='auth')
@require_POST
def delete_note(request, pk):
    deleted, _ = Note.objects.filter(pk=pk, student=request.user).delete()
    if deleted:
        messages.success(request, 'Note deleted.')
    else:
        messages.error(request, 'That note is unavailable.')
    return redirect(f'{reverse("home")}#notes')
