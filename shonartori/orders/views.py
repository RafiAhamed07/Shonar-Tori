from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from products.models import Cart
from .models import Order, OrderItem

import uuid
from sslcommerz_lib import SSLCOMMERZ
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .inventory import (
    InsufficientStock,
    assert_cart_has_stock,
    commit_inventory_for_order,
    restore_inventory_for_order,
)


@login_required(login_url="login")
def checkout(request):
    cart = Cart.objects.filter(user=request.user).first()

    if not cart or not cart.cart_items.all():
        return redirect("view-cart")

    total = sum(item.get_total_price() for item in cart.cart_items.all())

    if request.method == "POST":
        address = request.POST.get("address")
        phone = request.POST.get("phone")

        try:
            assert_cart_has_stock(cart)
        except InsufficientStock as exc:
            messages.error(request, str(exc))
            return redirect("view-cart")

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user, total_price=total, address=address, phone=phone
                )
                for item in cart.cart_items.all():
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price,
                    )
                commit_inventory_for_order(order)
                cart.cart_items.all().delete()
        except InsufficientStock as exc:
            messages.error(request, str(exc))
            return redirect("view-cart")

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

    if order.status == "pending":
        try:
            with transaction.atomic():
                if order.inventory_committed:
                    restore_inventory_for_order(order)
                order.status = "cancelled"
                order.save(update_fields=["status"])
        except Exception:
            messages.error(request, "Could not cancel order.")
            return redirect("my-orders")
        messages.success(request, "Order cancelled.")

    return redirect("my-orders")


@login_required(login_url="login")
def initiate_payment(request):
    if request.method != "POST":
        return redirect("checkout")

    cart = Cart.objects.filter(user=request.user).first()

    if not cart or not cart.cart_items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect("view-cart")

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

    try:
        assert_cart_has_stock(cart)
    except InsufficientStock as exc:
        messages.error(request, str(exc))
        return redirect("view-cart")

    total = sum(item.get_total_price() for item in cart.cart_items.all())
    tran_id = str(uuid.uuid4())

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
        "cus_phone": phone,
        "cus_add1": address,
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


@csrf_exempt
def payment_success(request):
    tran_id = request.POST.get("tran_id") or request.GET.get("tran_id")
    order = Order.objects.filter(transaction_id=tran_id).first()
    if order:
        try:
            with transaction.atomic():
                order_locked = Order.objects.select_for_update().get(pk=order.pk)
                commit_inventory_for_order(order_locked)
                order_locked.status = "paid"
                order_locked.save(update_fields=["status"])
        except InsufficientStock:
            order.status = "failed"
            order.save(update_fields=["status"])
            messages.error(request, "Payment recorded but inventory could not be fulfilled.")
            return redirect("view-cart")
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
