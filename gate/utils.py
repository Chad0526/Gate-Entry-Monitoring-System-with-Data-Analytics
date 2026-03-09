"""Helpers for events app (e.g. photo handling for gate verification)."""
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

PHOTO_MAX_WIDTH = 800
PHOTO_JPEG_QUALITY = 80


def compress_student_photo(file_in):
    """
    Normalize student face photo: convert to JPEG, max width 800px, quality 80.
    Returns an InMemoryUploadedFile suitable for saving to ImageField.
    Speeds up gate display and keeps storage small.
    """
    from PIL import Image
    if hasattr(file_in, 'seek'):
        file_in.seek(0)
    img = Image.open(file_in).convert('RGB')
    w, h = img.size
    if w > PHOTO_MAX_WIDTH or h > PHOTO_MAX_WIDTH:
        ratio = min(PHOTO_MAX_WIDTH / w, PHOTO_MAX_WIDTH / h)
        new_size = (int(w * ratio), int(h * ratio))
        resample = getattr(Image, 'Resampling', Image).LANCZOS
        img = img.resize(new_size, resample)
    out = BytesIO()
    img.save(out, format='JPEG', quality=PHOTO_JPEG_QUALITY, optimize=True)
    out.seek(0)
    return InMemoryUploadedFile(
        out, 'ImageField', 'face.jpg', 'image/jpeg', out.getbuffer().nbytes, None
    )
