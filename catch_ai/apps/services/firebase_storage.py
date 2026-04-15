import uuid
import mimetypes
import requests
from .firebase import bucket


# ==========================================================
# COMMON VALIDATIONS
# ==========================================================
ALLOWED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"]
ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime"]

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


# ==========================================================
# GENERIC FILE UPLOAD (USER INPUT)
# ==========================================================
def upload_file(file, path):
    """
    Upload user file (image/video/etc) to Firebase (streaming optimized)
    """

    # Validate size
    if file.size > MAX_FILE_SIZE:
        raise Exception("File too large (max 20MB allowed)")

    extension = file.name.split(".")[-1].lower()
    filename = f"{uuid.uuid4()}.{extension}"

    blob = bucket.blob(f"{path}/{filename}")

    # detect mime type
    content_type = getattr(file, "content_type", None)

    if not content_type:
        content_type, _ = mimetypes.guess_type(file.name)

    if not content_type:
        content_type = "application/octet-stream"

    blob.chunk_size = 5 * 1024 * 1024  # 5MB chunks

    blob.upload_from_file(
        file,
        content_type=content_type,
        rewind=True
    )

    blob.make_public()

    return blob.public_url, content_type


# ==========================================================
# BANNER MEDIA UPLOAD
# ==========================================================
def upload_banner_media(file):
    """
    Upload banner image/video to Firebase (banners folder)
    """

    content_type = getattr(file, "content_type", None)

    if not content_type:
        content_type, _ = mimetypes.guess_type(file.name)

    if content_type in ALLOWED_IMAGE_TYPES:
        media_type = "image"

    elif content_type in ALLOWED_VIDEO_TYPES:
        media_type = "video"

    else:
        raise Exception("Invalid file type. Only images/videos allowed.")

    url, _ = upload_file(file, "banners")

    return url, media_type


# ==========================================================
# USER INPUT UPLOAD
# ==========================================================
def upload_user_input(file, user_id):
    path = f"users/{user_id}/input"
    url, _ = upload_file(file, path)
    return url


# ==========================================================
# GENERATED FILE UPLOAD (IMAGE + VIDEO)
# ==========================================================
def upload_generated_file(file_url, user_id):
    """
    Stream download AI generated file and upload to Firebase (NO RAM LOAD)
    """
    response = requests.get(file_url, stream=True, timeout=120)

    if response.status_code != 200:
        raise Exception("Failed to download generated file")

    # extract extension safely
    extension = file_url.split(".")[-1].split("?")[0].lower()

    valid_extensions = [
        "png", "jpg", "jpeg", "webp",
        "mp4", "mov", "webm"
    ]

    if extension not in valid_extensions:
        extension = "bin"

    filename = f"{uuid.uuid4()}.{extension}"
    path = f"users/{user_id}/output/{filename}"

    blob = bucket.blob(path)

    # detect MIME type
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"

    blob.chunk_size = 5 * 1024 * 1024  # 5MB chunks

    blob.upload_from_file(
        response.raw,
        content_type=content_type
    )

    blob.make_public()

    return blob.public_url


# ==========================================================
# DELETE FILE
# ==========================================================
def delete_file(file_url):
    """
    Delete file from Firebase using public URL
    """
    try:
        if not file_url:
            return

        # safer extraction
        if ".appspot.com/" in file_url:
            path = file_url.split(".appspot.com/")[-1]
        else:
            return

        blob = bucket.blob(path)

        if blob.exists():
            blob.delete()

    except Exception as e:
        print("Delete failed:", str(e))

# ==========================================================
# PLAN SLIDE MEDIA UPLOAD
# ==========================================================
def upload_plan_slide(file):
    """
    Upload plan slide media to Firebase
    Path: plan_media/
    """

    # Validate size
    if file.size > MAX_FILE_SIZE:
        raise Exception("File too large")

    content_type = getattr(file, "content_type", None)

    if not content_type:
        content_type, _ = mimetypes.guess_type(file.name)

    if content_type in ALLOWED_IMAGE_TYPES:
        media_type = "image"

    elif content_type in ALLOWED_VIDEO_TYPES:
        media_type = "video"

    else:
        raise Exception("Invalid file type")

    url, _ = upload_file(file, "plan_media")

    return url, media_type