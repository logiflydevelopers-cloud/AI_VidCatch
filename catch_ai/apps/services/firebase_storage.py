import uuid
import mimetypes
from .firebase import bucket


import uuid
import mimetypes
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