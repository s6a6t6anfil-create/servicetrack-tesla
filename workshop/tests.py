from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Customer, Vehicle, Order, OrderItem, Event

class WorkshopTests(TestCase):
    def setUp(self):
        self.admin=get_user_model().objects.create_user('admin',password='test',is_superuser=True)
        self.mechanic=get_user_model().objects.create_user('mechanic',password='test')
        self.other=get_user_model().objects.create_user('other',password='test')
        g=Group.objects.create(name='Механік');self.mechanic.groups.add(g);self.other.groups.add(g)
        self.customer=Customer.objects.create(name='Тест',phone='000')
        self.vehicle=Vehicle.objects.create(customer=self.customer,model='Model Y',year=2023,vin='DEMO0000000000001')
        self.order=Order.objects.create(vehicle=self.vehicle,mechanic=self.mechanic,complaint='Огляд',due_date=timezone.localdate()-timedelta(days=1))
        self.client=APIClient();self.client.force_authenticate(self.admin)
    def test_anonymous_forbidden(self):
        self.client.force_authenticate(None)
        for url in ['customers','vehicles','orders','items','session']:
            self.assertEqual(self.client.get(f'/api/{url}/').status_code,403)
    def test_customer_create_validation(self):
        self.assertEqual(self.client.post('/api/customers/',{'name':'Новий','phone':'000','email':'not-email'}).status_code,400)
        self.assertEqual(self.client.post('/api/customers/',{'name':'Новий','phone':'000'}).status_code,201)
    def test_vehicle_invalid_and_duplicate_vin(self):
        base={'customer':self.customer.pk,'model':'Model Y','year':2023,'mileage':0}
        for vin in ['short','I'*17,self.vehicle.vin]:
            self.assertEqual(self.client.post('/api/vehicles/',{**base,'vin':vin}).status_code,400)
    def test_vehicle_normalizes_lowercase_vin(self):
        result=self.client.post('/api/vehicles/',{'customer':self.customer.pk,'model':'Model Y','year':2023,'vin':'demo0000000000002'})
        self.assertEqual(result.status_code,201)
        self.assertEqual(result.data['vin'],'DEMO0000000000002')
    def test_mechanic_scope(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/orders/').data['count'],0)
        self.assertEqual(self.client.get(f'/api/orders/{self.order.pk}/').status_code,404)
        self.assertEqual(self.client.get('/api/customers/').data['count'],0)
        self.assertEqual(self.client.get('/api/vehicles/').data['count'],0)
    def test_mechanic_write_permissions(self):
        self.client.force_authenticate(self.mechanic)
        self.assertEqual(self.client.post('/api/customers/',{'name':'x','phone':'000'}).status_code,403)
        self.assertEqual(self.client.patch(f'/api/orders/{self.order.pk}/',{'due_date':'2026-10-01'}).status_code,403)
        self.assertEqual(self.client.patch(f'/api/orders/{self.order.pk}/',{'diagnosis':'Перевірено'}).status_code,200)
    def test_status_and_audit(self):
        endpoint=f'/api/orders/{self.order.pk}/transition/'
        self.assertEqual(self.client.post(endpoint,{'status':'delivered'}).status_code,400)
        self.assertEqual(self.client.post(endpoint,{'status':'diagnosis'}).status_code,200)
        self.assertEqual(Event.objects.filter(order=self.order,kind='status').count(),1)
        self.assertEqual(self.client.post(endpoint,{'status':'diagnosis'}).status_code,400)
        self.assertEqual(Event.objects.filter(order=self.order).count(),1)
    def test_mechanic_cannot_deliver(self):
        self.order.status='ready';self.order.save();self.client.force_authenticate(self.mechanic)
        self.assertEqual(self.client.post(f'/api/orders/{self.order.pk}/transition/',{'status':'delivered'}).status_code,400)
    def test_total_decimal_and_negative_price(self):
        for qty,price in [('3','0.10'),('1.50','100.00')]:
            self.assertEqual(self.client.post('/api/items/',{'order':self.order.pk,'kind':'labor','name':'Робота','quantity':qty,'unit_price':price}).status_code,201)
        self.assertEqual(self.order.total,Decimal('150.30'))
        for qty,price in [('0','1'),('1','-1')]:
            self.assertEqual(self.client.post('/api/items/',{'order':self.order.pk,'kind':'labor','name':'x','quantity':qty,'unit_price':price}).status_code,400)
    def test_protected_delete(self):
        self.assertEqual(self.client.delete(f'/api/customers/{self.customer.pk}/').status_code,400)
        self.assertEqual(self.client.delete(f'/api/vehicles/{self.vehicle.pk}/').status_code,400)
    def test_closed_order_immutable(self):
        self.order.status='delivered';self.order.save()
        self.assertEqual(self.client.patch(f'/api/orders/{self.order.pk}/',{'complaint':'Changed'}).status_code,400)
        self.assertEqual(self.client.post('/api/items/',{'order':self.order.pk,'kind':'part','name':'x','quantity':'1','unit_price':'1'}).status_code,400)
    def test_filter_and_invalid_query(self):
        self.assertEqual(self.client.get('/api/orders/?overdue=true').data['count'],1)
        self.assertEqual(self.client.get(f'/api/orders/?number=ST-{self.order.pk:04}').data['count'],1)
        self.assertEqual(self.client.get('/api/orders/?vehicle=abc').status_code,400)
    def test_comment_and_history(self):
        self.assertEqual(self.client.post(f'/api/orders/{self.order.pk}/comment/',{'text':''}).status_code,400)
        self.assertEqual(self.client.post(f'/api/orders/{self.order.pk}/comment/',{'text':'Тест'}).status_code,201)
        self.assertEqual(self.client.get(f'/api/orders/{self.order.pk}/history/').data[0]['text'],'Тест')
    def test_order_creation_audit_and_mechanic_validation(self):
        data={'vehicle':self.vehicle.pk,'complaint':'Новий','due_date':'2026-10-01','mechanic':self.admin.pk}
        self.assertEqual(self.client.post('/api/orders/',data).status_code,400)
        data['mechanic']=self.mechanic.pk
        r=self.client.post('/api/orders/',data)
        self.assertEqual(r.status_code,201)
        self.assertTrue(Event.objects.filter(order_id=r.data['id'],kind='created').exists())
    def test_csrf_required_on_session_write(self):
        c=APIClient(enforce_csrf_checks=True);c.force_login(self.admin)
        self.assertEqual(c.post('/api/customers/',{'name':'x','phone':'0'}).status_code,403)
    def test_ui_pages(self):
        self.assertEqual(self.client.get('/accounts/login/').status_code,200)
        c=APIClient();self.assertEqual(c.get('/').status_code,302)
