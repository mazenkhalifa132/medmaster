from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import redirect, render

from .models import Feedback, FeedbackSettings


def feedback_is_active():
    settings = FeedbackSettings.objects.order_by('pk').first()
    return settings is None or settings.is_active


@login_required(login_url='auth')
def submit_feedback(request):
    if not feedback_is_active():
        raise Http404('Feedback is currently unavailable.')

    already_submitted = Feedback.objects.filter(student=request.user).exists()
    if request.method == 'POST':
        if already_submitted:
            messages.info(request, 'You have already sent feedback. Thank you!')
            return redirect('feedback:submit')

        message = request.POST.get('message', '').strip()
        if not message:
            messages.error(request, 'Please write your feedback before submitting.')
        else:
            try:
                with transaction.atomic():
                    Feedback.objects.create(
                        student=request.user,
                        message=message,
                        hide_identity=request.POST.get('hide_identity') == 'on',
                    )
            except IntegrityError:
                messages.info(request, 'You have already sent feedback. Thank you!')
            else:
                messages.success(request, 'We received your feedback and are working on it. Thank you!')
            return redirect('feedback:submit')

    return render(request, 'feedback/submit.html', {'already_submitted': already_submitted})

# Create your views here.
