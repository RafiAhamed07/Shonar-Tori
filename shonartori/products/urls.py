from django.urls import path
from products.views import get_product, add_to_cart

urlpatterns = [
    path('add-to-cart/<uid>/', add_to_cart, name="add_to_cart"),
    path('<slug>/' , get_product , name="get_product"),
]