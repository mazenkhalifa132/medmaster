from pathlib import Path

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import TextContentImage


MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_SIGNATURES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG\r\n\x1a\n': 'image/png',
    b'GIF87a': 'image/gif',
    b'GIF89a': 'image/gif',
    b'RIFF': 'image/webp',
}
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}


def can_upload_text_images(user):
    return user.is_authenticated and user.is_staff and (
        user.has_perm('text.add_textcontent') or user.has_perm('text.change_textcontent')
    )


def detected_image_type(upload):
    header = upload.read(12)
    upload.seek(0)
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'image/webp'
    for signature, content_type in IMAGE_SIGNATURES.items():
        if header.startswith(signature):
            return content_type
    return None


@login_required
@user_passes_test(can_upload_text_images)
@require_POST
def upload_editor_image(request):
    upload = request.FILES.get('image')
    if not upload:
        return JsonResponse({'error': 'Choose an image to upload.'}, status=400)
    if upload.size > MAX_IMAGE_SIZE:
        return JsonResponse({'error': 'Images must be 5 MB or smaller.'}, status=400)
    extension = Path(upload.name).suffix.lower().lstrip('.')
    content_type = detected_image_type(upload)
    if extension not in {'jpg', 'jpeg', 'png', 'gif', 'webp'} or content_type not in ALLOWED_IMAGE_TYPES:
        return JsonResponse({'error': 'Only JPG, PNG, GIF, and WebP images are allowed.'}, status=400)
    image = TextContentImage.objects.create(uploaded_by=request.user, image=upload)
    return JsonResponse({'url': image.image.url})
