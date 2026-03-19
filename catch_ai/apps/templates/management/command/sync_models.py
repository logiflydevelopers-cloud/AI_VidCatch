import requests
from django.core.management.base import BaseCommand
from apps.templates.models import AIModel
from django.conf import settings

FASTAPI_MODEL_REGISTRY_URL = settings.FASTAPI_MODEL_REGISTRY_URL


class Command(BaseCommand):
    help = "Sync AI Models from FastAPI"

    def handle(self, *args, **kwargs):

        try:
            response = requests.get(FASTAPI_MODEL_REGISTRY_URL)
            data = response.json().get("data", {})
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            return

        created = 0
        updated = 0

        all_model_keys = []

        for feature, models in data.items():

            for model_name, details in models.items():

                all_model_keys.append(model_name)

                obj, is_created = AIModel.objects.update_or_create(
                    model_name=model_name,
                    defaults={
                        "name": model_name.replace("_", " ").title(),
                        "feature_type": feature,
                        "provider": details.get("provider"),
                        "credit_cost": details.get("credit_cost", 1),
                        "is_active": True,
                    }
                )

                if is_created:
                    created += 1
                else:
                    updated += 1

        # deactivate removed models
        AIModel.objects.exclude(model_name__in=all_model_keys).update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync done → {created} created, {updated} updated"
            )
        )