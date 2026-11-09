#!/usr/bin/env python3
"""Genera los datos de la figura alpha(m, u) del paper de SuperMinHash.

La formula (7) del paper es

    alpha(m, u) = 1 - sum_{l=1}^{m-1} l^u ((l+1)^u + (l-1)^u - 2 l^u)
                       / ((m-1)^(u-1) m^u (u-1))

Se calcula con enteros y fracciones exactas para evitar desbordes y perdida
de precision. El archivo de salida tiene una fila por valor de u y una columna
por cada tamano de firma m.
"""

from fractions import Fraction
from pathlib import Path

M_VALUES = (8, 16, 32, 64, 128)

U_VALUES = (
    list(range(2, 17))
    + [20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 112, 128]
    + [160, 192, 256, 320, 384, 512, 640, 768, 1024, 1280, 1536, 2048, 3072, 4096]
)


def alpha(m: int, u: int) -> float:
    """Reduccion de varianza alpha(m, u) usando aritmetica exacta."""
    numerator = sum(
        (l**u) * ((l + 1) ** u + (l - 1) ** u - 2 * (l**u)) for l in range(1, m)
    )
    denominator = (m - 1) ** (u - 1) * m**u * (u - 1)
    value = 1 - Fraction(numerator, denominator)
    return float(value)


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "data" / "alpha.dat"
    out.parent.mkdir(parents=True, exist_ok=True)

    header = "u " + " ".join(f"m{m}" for m in M_VALUES)
    rows = [header]

    for u in U_VALUES:
        values = [alpha(m, u) for m in M_VALUES]
        for value in values:
            if not 0.0 <= value < 1.0:
                raise ValueError(f"alpha fuera de rango: m={m}, u={u}, alpha={value}")
        rows.append(f"{u} " + " ".join(f"{value:.6f}" for value in values))

    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Escrito {out} ({len(U_VALUES)} valores de u, {len(M_VALUES)} valores de m)")


if __name__ == "__main__":
    main()
