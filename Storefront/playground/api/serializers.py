from rest_framework import serializers
from playground.models import Product, Order, OrderItem, CartItem


class ProductSerializer(serializers.ModelSerializer):
    current_price = serializers.SerializerMethodField()
    seller = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = [
            'id', 'title', 'slug', 'description',
            'base_price', 'current_price', 'inventory',
            'available', 'image', 'seller', 'created',
        ]

    def get_current_price(self, obj):
        return obj.get_current_price()


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.get_total_price()
