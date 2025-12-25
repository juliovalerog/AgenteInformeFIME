"""Parametros fijos del scoring determinista."""

from dataclasses import dataclass

@dataclass(frozen=True)
class ScoringConfig:
    # Pesos del scoring (deben sumar 1.0).
    w_return: float = 0.50
    w_vol: float = 0.30
    w_dd: float = 0.20

    # Hard stops.
    hardstop_return_lt: float = 0.0      # rentabilidad < 0%
    hardstop_dd_gt: float = 40.0         # drawdown > 40% (en valor absoluto)
    hardstop_vol_gt: float = 50.0        # volatilidad > 50%

    # Scoring final entero 1..10.
    score_min: int = 1
    score_max: int = 10
