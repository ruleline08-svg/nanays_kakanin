from django.http import JsonResponse
from django.conf import settings

def storage_debug(request):
    return JsonResponse({
        "DEFAULT_FILE_STORAGE": settings.DEFAULT_FILE_STORAGE,
        "CLOUDINARY_CLOUD_NAME": settings.CLOUDINARY_STORAGE.get("CLOUD_NAME"),
        "MEDIA_URL": settings.MEDIA_URL,
    })