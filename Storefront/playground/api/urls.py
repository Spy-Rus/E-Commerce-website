from django.urls import path
from .api_views import (
    ProductListAPI,
    MyOrdersAPI,
    create_order_api,
    pay_order_api,
)

urlpatterns = [
    path('products/', ProductListAPI.as_view()),   # GET
    path('orders/', create_order_api),              # POST ✅
    path('my-orders/', MyOrdersAPI.as_view()),      # GET
    path('pay/', pay_order_api),
]