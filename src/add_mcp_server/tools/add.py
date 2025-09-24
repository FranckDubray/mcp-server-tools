def run(a: float, b: float):
    """Sum two numbers."""
    return float(a) + float(b)

def spec():
    """Return the MCP function specification."""
    return {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Sum two numbers.",
            "parameters": {
                "type": "object",
                "required": ["a", "b"],
                "properties": {
                    "a": {"type": "number", "description": "First number"},
                    "b": {"type": "number", "description": "Second number"}
                },
                "additionalProperties": False
            }
        }
    }