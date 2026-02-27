from django.urls import path
from . import views

app_name = 'playground'

urlpatterns = [
    # Home & products
    path('', views.home, name='home'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('orders/', views.my_orders, name='my_orders'),

    # Orders
    path('checkout/', views.checkout, name='checkout'),
    path('order/<int:id>/success/', views.order_success, name='order_success'),
    path('orders/<int:id>/', views.order_detail, name='order_detail'),
    path('payment/<int:order_id>/', views.payment, name='payment'),
    path('payment/success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('products/', views.browse_products, name='browse_products'),




    # AUTH (ONE login for both buyer & seller)
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('signup/', views.signup, name='signup'),

    # Cart
    path('cart/', views.cart, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/increase/<int:product_id>/', views.increase_cart, name='increase_cart'),
    path('cart/decrease/<int:product_id>/', views.decrease_cart, name='decrease_cart'),


    # Seller
    path('seller/signup/', views.seller_signup, name='seller_signup'),
    path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('seller/products/add/', views.seller_add_product, name='seller_add_product'),
    path('seller/product/<int:id>/edit/', views.seller_edit_product, name='seller_edit_product'),
    path('seller/product/<int:id>/delete/', views.seller_delete_product, name='seller_delete_product'),
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path(
        'seller/order-item/<int:item_id>/status/',
        views.update_order_item_status,
        name='update_order_item_status'
    ),
    path('seller/analytics/', views.seller_analytics, name='seller_analytics'),

]
