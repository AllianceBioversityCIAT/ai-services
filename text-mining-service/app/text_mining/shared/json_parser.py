import re
import json


def extract_json_from_markdown(text):
    """Extract JSON from markdown code blocks if present"""
    
    json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
    match = re.search(json_pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    
    return text.strip()


def is_valid_json(text):
    """Check if the text is a valid JSON string"""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False