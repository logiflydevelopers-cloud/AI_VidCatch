import uuid
import mimetypes
import requests
from .firebase import bucket


def upload_file(file, path):

    # generate clean filename
    extension = file.name.split(".")[-1]
    filename = f"{uuid.uuid4()}.{extension}"

    blob = bucket.blob(f"{path}/{filename}")

    # detect mime type
    content_type = file.content_type
    if not content_type:
        content_type, _ = mimetypes.guess_type(file.name)

    if not content_type:
        content_type = "application/octet-stream"

    # upload file bytes
    blob.upload_from_string(
        file.read(),
        content_type=content_type
    )

    blob.make_public()

    return blob.public_url


# ==========================================================
# USER INPUT IMAGE UPLOAD
# ==========================================================
def upload_user_input(file, user_id):
    """
    Upload user input images used for AI generation
    """

    path = f"users/{user_id}/input"

    return upload_file(file, path)


# ==========================================================
# DOWNLOAD IMAGE FROM URL AND STORE IN FIREBASE
# ==========================================================
def upload_generated_image(image_url, user_id):
    """
    Download AI generated image and upload to Firebase
    """

    response = requests.get(image_url, timeout=30)

    if response.status_code != 200:
        raise Exception("Failed to download generated image")

    extension = image_url.split(".")[-1].split("?")[0]

    if extension not in ["png", "jpg", "jpeg", "webp"]:
        extension = "png"

    filename = f"{uuid.uuid4()}.{extension}"

    path = f"users/{user_id}/output/{filename}"

    blob = bucket.blob(path)

    content_type = f"image/{extension}"

    blob.upload_from_string(
        response.content,
        content_type=content_type
    )

    blob.make_public()

    return blob.public_url


# ==========================================================
# DELETE FILE FROM FIREBASE
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