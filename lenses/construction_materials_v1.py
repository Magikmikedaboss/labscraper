# Materials Performance Lens v1
# Extracts material properties, measurements, and comparisons from construction science text.

LENS_ID = "materials_performance_v1"

TARGET_ENTITIES = [
    "material",
    "property",
    "value",
    "unit",
    "test_method"
]

KEYWORDS = [
    # Properties and measurements
    "compressive strength", "modulus", "conductivity", "permeability", "chloride diffusion",
    # Comparisons
    "increased by", "reduced by",
    # Curing age
    "7 days", "28 days", "90 days"
]

OUTPUT_TYPES = [
    "material",
    "property",
    "value",
    "unit",
    "test_method"
]
