from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from products.models import Product




def get_product(request , slug):
    try:
        product = Product.objects.get(slug =slug)
        return render(request  , 'product.html' , context = {'product' : product})

    except Exception as e:
        print(e)


@login_required(login_url='login_page')
def add_to_cart(request, uid):
    """Add a product to the user's cart"""
    try:
        product = Product.objects.get(uid=uid)
        messages.success(request, f'{product.product_name} added to cart')
        return redirect(request.META.get('HTTP_REFERER', 'get_product'))
    except Product.DoesNotExist:
        messages.error(request, 'Product not found')
        return redirect('get_product')
    except Exception as e:
        print(f"Error adding to cart: {e}")
        messages.error(request, 'An error occurred while adding to cart')
        return redirect(request.META.get('HTTP_REFERER', 'get_product'))