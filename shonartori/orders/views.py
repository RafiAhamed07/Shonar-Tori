from django.shortcuts import render, redirect, get_object_or_404
from products.models import Cart
from .models import Order, OrderItem

import uuid
from sslcommerz_lib import SSLCOMMERZ
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required


@login_required(login_url="login")
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()

    if not cart or not cart.cart_items.all():
        return redirect("view-cart")

    total = sum(item.get_total_price() for item in cart.cart_items.all())

    if request.method == "POST":
        address = request.POST.get("address")
        phone = request.POST.get("phone")

        # Create Order
        order = Order.objects.create(
            user=request.user, total_price=total, address=address, phone=phone
        )

        # Create Order Items
        for item in cart.cart_items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
            )

        # Clear cart
        cart.cart_items.all().delete()

        return redirect("order-success")

    return render(request, "checkout.html", {"cart": cart, "total": total})


@login_required(login_url="login")
def order_success(request):
    return render(request, "order_success.html")


@login_required(login_url="login")
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "my_orders.html", {"orders": orders})


@login_required(login_url="login")
def order_detail(request, uid):
    order = get_object_or_404(Order, uid=uid, user=request.user)
    return render(request, "order_detail.html", {"order": order})


@login_required(login_url="login")
def cancel_order(request, uid):
    order = get_object_or_404(Order, uid=uid, user=request.user)

    # Only allow cancel if not completed
    if order.status in ["pending", "processing"]:
        order.status = "cancelled"
        order.save()

    return redirect("my-orders")


def initiate_payment(request):
    if request.method != "POST":
        return redirect("checkout")

    cart = Cart.objects.filter(user=request.user).first()

    if not cart or not cart.cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("view-cart")

    # ✅ GET DATA FROM FORM
    address = request.POST.get("address")
    phone = request.POST.get("phone")

    if not address or not phone:
        messages.warning(request, "Address and phone are required for payment.")
        return redirect("checkout")

    if not settings.SSL_STORE_ID or not settings.SSL_STORE_PASSWORD:
        messages.error(
            request,
            "Payment gateway credentials are missing. Please set SSL_STORE_ID and SSL_STORE_PASSWORD.",
        )
        return redirect("checkout")

    total = sum(item.get_total_price() for item in cart.cart_items.all())
    tran_id = str(uuid.uuid4())

    # ✅ SAVE address & phone HERE
    order = Order.objects.create(
        user=request.user,
        total_price=total,
        transaction_id=tran_id,
        status="pending",
        address=address,
        phone=phone,
    )

    for item in cart.cart_items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price,
        )

    sslcz = SSLCOMMERZ(
        {
            "store_id": settings.SSL_STORE_ID,
            "store_pass": settings.SSL_STORE_PASSWORD,
            "issandbox": settings.SSL_SANDBOX,
        }
    )

    post_body = {
        "total_amount": total,
        "currency": "BDT",
        "tran_id": tran_id,
        "success_url": request.build_absolute_uri("/orders/callback/success/"),
        "fail_url": request.build_absolute_uri("/orders/callback/fail/"),
        "cancel_url": request.build_absolute_uri("/orders/callback/cancel/"),
        "cus_name": request.user.username,
        "cus_email": request.user.email,
        "cus_phone": phone,  # ✅ USE FORM DATA
        "cus_add1": address,  # ✅ USE FORM DATA
        "cus_city": "Dhaka",
        "cus_country": "Bangladesh",
        "shipping_method": "NO",
        "product_name": "EWU Order",
        "product_category": "General",
        "product_profile": "general",
    }

    response = sslcz.createSession(post_body)
    gateway_url = response.get("GatewayPageURL")
    if gateway_url:
        return redirect(gateway_url)

    order.status = "failed"
    order.save(update_fields=["status"])
    messages.error(request, response.get("failedreason", "Unable to initialize payment session."))
    return redirect("checkout")


from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def payment_success(request):
    tran_id = request.POST.get("tran_id") or request.GET.get("tran_id")
    order = Order.objects.filter(transaction_id=tran_id).first()
    if order:
        order.status = "paid"
        order.save()
        # Clear cart items
        cart = Cart.objects.filter(user=order.user).first()
        if cart:
            cart.cart_items.all().delete()
    return redirect("order-success")


@csrf_exempt
def payment_fail(request):
    tran_id = request.POST.get("tran_id") or request.GET.get("tran_id")
    order = Order.objects.filter(transaction_id=tran_id).first()
    if order:
        order.status = "failed"
        order.save()
    messages.error(request, "Payment failed. Please try again.")
    return redirect("view-cart")


@csrf_exempt
def payment_cancel(request):
    tran_id = request.POST.get("tran_id") or request.GET.get("tran_id")
    order = Order.objects.filter(transaction_id=tran_id).first()
    if order:
        order.status = "cancelled"
        order.save()
    messages.warning(request, "Payment was cancelled.")
    return redirect("view-cart")
