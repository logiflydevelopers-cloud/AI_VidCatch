def calculate_feature_cost(feature, mode=None, options=None):
    options = options or {}

    credits = feature.credits_config or {}

    total = 0

    # ==========================================
    # 🎬 DURATION (MAIN COST)
    # ==========================================
    duration_config = credits.get("duration", {})
    mode_duration = duration_config.get(mode, {})

    selected_duration = options.get("duration")

    if selected_duration and selected_duration in mode_duration:
        total += mode_duration[selected_duration]
    elif mode_duration:
        # fallback → minimum cost
        total += min(mode_duration.values())

    # ==========================================
    # 🎥 RESOLUTION (OPTIONAL ADD-ON)
    # ==========================================
    resolution_config = credits.get("resolution", {})
    mode_resolution = resolution_config.get(mode, {})

    selected_resolution = options.get("resolution")

    if selected_resolution and selected_resolution in mode_resolution:
        total += mode_resolution[selected_resolution]

    # ==========================================
    # 🔊 AUDIO (BOOLEAN + COST)
    # ==========================================
    audio_config = credits.get("audio", {})
    mode_audio = audio_config.get(mode)

    if isinstance(mode_audio, dict):
        # new structure → { enabled, cost }
        if options.get("generate_audio") and mode_audio.get("enabled"):
            total += mode_audio.get("cost", 0)

    elif isinstance(mode_audio, bool):
        # fallback old structure (just true/false)
        if options.get("generate_audio") and mode_audio:
            total += 0  # no cost defined

    # ==========================================
    # 🔥 FUTURE GENERIC SUPPORT
    # ==========================================
    for key, value in credits.items():

        if key in ["duration", "resolution", "audio"]:
            continue

        if isinstance(value, dict):
            mode_data = value.get(mode)

            if isinstance(mode_data, dict):
                selected = options.get(key)

                if selected and selected in mode_data:
                    total += mode_data[selected]

            elif isinstance(mode_data, (int, float)):
                if options.get(key):
                    total += mode_data

    return total