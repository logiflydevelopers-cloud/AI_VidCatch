import firebase_admin
from firebase_admin import credentials, storage, firestore
from django.conf import settings

if not firebase_admin._apps:
    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
    firebase_admin.initialize_app(cred, {
        "storageBucket": settings.FIREBASE_STORAGE_BUCKET
    })

bucket = storage.bucket()
db = firestore.client()