# cattle_tracker_app/constants.py

# Semen type for AI sires
SEMEN_TYPE_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('regular', 'Unsorted/Regular'),
]

# Breeding method
BREEDING_METHOD_CHOICES = [
    ('natural', 'Natural Breeding'),
    ('ai', 'Artificial Insemination'),
]

# Cleanup method after AI
CLEANUP_METHOD_CHOICES = [
    ('ai', 'Artificial Insemination'),
    ('natural', 'Natural Breeding'),
]
