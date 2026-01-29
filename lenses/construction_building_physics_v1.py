# Building Physics Lens v1
# Extracts building physics metrics, assemblies, and climate factors from construction science text.

LENS_ID = "building_physics_v1"

TARGET_ENTITIES = [
    "assembly",
    "system",
    "physics_metric",
    "climate_factor"
]

KEYWORDS = [
    # Metrics
    "U-value", "R-value", "infiltration", "ventilation", "dew point", "condensation", "hygrothermal", "energy load",
    # Moisture/mold
    "moisture", "mold"
]

OUTPUT_TYPES = [
    "assembly",
    "system",
    "physics_metric",
    "climate_factor"
]
