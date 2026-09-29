from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import serializers
from .models import Customer, Vehicle, Order, OrderItem, Event
from .serializers import CustomerSerializer, VehicleSerializer, OrderSerializer, ItemSerializer, EventSerializer, StatusSerializer, CommentSerializer
from .services import is_manager, change_status

class ManagerWrite(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.method in permissions.SAFE_METHODS or is_manager(request.user))

class ProtectedDeleteMixin:
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({'detail': 'Запис має пов’язані дані. Спочатку опрацюй залежні записи.'})

class CustomerViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Customer.objects.none()
    serializer_class = CustomerSerializer
    permission_classes = [ManagerWrite]
    search_fields = ['name', 'phone', 'email']
    def get_queryset(self):
        qs = Customer.objects.all().order_by('name')
        if not is_manager(self.request.user):
            qs = qs.filter(vehicles__orders__mechanic=self.request.user).distinct()
        return qs

class VehicleViewSet(ProtectedDeleteMixin, viewsets.ModelViewSet):
    queryset = Vehicle.objects.none()
    serializer_class = VehicleSerializer
    permission_classes = [ManagerWrite]
    search_fields = ['vin', 'plate', 'customer__name']
    def get_queryset(self):
        qs = Vehicle.objects.select_related('customer').order_by('-id')
        if not is_manager(self.request.user):
            qs = qs.filter(orders__mechanic=self.request.user).distinct()
        customer = self.request.query_params.get('customer')
        if customer:
            if not customer.isdigit():
                raise ValidationError({'customer': 'Потрібне ціле число.'})
            qs = qs.filter(customer_id=customer)
        return qs

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.none()
    serializer_class = OrderSerializer
    search_fields = ['vehicle__vin', 'vehicle__plate', 'vehicle__customer__name', 'complaint']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    def get_queryset(self):
        qs = Order.objects.select_related('vehicle__customer', 'mechanic').prefetch_related('items')
        if not is_manager(self.request.user):
            qs = qs.filter(mechanic=self.request.user)
        s = self.request.query_params.get('status')
        if s:
            qs = qs.filter(status=s)
        if self.request.query_params.get('overdue') == 'true':
            qs = qs.filter(due_date__lt=timezone.localdate()).exclude(status__in=['ready', 'delivered'])
        v = self.request.query_params.get('vehicle')
        if v:
            if not v.isdigit():
                raise ValidationError({'vehicle': 'Потрібне ціле число.'})
            qs = qs.filter(vehicle_id=v)
        number = self.request.query_params.get('number', '').upper().replace('ST-', '')
        if number:
            if not number.isdigit():
                raise ValidationError({'number': 'Потрібен номер замовлення.'})
            qs = qs.filter(pk=int(number))
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        if not is_manager(self.request.user):
            raise PermissionDenied('Створення доступне адміністратору.')
        order = serializer.save()
        Event.objects.create(order=order, author=self.request.user, kind='created', text='Замовлення прийнято')

    def perform_update(self, serializer):
        obj = self.get_object()
        if obj.status == 'delivered':
            raise ValidationError({'detail': 'Видане замовлення закрите для редагування.'})
        if not is_manager(self.request.user) and set(self.request.data) - {'diagnosis', 'fault_codes'}:
            raise PermissionDenied('Механік редагує тільки діагностику та коди помилок.')
        serializer.save()

    @extend_schema(request=StatusSerializer, responses=OrderSerializer)
    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        payload = StatusSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        obj = change_status(self.get_object(), payload.validated_data['status'], request.user)
        return Response(self.get_serializer(obj).data)

    @extend_schema(responses=EventSerializer(many=True))
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        obj = self.get_object()
        return Response(EventSerializer(obj.events.select_related('author'), many=True).data)

    @extend_schema(request=CommentSerializer, responses=EventSerializer)
    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):
        obj = self.get_object()
        payload = CommentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        event = Event.objects.create(order=obj, author=request.user, kind='comment', **payload.validated_data)
        return Response(EventSerializer(event).data, status=201)

class ItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.none()
    serializer_class = ItemSerializer
    permission_classes = [ManagerWrite]
    def get_queryset(self):
        qs = OrderItem.objects.select_related('order')
        if not is_manager(self.request.user):
            qs = qs.filter(order__mechanic=self.request.user)
        return qs.order_by('id')
    def check_order(self, order):
        if order.status == 'delivered':
            raise ValidationError({'order': 'Видане замовлення закрите для редагування.'})
    def perform_create(self, serializer):
        self.check_order(serializer.validated_data['order'])
        serializer.save()
    def perform_update(self, serializer):
        self.check_order(serializer.instance.order)
        self.check_order(serializer.validated_data.get('order', serializer.instance.order))
        serializer.save()
    def perform_destroy(self, instance):
        self.check_order(instance.order)
        instance.delete()

@login_required
def app(request):
    return render(request, 'app.html', {'manager': is_manager(request.user)})

@extend_schema(responses=inline_serializer(name='SessionInfo', fields={'username': serializers.CharField(), 'manager': serializers.BooleanField(), 'mechanics': serializers.ListField(child=serializers.DictField()), 'statuses': serializers.ListField(child=serializers.DictField())}))
@api_view(['GET'])
def session_info(request):
    manager = is_manager(request.user)
    mechanics = list(get_user_model().objects.filter(groups__name='Механік', is_active=True).values('id', 'username')) if manager else []
    return Response({'username': request.user.username, 'manager': manager, 'mechanics': mechanics, 'statuses': [{'value': s.value, 'label': s.label} for s in Order.Status]})
