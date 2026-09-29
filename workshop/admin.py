from django.contrib import admin
from .models import Customer, Vehicle, Order, OrderItem, Event
# Business writes use the API so that permissions and status history remain consistent.
class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
for model in [Customer, Vehicle, Order, OrderItem, Event]:
    admin.site.register(model, ReadOnlyAdmin)
admin.site.site_header = 'ServiceTrack — облікові записи'
