from decimal import Decimal, localcontext
import re
from typing import Dict, Any

_num_re = re.compile(r"^[+-]?(?:\d+(?:[\.,]\d+)?|[\.,]\d+)$")

def _normalize(s: str) -> str:
    s = s.strip().replace("_", "")
    if not s:
        raise ValueError("empty string")
    if not _num_re.match(s):
        raise ValueError(f"invalid number format: {s}")
    s = s.replace(",", ".")
    if s.startswith("."):
        s = "0" + s
    if s.startswith("-."):
        s = "-0" + s[1:]
    return s


def run(a: str, b: str) -> str:
    """Multiplication de deux décimaux signés de précision arbitraire.
    Entrée: a, b (strings). Sortie: string.
    - Supporte virgule ou point comme séparateur décimal
    - Le résultat est fourni sans notation scientifique
    """
    sa = _normalize(a)
    sb = _normalize(b)
    with localcontext() as ctx:
        # Définir une précision suffisante: digits(a)+digits(b)+10
        digits_a = len(sa.lstrip('+-').replace('.', ''))
        digits_b = len(sb.lstrip('+-').replace('.', ''))
        ctx.prec = max(50, digits_a + digits_b + 10)
        da = Decimal(sa)
        db = Decimal(sb)
        prod = da * db
        # Sortie canonique sans exposant
        return format(prod, 'f').rstrip('0').rstrip('.') if '.' in format(prod, 'f') else format(prod, 'f')


def spec() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "multiply",
            "description": "Multiplication de deux nombres décimaux signés en précision arbitraire. Entrée: 2 strings, Sortie: string.",
            "parameters": {
                "type": "object",
                "required": ["a", "b"],
                "properties": {
                    "a": {"type": "string", "description": "Opérande A (décimal signé)"},
                    "b": {"type": "string", "description": "Opérande B (décimal signé)"}
                },
                "additionalProperties": False
            }
        }
    }
