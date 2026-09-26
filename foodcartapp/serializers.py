from rest_framework import serializers

from .models import Order, OrderItem, Product


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
    )
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    products = OrderItemSerializer(many=True, allow_empty=False, write_only=True)
    firstname = serializers.CharField()
    lastname = serializers.CharField()
    address = serializers.CharField()

    class Meta:
        model = Order
        fields = ['firstname', 'lastname', 'phonenumber', 'address', 'products']

    def validate_firstname(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError('Имя должно быть строкой.')
        return value
