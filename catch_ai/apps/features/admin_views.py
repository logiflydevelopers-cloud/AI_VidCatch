from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404

from .models import Features, FeatureSetting
from .serializers import FeatureUpdateSerializer
from apps.templates.models import AIModel


def get_model_name(model_id):
    if not model_id:
        return None
    model = AIModel.objects.filter(id=model_id).first()
    return model.name if model else None

# ==========================================================
# LIST FEATURES
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAdminUser])
def list_features(request):
    features = Features.objects.all()

    data = [
        {
            "id": f.id,
            "name": f.name,
            "feature_type": f.feature_type,
            "is_multi_mode": f.is_multi_mode,
            "is_active": f.is_active,
        }
        for f in features
    ]

    return Response(data)


# ==========================================================
# GET SINGLE FEATURE
# ==========================================================
@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_feature(request, feature_id):
    try:
        f = get_object_or_404(Features, id=feature_id)
        mapping = f.model_mapping or {}

        allowed_models = f.allowed_models.all()

        # ----------------------------------
        # BUILD NESTED MODEL MAPPING
        # ----------------------------------
        def build_model_mapping(data):
            if isinstance(data, dict):
                return {
                    key: build_model_mapping(value)
                    for key, value in data.items()
                }
            else:
                if not data:
                    return None
                return {
                    "id": data,
                    "name": get_model_name(data)
                }

        response = {
            "id": f.id,
            "name": f.name,
            "feature_type": f.feature_type,
            "is_multi_mode": f.is_multi_mode,
            "allowed_models": [
                {
                    "id": m.id,
                    "name": m.name
                }
                for m in allowed_models
            ],
            "is_active": f.is_active,
            "is_premium": f.is_premium,
            "credits_config": f.credits_config,
        }

        # ==========================================
        # MULTI MODE (NESTED SUPPORT)
        # ==========================================
        if f.is_multi_mode:
            response.update({
                "model_mapping": build_model_mapping(mapping),
            })

        # ==========================================
        # SINGLE MODE
        # ==========================================
        else:
            default_model_id = f.default_model_id

            response.update({
                "model_mapping": {
                    "default": {
                        "id": default_model_id,
                        "name": get_model_name(default_model_id)
                    } if default_model_id else None
                },
                "credit_cost": f.credit_cost
            })

        return Response(response)

    except Exception as e:
        return Response({"error": str(e)})
# ==========================================================
# UPDATE FEATURE
# ==========================================================
@api_view(["PATCH"])
@permission_classes([IsAdminUser])
def update_feature(request, feature_id):
    feature = get_object_or_404(Features, id=feature_id)

    data = request.data.copy()

    # =========================
    # MERGE MODEL MAPPING (FIXES OVERWRITE BUG)
    # =========================
    if "model_mapping" in data:
        existing_mapping = feature.model_mapping or {}
        incoming_mapping = data.get("model_mapping") or {}

        existing_mapping.update(incoming_mapping)
        data["model_mapping"] = existing_mapping

    # =========================
    # HANDLE MODE SWITCH
    # =========================
    is_multi_mode = data.get("is_multi_mode", feature.is_multi_mode)

    if not is_multi_mode:
        mapping = data.get("model_mapping") or feature.model_mapping or {}

        data["model_mapping"] = {
            "default": mapping.get("default")
        }

        data.pop("standard_credit_cost", None)
        data.pop("advanced_credit_cost", None)

    else:
        mapping = data.get("model_mapping") or feature.model_mapping or {}
        mapping.pop("default", None)
        data["model_mapping"] = mapping

    # =========================
    # SAVE FEATURE
    # =========================
    serializer = FeatureUpdateSerializer(
        feature,
        data=data,
        partial=True
    )

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    feature = serializer.save()

    # =========================
    # 🔥 AUTO SYNC SETTINGS FROM credits_config
    # =========================
    KEY_MAP = {
        "audio": "generate_audio"
    }

    credits_config = data.get("credits_config")

    if credits_config:

        existing_settings = {
            (s.mode, s.key): s
            for s in feature.settings.all()
        }

        incoming_keys = set()

        for key, value in credits_config.items():

            db_key = KEY_MAP.get(key, key)

            # =========================
            # CASE 1: BOOLEAN (audio)
            # =========================
            if all(isinstance(v, int) for v in value.values()):

                for mode in value.keys():

                    incoming_keys.add((mode, db_key))

                    FeatureSetting.objects.update_or_create(
                        feature=feature,
                        key=db_key,
                        mode=mode,
                        defaults={
                            "type": "boolean",
                            "options": [True, False],
                            "default_value": False,
                            "is_required": True
                        }
                    )

            # =========================
            # CASE 2: SELECT (duration/resolution)
            # =========================
            else:
                for mode, options_dict in value.items():

                    options = list(options_dict.keys())

                    incoming_keys.add((mode, db_key))

                    FeatureSetting.objects.update_or_create(
                        feature=feature,
                        key=db_key,
                        mode=mode,
                        defaults={
                            "type": "select",
                            "options": options,
                            "default_value": options[0] if options else None,
                            "is_required": True
                        }
                    )

        # =========================
        # DELETE REMOVED SETTINGS
        # =========================
        for (mode, key), obj in existing_settings.items():
            if (mode, key) not in incoming_keys:
                obj.delete()

    return Response(serializer.data)