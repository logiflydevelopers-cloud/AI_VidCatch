def calculate_feature_cost(feature, mode=None, options=None):
    options = options or {}

    # normalize
    if feature.credits_config:
        credits = feature.credits_config
    elif feature.is_multi_mode:
        credits = {
            "fast": feature.fast_credit_cost,
            "standard": feature.standard_credit_cost,
            "advanced": feature.advanced_credit_cost
        }
    else:
        credits = {"default": feature.credit_cost}

    base = credits.get(mode) or credits.get("default", 0)
    total = base

    # map settings → addon keys
    for key, value in credits.items():
        if isinstance(value, dict):

            # map generate_audio → audio
            if key == "audio" and options.get("generate_audio"):
                total += value.get(mode, 0)

            # future generic support
            elif options.get(key):
                total += value.get(mode, 0)

    return total