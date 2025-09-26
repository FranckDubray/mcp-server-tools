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

def _frac_len(s: str) -> int:
    s2 = s.lstrip("+-")
    if "." in s2:
        return len(s2.split(".")[1])
    return 0

def _digits_count(s: str) -> int:
    s2 = s.lstrip("+-").replace(".", "")
    return len(s2)

def _quantize_fixed(d: Decimal, frac_len: int) -> Decimal:
    if frac_len > 0:
        q = Decimal(1).scaleb(-frac_len)  # 10^-frac_len
        return d.quantize(q)
    else:
        return d.quantize(Decimal(1))


def run(a: str, b: str) -> str:
    """Addition de deux décimaux signés de précision arbitraire.
    Entrée: a, b (strings). Sortie: string.
    - Supporte virgule ou point comme séparateur décimal
    - Préserve le nombre de décimales le plus grand des deux opérandes
    """
    sa = _normalize(a)
    sb = _normalize(b)
    fa = _frac_len(sa)
    fb = _frac_len(sb)
    frac_len = max(fa, fb)
    prec = max(50, _digits_count(sa) + _digits_count(sb) + 10)
    with localcontext() as ctx:
        ctx.prec = prec
        da = Decimal(sa)
        db = Decimal(sb)
        dsum = da + db
        dq = _quantize_fixed(dsum, frac_len)
        # Normaliser -0.00 -> 0.00 ou 0
        if dq == 0:
            return "0." + ("0" * frac_len) if frac_len > 0 else "0"
        return format(dq, 'f')


def spec() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Addition de deux nombres décimaux signés en précision arbitraire. Entrée: 2 strings, Sortie: string.",
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
