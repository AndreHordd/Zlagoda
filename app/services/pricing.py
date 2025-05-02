# app/services/pricing.py
from decimal import Decimal, ROUND_HALF_UP

VAT_RATE         = Decimal('0.20')   # 20 %
PROMO_DISCOUNT   = Decimal('0.20')   # 20 %

def price_gross(net: Decimal) -> Decimal:
    """Нетто → з ПДВ, округлено до копійок."""
    return (net * (1 + VAT_RATE)).quantize(Decimal('0.01'), ROUND_HALF_UP)

def price_promo(gross_regular: Decimal) -> Decimal:
    """Акційна (з ПДВ) = gross_regular × 0.8."""
    return (gross_regular * (1 - PROMO_DISCOUNT)).quantize(Decimal('0.01'),
                                                           ROUND_HALF_UP)
