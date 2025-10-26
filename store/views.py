# store/views.py (abbreviated)
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import Product, Category, Order, OrderItem
from .utils import get_cart_items
from decimal import Decimal
from django.conf import settings
import razorpay
from reportlab.pdfgen import canvas
from io import BytesIO

def home(request):
    return render(request, 'store/home.html')

def shop(request):
    cat_slug = request.GET.get('category')
    categories = Category.objects.all()
    qs = Product.objects.all()
    if cat_slug:
        qs = qs.filter(category__slug=cat_slug)
    return render(request, 'store/shop.html', {'products': qs, 'categories': categories})

def add_to_cart(request):
    # expected POST JSON: {product_id: int, quantity: int}
    if request.method == 'POST':
        pid = str(request.POST.get('product_id'))
        qty = int(request.POST.get('quantity', 1))
        cart = request.session.get('cart', {})
        cart[pid] = cart.get(pid, 0) + qty
        request.session['cart'] = cart
        items, total, gst = get_cart_items(request.session)
        return JsonResponse({'status':'ok','cart_count': sum(cart.values()), 'total': str(total + gst)})
    return JsonResponse({'status':'fail'}, status=400)

def cart_view(request):
    items, subtotal, total_gst = get_cart_items(request.session)
    return render(request, 'store/cart.html', {'items': items, 'subtotal': subtotal, 'total_gst': total_gst, 'total': subtotal + total_gst})

def update_cart(request):
    # increment, decrement, or remove via POST: action, product_id
    if request.method == 'POST':
        action = request.POST.get('action')
        pid = str(request.POST.get('product_id'))
        cart = request.session.get('cart', {})
        if pid not in cart:
            return JsonResponse({'status':'noitem'}, status=404)
        if action == 'increment':
            cart[pid] += 1
        elif action == 'decrement':
            cart[pid] = max(1, cart[pid]-1)
        elif action == 'delete':
            cart.pop(pid, None)
        request.session['cart'] = cart
        items, subtotal, gst = get_cart_items(request.session)
        return JsonResponse({'status':'ok','subtotal': str(subtotal),'gst': str(gst),'total': str(subtotal+gst),'cart_count': sum(cart.values())})
    return JsonResponse({'status':'fail'}, status=400)

# store/views.py (only the updated parts shown)
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from .models import Product, Category, Order, OrderItem
from .utils import get_cart_items
from decimal import Decimal
from django.conf import settings
import razorpay
from reportlab.pdfgen import canvas
from io import BytesIO

# helper to get razorpay client
def _razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))




def payment_success(request):
    """
    POST endpoint called after Razorpay payment. Expects:
    - razorpay_payment_id
    - razorpay_order_id
    - razorpay_signature
    Verifies signature, then marks DB order as paid and returns JSON with order_id.
    """
    if request.method == 'POST':
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')

        if not (payment_id and order_id and signature):
            return JsonResponse({'status': 'fail', 'error': 'missing_parameters'}, status=400)

        client = _razorpay_client()
        # Verify signature
        try:
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            client.utility.verify_payment_signature(params_dict)
        except Exception as e:
            # signature verification failed
            return JsonResponse({'status': 'fail', 'error': 'signature_verification_failed'}, status=400)

        # signature valid -> find our DB order and mark paid
        try:
            order = Order.objects.get(razorpay_order_id=order_id)
        except Order.DoesNotExist:
            return JsonResponse({'status': 'fail', 'error': 'order_not_found'}, status=404)

        order.razorpay_payment_id = payment_id
        order.paid = True
        order.save()

        # clear session cart
        request.session['cart'] = {}

        return JsonResponse({'status': 'ok', 'order_id': order.id})

    return JsonResponse({'status': 'fail'}, status=400)



from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from .models import Product, Category, Order, OrderItem
from .utils import get_cart_items
from decimal import Decimal
from io import BytesIO
from reportlab.pdfgen import canvas

# -----------------------
# Checkout page + simulated payment
# -----------------------
def checkout(request):
    items, subtotal, total_gst = get_cart_items(request.session)
    total_amount = subtotal + total_gst

    if request.method == 'POST':
        data = request.POST

        # 1️⃣ Create real order in DB
        order = Order.objects.create(
            first_name=data.get('first_name'),
            last_name=data.get('last_name',''),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            city=data.get('city'),
            paid=True  # since simulated
        )

        # 2️⃣ Create OrderItems
        for line in items:
            OrderItem.objects.create(
                order=order,
                product=line['product'],
                unit_price=line['unit_price'],
                quantity=line['quantity']
            )

        # 3️⃣ Clear cart session
        request.session['cart'] = {}

        # 4️⃣ Respond with order_id
        return JsonResponse({'status':'ok','order_id': order.id})

    # GET
    return render(request, 'store/checkout.html', {
        'cart_items': items,
        'subtotal': subtotal,
        'total_gst': total_gst,
        'total': total_amount,
        'gst_percent': items[0]['product'].gst_percent if items else 0
    })


# -----------------------
# Success page
# -----------------------
# store/views.py
from django.shortcuts import render, get_object_or_404
from .models import Order

def order_success(request, order_id):
    print("✅ order_success view reached with ID:", order_id)
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'store/order_success.html', {'order': order})



# -----------------------
# Invoice PDF
# -----------------------
def invoice_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50,800, "INVOICE")
    p.setFont("Helvetica", 12)
    p.drawString(50,780, f"Order ID: {order.id}")
    p.drawString(50,760, f"Name: {order.first_name} {order.last_name}")
    p.drawString(50,740, f"Email: {order.email}")
    y = 700
    p.drawString(50,y, "Items:")
    y -= 20
    for item in order.items.all():
        p.drawString(60,y, f"{item.product.name} x{item.quantity}  ₹{item.line_total():.2f}")
        y -= 16
        p.drawString(80,y, f"GST {item.product.gst_percent}%: ₹{item.gst_amount():.2f}")
        y -= 22
    p.drawString(50,y-10, f"Total: ₹{order.total():.2f}")
    p.showPage()
    p.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=invoice_order_{order.id}.pdf'
    return response
