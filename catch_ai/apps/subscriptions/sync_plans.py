from .models import Plan
from apps.services.firebase import db


def sync_plans():
    plans_ref = db.collection("plans")
    docs = plans_ref.stream()

    firebase_ids = []

    for doc in docs:
        data = doc.to_dict()
        firebase_ids.append(doc.id)

        Plan.objects.update_or_create(
            id=doc.id,   # IMPORTANT: keep same ID as Firebase
            defaults={
                "name": data.get("name"),
                "credits_per_month": data.get("credits_per_month", 0),
                "price_inr": data.get("price_inr", 0),
                "daily_limit": data.get("daily_limit"),
                "features": data.get("features", []),
                "validity_days": data.get("validity_days", 30),
                "is_active": data.get("is_active", True),
            }
        )

    # DELETE plans not in Firebase
    Plan.objects.exclude(id__in=firebase_ids).delete()

    return True