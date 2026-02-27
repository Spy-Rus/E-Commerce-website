from rest_framework.generics import ListAPIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from playground.models import Product, Order, OrderItem,CartItem, Payment
from .serializers import ProductSerializer, OrderSerializer, CreateOrderSerializer
from playground.services import update_order_item_status_service


class ProductListAPI(ListAPIView):
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer


class MyOrdersAPI(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related('items__product')
            .order_by('-created_at')
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_order_api(request):
    serializer = CreateOrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    items = serializer.validated_data['items']
    total = 0

    with transaction.atomic():
        order = Order.objects.create(user=request.user, total_price=0)

        for item in items:
            product = item['product']
            quantity = item['quantity']

            if quantity > product.inventory:
                raise serializers.ValidationError(
                    f"Not enough stock for {product.title}"
                )

            OrderItem.objects.create(
                order=order,
                product=product,
                seller=product.seller,
                quantity=quantity,
                price_at_purchase=product.get_current_price()
            )

            total += product.get_current_price() * quantity

        order.total_price = total
        order.save()

    return Response({
        "order_id": order.id,
        "total_price": order.total_price,
        "status": order.status
    }, status=201)


from playground.services import finalize_order_payment

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def seller_update_order_item_status_api(request, item_id):
    new_status = request.data.get('status')

    order_item = get_object_or_404(
        OrderItem,
        id=item_id,
        seller=request.user
    )

    update_order_item_status_service(
        order_item=order_item,
        seller=request.user,
        new_status=new_status
    )

    return Response({
        "item_id": order_item.id,
        "status": order_item.status
    })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_order_api(request):
    order_id = request.data.get('order_id')

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user,
        status=Order.STATUS_PENDING
    )

    finalize_order_payment(order, payment_id=f"MOCK-{order.id}")

    return Response({
        "message": "Payment successful",
        "order_id": order.id,
        "status": order.status
    }, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_payment_api(request):
    order_id = request.data.get('order_id')

    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({"error": "Order not found"}, status=404)

    if order.status == Order.STATUS_PAID:
        return Response({"error": "Order already paid"}, status=400)

    with transaction.atomic():
        # Create payment record
        Payment.objects.create(
            order=order,
            amount=order.total_price,
            status=Payment.STATUS_SUCCESS  # or 'success'
        )

        # 🔥 THIS is what your seller dashboard needs
        order.status = Order.STATUS_PAID
        order.save()

    return Response({
        "order_id": order.id,
        "order_status": order.status
    }, status=200)