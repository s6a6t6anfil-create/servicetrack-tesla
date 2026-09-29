from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Customer, Vehicle, Order, OrderItem, Event
from .services import TRANSITIONS

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'email', 'notes', 'created_at']
        read_only_fields = ['created_at']

class VehicleSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    def to_internal_value(self, data):
        data = data.copy()
        if isinstance(data.get("vin"), str):
            data["vin"] = data["vin"].strip().upper()
        return super().to_internal_value(data)
    class Meta:
        model = Vehicle
        fields = ['id', 'customer', 'customer_name', 'model', 'year', 'vin', 'plate', 'mileage']

class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'kind', 'name', 'quantity', 'unit_price']

class EventSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    class Meta:
        model = Event
        fields = ['id', 'kind', 'text', 'author_name', 'created_at']

class OrderSerializer(serializers.ModelSerializer):
    number = serializers.SerializerMethodField()
    vehicle_label = serializers.CharField(source='vehicle.__str__', read_only=True)
    vin = serializers.CharField(source='vehicle.vin', read_only=True)
    customer_name = serializers.CharField(source='vehicle.customer.name', read_only=True)
    mechanic_name = serializers.CharField(source='mechanic.username', read_only=True, default='Не призначено')
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    items = ItemSerializer(many=True, read_only=True)
    transitions = serializers.SerializerMethodField()
    def get_number(self, obj) -> str:
        return str(obj)
    def get_transitions(self, obj) -> list:
        return [{'value': s, 'label': Order.Status(s).label} for s in TRANSITIONS[obj.status]]
    def validate_mechanic(self, value):
        if value and (not value.is_active or not value.groups.filter(name='Механік').exists()):
            raise serializers.ValidationError('Обери активного користувача з роллю механіка.')
        return value
    class Meta:
        model = Order
        fields = ['id', 'number', 'vehicle', 'vehicle_label', 'vin', 'customer_name', 'mechanic', 'mechanic_name', 'complaint', 'diagnosis', 'fault_codes', 'due_date', 'status', 'status_label', 'created_at', 'updated_at', 'total', 'items', 'transitions']
        read_only_fields = ['status', 'created_at', 'updated_at']

class StatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)

class CommentSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000)
