import uuid
import mimetypes
import requests
from .firebase import bucket


# ==========================================================
# GENERIC FILE UPLOAD (USER INPUT)
# ==========================================================
def upload_file(file, path):
    """
    Upload user file (image/video/etc) to Firebase
    """

    # get extension safely
    extension = file.name.split(".")[-1].lower()
    filename = f"{uuid.uuid4()}.{extension}"

    blob = bucket.blob(f"{path}/{filename}")

    # detect mime type
    content_type = getattr(file, "content_type", None)

    if not content_type:
        content_type, _ = mimetypes.guess_type(file.name)

    if not content_type:
        content_type = "application/octet-stream"

    # upload file
    blob.upload_from_string(
        file.read(),
        content_type=content_type
    )

    blob.make_public()

    return blob.public_url


# ==========================================================
# USER INPUT UPLOAD
# ==========================================================
def upload_user_input(file, user_id):
    """
    Upload user input files used for AI generation
    """
    path = f"users/{user_id}/input"
    return upload_file(file, path)


# ==========================================================
# GENERATED FILE UPLOAD (IMAGE + VIDEO)
# ==========================================================
def upload_generated_file(file_url, user_id):
    """
    Download AI generated file (image/video) and upload to Firebase
    """

    response = requests.get(file_url, timeout=60)

    if response.status_code != 200:
        raise Exception("Failed to download generated file")

    # extract extension safely
    extension = file_url.split(".")[-1].split("?")[0].lower()

    # supported extensions
    valid_extensions = [
        "png", "jpg", "jpeg", "webp",
        "mp4", "mov", "webm"
    ]

    if extension not in valid_extensions:
        extension = "bin"

    filename = f"{uuid.uuid4()}.{extension}"
    path = f"users/{user_id}/output/{filename}"

    blob = bucket.blob(path)

    # detect correct MIME type
    content_type, _ = mimetypes.guess_type(filename)

    if not content_type:
        content_type = "application/octet-stream"

    blob.upload_from_string(
        response.content,
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