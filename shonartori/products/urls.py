from django.urls import path
from products.views import get_product, add_to_cart, view_cart, update_cart, remove_cart_item

urlpatterns = [
    path('cart/', view_cart, name="view-cart"),
    path('cart/update/<uuid:uid>/<str:action>/', update_cart, name="update-cart"),
    path('cart/remove/<uuid:uid>/', remove_cart_item, name="remove-cart"),
    path('add-to-cart/<uid>/', add_to_cart, name="add_to_cart"),
    path('<slug>/' , get_product , name="get_product"),
]