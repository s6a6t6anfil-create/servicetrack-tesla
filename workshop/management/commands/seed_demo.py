import os
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone
from workshop.models import Customer, Vehicle, Order, OrderItem, Event

class Command(BaseCommand):
    help = 'Create fictional demo data on an empty database; password from DEMO_PASSWORD.'
    @transaction.atomic
    def handle(self, *args, **options):
        password = os.environ.get('DEMO_PASSWORD')
        if not password or len(password) < 12:
            raise CommandError('Set DEMO_PASSWORD (at least 12 characters).')
        if Customer.objects.exists() or get_user_model().objects.exists():
            raise CommandError('Demo seed requires an empty database; existing data were preserved.')
        manager_group, _ = Group.objects.get_or_create(name='Адміністратор')
        mechanic_group, _ = Group.objects.get_or_create(name='Механік')
        manager = get_user_model().objects.create_superuser('admin', 'admin@example.invalid', password)
        manager.groups.add(manager_group)
        mechanic = get_user_model().objects.create_user('mechanic', password=password)
        mechanic.groups.add(mechanic_group)
        for i, (name, model, complaint, state) in enumerate([
            ('Демо Олексій', 'Model Y', 'Перевірка шуму передньої підвіски', 'diagnosis'),
            ('Демо Марія', 'Model 3', 'Заміна салонного фільтра', 'received'),
            ('Демо Андрій', 'Model S', 'Перевірка низьковольтної системи', 'parts'),
            ('Демо Олена', 'Model X', 'Плановий огляд гальм', 'ready'),
        ], 1):
            c = Customer.objects.create(name=name, phone=f'+38000000000{i}', email=f'demo{i}@example.invalid', notes='Вигадані демонстраційні дані')
            v = Vehicle.objects.create(customer=c, model=model, year=2021+i, vin=f'DEMX00000000000{i:02}', plate=f'ДЕМО {i:04}', mileage=15000*i)
            o = Order.objects.create(vehicle=v, mechanic=mechanic, complaint=complaint, status=state, due_date=timezone.localdate()+timedelta(days=i-3), diagnosis='Демонстраційний запис; не технічна рекомендація.')
            OrderItem.objects.create(order=o, kind='labor', name='Огляд автомобіля', quantity=Decimal('1'), unit_price=Decimal('800'))
            Event.objects.create(order=o, author=manager, kind='created', text=f'Демонстраційне замовлення: {o.get_status_display()}')
        self.stdout.write(self.style.SUCCESS('Created admin, mechanic and 4 fictional orders.'))
