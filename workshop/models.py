from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models

vin_validator = RegexValidator(r'^[A-HJ-NPR-Z0-9]{17}$', 'VIN має містити 17 латинських літер або цифр, без I, O, Q.')

class Customer(models.Model):
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True, max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Vehicle(models.Model):
    MODELS = [(x, x) for x in ['Model S', 'Model 3', 'Model X', 'Model Y', 'Cybertruck', 'Roadster']]
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='vehicles')
    model = models.CharField(max_length=20, choices=MODELS)
    year = models.PositiveIntegerField(validators=[MinValueValidator(2008), MaxValueValidator(2100)])
    vin = models.CharField(max_length=17, unique=True, validators=[vin_validator])
    plate = models.CharField(max_length=20, blank=True)
    mileage = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(3000000)])

    def __str__(self):
        return f'{self.model} · {self.plate or self.vin}'

class Order(models.Model):
    class Status(models.TextChoices):
        RECEIVED = 'received', 'Прийнято'
        DIAGNOSIS = 'diagnosis', 'Діагностика'
        APPROVAL = 'approval', 'Очікує погодження'
        PARTS = 'parts', 'Очікує запчастин'
        REPAIR = 'repair', 'У ремонті'
        READY = 'ready', 'Готово'
        DELIVERED = 'delivered', 'Видано'

    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT, related_name='orders')
    mechanic = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='orders')
    complaint = models.TextField(max_length=4000)
    diagnosis = models.TextField(blank=True, max_length=8000)
    fault_codes = models.CharField(blank=True, max_length=1000)
    due_date = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']
        indexes = [models.Index(fields=['status', 'due_date'])]

    @property
    def total(self):
        return sum((i.quantity * i.unit_price for i in self.items.all()), Decimal('0')).quantize(Decimal('0.01'))

    def __str__(self):
        return f'ST-{self.pk:04d}'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    kind = models.CharField(max_length=8, choices=[('labor', 'Робота'), ('part', 'Запчастина')])
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])

class Event(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='events')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=16, choices=[('created', 'Створення'), ('status', 'Статус'), ('comment', 'Коментар')])
    text = models.TextField(max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
