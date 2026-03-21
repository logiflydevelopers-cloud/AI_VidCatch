import uuid
import mimetypes
import requests
from .firebase import bucket


# ==========================================================
# GENERIC FILE UPLOAD (USER INPUT)
# ==========================================================
def upload_file(file, path):
    """
    Upload user file (image/video/etc) to Firebase (streaming optimized)
    """

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

    return blob.public_url


# ==========================================================
# USER INPUT UPLOAD
# ==========================================================
def upload_user_input(file, user_id):
    path = f"users/{user_id}/input"
    return upload_file(file, path)


# ==========================================================
# GENERATED FILE UPLOAD (IMAGE + VIDEO) - OPTIMIZED
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

    # PERFORMANCE BOOST
    blob.chunk_size = 5 * 1024 * 1024  # 5MB chunks

    # DIRECT STREAM PIPE (no full memory load)
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
        path = file_url.split(".appspot.com/")[-1]
        blob = bucket.blob(path)
        blob.delete()
    except Exception:
        pass