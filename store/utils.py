from decimal import Decimal
from .models import Product

def get_cart_items(session):
    cart = session.get('cart', {})
    items = []
    total = Decimal('0.00')
    total_gst = Decimal('0.00')
    for pid, qty in cart.items():
        try:
            p = Product.objects.get(id=pid)
        except Product.DoesNotExist:
            continue
        line = {
            'product': p,
            'quantity': qty,
            'unit_price': p.price,
            'line_total': p.price * qty,
            'gst': (p.gst_percent / Decimal('100.00')) * (p.price * qty)
        }
        total += line['line_total']
        total_gst += line['gst']
        items.append(line)
    return items, total, total_gst
