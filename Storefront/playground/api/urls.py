from django.urls import path
from .api_views import (
    ProductListAPI,
    ProductDetailAPI,
    CartAPI,
    CartItemAPI,
    cart_increase,
    cart_decrease,
    seller_update_order_item_status_api,
)

urlpatterns = [
    # Public
    path('products/', ProductListAPI.as_view()),
    path('products/<int:id>/', ProductDetailAPI.as_view()),

    # Cart
    path('cart/', CartAPI.as_view()),
    path('cart/<int:id>/', CartItemAPI.as_view()),
    path('cart/<int:id>/increase/', cart_increase),
    path('cart/<int:id>/decrease/', cart_decrease),

    # Seller
    path('seller/order-item/<int:item_id>/status/', seller_update_order_item_status_api),
]
