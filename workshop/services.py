from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Order, Event

TRANSITIONS = {
    'received': ['diagnosis'],
    'diagnosis': ['approval', 'parts', 'repair'],
    'approval': ['diagnosis', 'parts', 'repair'],
    'parts': ['diagnosis', 'repair'],
    'repair': ['diagnosis', 'parts', 'ready'],
    'ready': ['repair', 'delivered'],
    'delivered': [],
}

def is_manager(user):
    return user.is_superuser or user.groups.filter(name='Адміністратор').exists()

@transaction.atomic
def change_status(order, status, user):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if status not in TRANSITIONS[order.status]:
        raise ValidationError({'status': 'Недозволений перехід статусу.'})
    if status == 'delivered' and not is_manager(user):
        raise ValidationError({'status': 'Видачу автомобіля підтверджує адміністратор.'})
    previous = order.get_status_display()
    order.status = status
    order.save(update_fields=['status', 'updated_at'])
    Event.objects.create(order=order, author=user, kind='status', text=f'{previous} → {order.get_status_display()}')
    return order
