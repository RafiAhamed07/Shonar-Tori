from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from products.models import Product, Cart, CartItem


def get_product(request, slug):
    try:
        product = Product.objects.get(slug=slug)
        return render(request, "product.html", context={"product": product})
    except Exception as e:
        print(e)


@login_required(login_url="login")
def add_to_cart(request, uid):
    try:
        product = Product.objects.get(uid=uid)
        if not product.is_in_stock:
            messages.error(request, "This item is out of stock.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        quantity = request.GET.get("quantity", 1)
        try:
            quantity = max(1, int(quantity))
        except (TypeError, ValueError):
            quantity = 1

        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

        if created:
            new_qty = min(quantity, product.stock)
        else:
            new_qty = min(cart_item.quantity + quantity, product.stock)

        if new_qty < 1:
            messages.error(request, "This item is out of stock.")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        if created and new_qty < quantity:
            messages.warning(
                request,
                f"Only {product.stock} available — added {new_qty} to your bag.",
            )
        elif not created and cart_item.quantity + quantity > product.stock:
            messages.warning(
                request,
                f"Only {product.stock} available — quantity updated.",
            )

        cart_item.quantity = new_qty
        cart_item.save()

        messages.success(request, f"{product.product_name} added to cart.")
        return redirect(request.META.get("HTTP_REFERER", "/"))
    except Product.DoesNotExist:
        messages.error(request, "Product not found")
        return redirect("index")
    except Exception as e:
        print(f"Error adding to cart: {e}")
        messages.error(request, "An error occurred while adding to cart")
        return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required(login_url="login")
def view_cart(request):
    cart = Cart.objects.filter(user=request.user).first()
    total = 0
    if cart:
        total = sum(item.get_total_price() for item in cart.cart_items.all())
    return render(request, "cart.html", {"cart": cart, "total": total})


@login_required(login_url="login")
def update_cart(request, uid, action):
    cart_item = get_object_or_404(CartItem, uid=uid, cart__user=request.user)
    product = cart_item.product

    if action == "increase":
        if cart_item.quantity >= product.stock:
            messages.warning(request, f"Only {product.stock} in stock for this item.")
            return redirect("view-cart")
        cart_item.quantity += 1
        cart_item.save()
    elif action == "decrease":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    else:
        messages.warning(request, "Invalid cart action.")

    return redirect("view-cart")


@login_required(login_url="login")
def remove_cart_item(request, uid):
    cart_item = get_object_or_404(CartItem, uid=uid, cart__user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect("view-cart")
