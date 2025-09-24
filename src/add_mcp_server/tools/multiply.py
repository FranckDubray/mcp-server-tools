def run(a: float, b: float):
    """Multiply two numbers."""
    return float(a) * float(b)

def spec():
    """Return the MCP function specification."""
    return {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiply two numbers together.",
            "parameters": {
                "type": "object",
                "required": ["a", "b"],
                "properties": {
                    "a": {"type": "number", "description": "First number to multiply"},
                    "b": {"type": "number", "description": "Second number to multiply"}
                },
                "additionalProperties": False
            }
        }
    }