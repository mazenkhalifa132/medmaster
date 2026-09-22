from .views import feedback_is_active


def feedback_status(request):
    return {'feedback_is_active': feedback_is_active()}
