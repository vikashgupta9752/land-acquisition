"""File upload validators for security."""
import os
from django.core.exceptions import ValidationError


ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_document_file(value):
    """Validate document file extension and size."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise ValidationError(
            f'Unsupported file extension "{ext}". Allowed: {", ".join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}'
        )
    if value.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError('File size must not exceed 10 MB.')


def validate_image_file(value):
    """Validate image file extension and size."""
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'Unsupported image extension "{ext}". Allowed: {", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))}'
        )
    if value.size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError('Image size must not exceed 10 MB.')
