from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "config/google_play.json"

SCOPES = ["https://www.googleapis.com/auth/androidpublisher"]


def verify_android_purchase(package_name, product_id, purchase_token):
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        service = build("androidpublisher", "v3", credentials=credentials)

        result = service.purchases().products().get(
            packageName=package_name,
            productId=product_id,
            token=purchase_token
        ).execute()

        return result

    except Exception as e:
        print("Google Play Verification Error:", str(e))
        return None