# Integration contract exercise. Creates and destroys an isolated Django test database.
import os,sys,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root));os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
import django;django.setup()
from django.test.utils import setup_test_environment,setup_databases,teardown_databases
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
setup_test_environment();db=setup_databases(verbosity=0,interactive=False)
try:
 u=get_user_model().objects.create_superuser('api_demo',password='OnlyInIsolatedTests_934!')
 c=APIClient();c.force_login(u);out={}
 def call(method,url,body=None,key=None):
  r=getattr(c,method)(url,body,format='json') if body is not None else getattr(c,method)(url)
  try: response=r.json()
  except (ValueError, TypeError): response=None
  expected={'post':201,'delete':204}.get(method,200)
  if '/transition/' in url: expected=200
  assert r.status_code==expected,(method,url,r.status_code,expected,response)
  if method=='get' and url in ['/api/customers/','/api/vehicles/','/api/orders/','/api/items/']:
   assert set(['count','next','previous','results'])<=response.keys() and isinstance(response['results'],list)
  if '/history/' in url: assert isinstance(response,list)
  out[key or method.upper()+' '+url]={'request':body,'status':r.status_code,'response':response}
  return response
 customer={'name':'Демо клієнт','phone':'+380000000001','email':'demo@example.invalid','notes':''}
 vehicle={'customer':1,'model':'Model Y','year':2023,'vin':'TEST0000000000001','plate':'ДЕМО','mileage':12000}
 order={'vehicle':1,'complaint':'Огляд підвіски','due_date':'2026-10-05','mechanic':None}
 item={'order':1,'kind':'labor','name':'Огляд','quantity':'1.50','unit_price':'1000.00'}
 for name,data in [('customers',customer),('vehicles',vehicle),('orders',order),('items',item)]:call('post',f'/api/{name}/',data)
 for name,data in [('customers',customer),('vehicles',vehicle),('orders',order),('items',item)]:
  call('get',f'/api/{name}/')
  call('get',f'/api/{name}/1/',key=f'GET /api/{name}/{{id}}/')
  if name!='orders':call('put',f'/api/{name}/1/',data,key=f'PUT /api/{name}/{{id}}/')
  patch={'customers':{'notes':'Уточнення'},'vehicles':{'mileage':12100},'orders':{'diagnosis':'Огляд завершено'},'items':{'quantity':'2.00'}}[name]
  call('patch',f'/api/{name}/1/',patch,key=f'PATCH /api/{name}/{{id}}/')
 call('post','/api/orders/1/transition/',{'status':'diagnosis'},'POST /api/orders/{id}/transition/')
 call('post','/api/orders/1/comment/',{'text':'Очікується погодження'},'POST /api/orders/{id}/comment/')
 call('get','/api/orders/1/history/',key='GET /api/orders/{id}/history/')
 call('get','/api/session/')
 call('delete','/api/items/1/',key='DELETE /api/items/{id}/')
 # Separate unreferenced objects for successful deletes, leave business history intact.
 v=call('post','/api/vehicles/',{**vehicle,'vin':'TEST0000000000002'},'fixture vehicle')
 call('delete',f"/api/vehicles/{v['id']}/",key='DELETE /api/vehicles/{id}/')
 cu=call('post','/api/customers/',customer,'fixture customer')
 call('delete',f"/api/customers/{cu['id']}/",key='DELETE /api/customers/{id}/')
 for key in ['fixture vehicle','fixture customer']:out.pop(key)
 errors={}
 for label,method,url,data in [('invalid_customer','post','/api/customers/',{}),('invalid_vin','post','/api/vehicles/',{**vehicle,'vin':'INVALID'}),('bad_transition','post','/api/orders/1/transition/',{'status':'delivered'}),('empty_comment','post','/api/orders/1/comment/',{'text':''}),('protected_delete','delete','/api/customers/1/',None),('not_found','get','/api/orders/999/',None),('method_not_allowed','delete','/api/orders/1/',None),('invalid_item','post','/api/items/',{**item,'quantity':'0'}),('invalid_order','post','/api/orders/',{})]:
  r=getattr(c,method)(url,data,format='json') if data is not None else getattr(c,method)(url)
  assert r.status_code=={'protected_delete':400,'not_found':404,'method_not_allowed':405}.get(label,400),(label,r.status_code)
  errors[label]={'status':r.status_code,'response':r.json()}
 c.logout();r=c.get('/api/session/');assert r.status_code==403;errors['no_session']={'status':r.status_code,'response':r.json()}
 path=root/'docs/verification/pz19-api.json';path.write_text(json.dumps({'operations':out,'errors':errors},ensure_ascii=False,indent=2))
 print('Captured',len(out),'successful operations and',len(errors),'errors in isolated test database')
finally:teardown_databases(db,verbosity=0)
