TOOL_PARAMETERS = {
    # 🔥 Fire Tool
    "main_Campfire": ["flame size", "intensity", "flicker speed", "randomness", "opacity", "glow pulse"],
    "main_Torch": ["flame size", "intensity", "spark count", "opacity", "light radius"],
    "main_Candle": ["flame size", "flicker speed", "opacity", "smoke length"],
    "main_Lava": ["intensity", "grain", "distortion strength", "glow pulse", "smoke length"],

    "sub_sparks": ["spark count", "intensity"],
    "sub_smoke": ["intensity", "smoke length"],
    "sub_heat_distortion": ["distortion strength", "grain"],
    "sub_pulse": ["glow pulse", "intensity"],
    "sub_shadow_flicker": ["flicker speed", "opacity"],
    "sub_light_glow": ["light radius", "glow pulse"],

    # 💡 Light Tool
    "main_Firefly": ["intensity", "radius", "glow depth", "opacity", "pulse speed"],
    "main_Object_Light": ["intensity", "radius", "frequency", "duration", "glow depth", "count"],
    "main_lightning": ["bolt width", "light radius", "branch count", "frequency", "opacity", "duration"],

    "sub_pulse": ["pulse speed", "glow depth"],
    "sub_flicker": ["frequency", "intensity"],
    "sub_glow_spread": ["glow depth", "radius"],
    "sub_trail": ["duration", "opacity"],
    "sub_spark": ["count", "intensity"],
    "sub_flash": ["duration", "frequency"],
    "sub_radius_glow": ["radius", "glow depth"],
    "sub_focus_pulse": ["pulse speed", "focus"],
    "branches": ["branch count", "bolt width", "frequency"],

    # 🌊 Water Tool
    "main_waterfall": ["intensity", "power", "grain", "opacity", "randomness"],
    "main_river": ["intensity", "randomness", "opacity", "viscosity"],
    "main_Still_water": ["opacity", "transparency", "reflections", "grain"],

    "sub_waves": ["intensity", "randomness"],
    "sub_ripples": ["intensity", "grain"],
    "sub_splashes": ["power", "opacity"],
    "sub_Bubbles": ["intensity", "opacity"],
    "sub_reflections": ["opacity", "transparency"],
    "sub_Sediment": ["grain", "randomness"],
    "sub_foam": ["grain", "intensity"],
    "sub_transparency": ["opacity", "intensity"],
    "sub_viscosity": ["viscosity", "randomness"],
    "sub_wet_edge": ["intensity", "opacity"],
    "sub_caustics": ["intensity", "grain"],
    "sub_distortion": ["grain", "randomness", "power"],

    # ☁️ Weather Tool
    "main_Fog": ["intensity", "density", "opacity", "blur", "glow pulse"],
    "main_Wind": ["intensity", "drift speed", "pulse rate", "randomness"],
    "main_Smoke": ["intensity", "lift", "density", "glow pulse", "randomness"],
    "main_Vapour": ["intensity", "particle size", "lift", "glow pulse", "opacity"],

    "sub_swirls": ["intensity", "randomness", "blur"],
    "sub_drift": ["drift speed", "intensity"],
    "sub_gusts": ["pulse rate", "randomness"],
    "sub_density_pulse": ["density", "pulse rate"],
    "sub_fade_fluctuations": ["opacity", "glow pulse"],
    "sub_heat_lift": ["lift", "particle size", "intensity"],
}
