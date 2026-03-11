"""
Jewellery Type Constants

This file maps jewellery types to their categories and human parts.
Used for the WhatsApp conversation flow.
"""

# List of all jewellery types with their mappings
JEWELLERY_TYPES = [
    {
        "id": "ring",
        "label": "Ring",
        "option": "A",
        "category": "hand",
        "human_part": "finger",
    },
    {
        "id": "bangle",
        "label": "Bangle",
        "option": "B",
        "category": "hand",
        "human_part": "wrist",
    },
    {
        "id": "necklace",
        "label": "Necklace",
        "option": "C",
        "category": "neck",
        "human_part": "neck",
    },
    {
        "id": "earrings",
        "label": "Earrings",
        "option": "D",
        "category": "ear",
        "human_part": "ear",
    },
]


def get_all_jewellery_types():
    """
    Get all jewellery types as a list.
    
    Returns:
        list: List of jewellery type dictionaries
    """
    return JEWELLERY_TYPES.copy()


def get_jewellery_type_by_option(option: str):
    """
    Get jewellery type by option letter (case-insensitive).
    
    Args:
        option: Single letter option (e.g., "A", "a", "ring")
        
    Returns:
        dict or None: Jewellery type document if found
    """
    option_upper = option.strip().upper()
    option_lower = option.strip().lower()
    
    # First try to match by option letter
    for jt in JEWELLERY_TYPES:
        if jt["option"].upper() == option_upper:
            return jt
    
    # If no match by option, try to match by id
    for jt in JEWELLERY_TYPES:
        if jt["id"].lower() == option_lower:
            return jt
            
    return None


def get_jewellery_type_by_id(jewellery_id: str):
    """
    Get jewellery type by ID.
    
    Args:
        jewellery_id: The unique identifier (e.g., "ring", "bangle")
        
    Returns:
        dict or None: Jewellery type document if found
    """
    for jt in JEWELLERY_TYPES:
        if jt["id"] == jewellery_id:
            return jt
    return None


def build_jewellery_options_text():
    """
    Build the options text for the jewellery type question.
    
    Returns:
        str: Formatted options string
    """
    options = []
    for jt in JEWELLERY_TYPES:
        options.append(f"{jt['option']}. {jt['label']}")
    return "\n".join(options)


# Image type options
IMAGE_TYPES = [
    {
        "id": "plain",
        "label": "Plain background",
        "option": "A",
    },
    {
        "id": "human",
        "label": "On human",
        "option": "B",
    },
    {
        "id": "aesthetic",
        "label": "Aesthetic background",
        "option": "C",
    },
]


def get_image_type_by_option(option: str):
    """
    Get image type by option letter.
    
    Args:
        option: Single letter option (A, B, C)
        
    Returns:
        dict or None: Image type document if found
    """
    option_upper = option.strip().upper()
    for it in IMAGE_TYPES:
        if it["option"].upper() == option_upper:
            return it
    return None


def build_image_type_options_text(jewellery_type: dict = None):
    """
    Build the options text for the image type question.
    
    Args:
        jewellery_type: Optional jewellery type dict with human_part
        
    Returns:
        str: Formatted options string
    """
    options = []
    for it in IMAGE_TYPES:
        if it["id"] == "human" and jewellery_type:
            options.append(f"{it['option']}. On human ({jewellery_type['human_part']})")
        else:
            options.append(f"{it['option']}. {it['label']}")
    return "\n".join(options)
