from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework import status

from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError, PermissionDenied

from playground.models import Product, Order, OrderItem, CartItem
from playground.services import update_order_item_status_service
from playground.api.permissions import IsSeller
from .serializers import (
    ProductSerializer,
    CartItemSerializer,
)


# ─── Products (public) ───────────────────────────────────────────────────────

class ProductListAPI(ListAPIView):
    """GET /api/products/ — Public product listing"""
    queryset = Product.objects.filter(available=True).order_by('-created')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


class ProductDetailAPI(APIView):
    """GET /api/products/<id>/ — Single product detail"""
    permission_classes = [AllowAny]

    def get(self, request, id):
        product = get_object_or_404(Product, id=id, available=True)
        return Response(ProductSerializer(product).data)


# ─── Cart ────────────────────────────────────────────────────────────────────

class CartAPI(APIView):
    """
    GET  /api/cart/ — View cart with total
    POST /api/cart/ — Add item { product_id, quantity }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = CartItem.objects.filter(user=request.user).select_related('product')
        serializer = CartItemSerializer(items, many=True)
        total = sum(item.get_total_price() for item in items)
        return Response({
            'items': serializer.data,
            'total': total,
        })

    def post(self, request):
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id, available=True)

        if quantity < 1:
            return Response(
                {'detail': 'Quantity must be at least 1'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if quantity > product.inventory:
            return Response(
                {'detail': f'Only {product.inventory} items in stock'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.inventory:
                cart_item.quantity = product.inventory
            cart_item.save()

        return Response({
            **CartItemSerializer(cart_item).data,
            'created': created,
        }, status=status.HTTP_200_OK)


class CartItemAPI(APIView):
    """DELETE /api/cart/<id>/ — Remove item from cart"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        CartItem.objects.filter(user=request.user, product_id=id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cart_increase(request, id):
    """POST /api/cart/<id>/increase/ — Increase quantity by 1"""
    item = get_object_or_404(CartItem, user=request.user, product_id=id)
    if item.quantity < item.product.inventory:
        item.quantity += 1
        item.save()
    return Response(CartItemSerializer(item).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cart_decrease(request, id):
    """POST /api/cart/<id>/decrease/ — Decrease quantity by 1, remove if 0"""
    item = get_object_or_404(CartItem, user=request.user, product_id=id)
    item.quantity -= 1
    if item.quantity <= 0:
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    item.save()
    return Response(CartItemSerializer(item).data)


# ─── Seller ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsSeller])
def seller_update_order_item_status_api(request, item_id):
    """
    POST /api/seller/order-item/<id>/status/
    Body: { status: 'shipped' | 'delivered' }
    """
    new_status = request.data.get('status')
    order_item = get_object_or_404(OrderItem, id=item_id, seller=request.user)

    try:
        update_order_item_status_service(
            order_item=order_item,
            seller=request.user,
            new_status=new_status
        )
    except PermissionDenied as e:
        return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
    except ValidationError as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'item_id': order_item.id,
        'status': order_item.status,
    })
