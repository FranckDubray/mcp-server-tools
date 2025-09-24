"""Square a number tool - MCP format"""

def run(x: float) -> float:
    """Square a number."""
    return float(x) * float(x)

def spec():
    """Return the MCP function specification."""
    return {
        "type": "function",
        "function": {
            "name": "square",
            "description": "Square a number (multiply by itself)",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "number",
                        "description": "The number to square"
                    }
                },
                "required": ["x"],
                "additionalProperties": False
            }
        }
    }