"""Enrich generated OpenAPI with the actual API contract; no request handling."""
import json
from pathlib import Path


def document_api(result, generator, request, public):
    examples = json.loads((Path(__file__).resolve().parent.parent / 'docs/api-examples.json').read_text())
    error_schema = {'type': 'object', 'additionalProperties': True, 'description': 'Помилки полів або detail; текст локалізований.'}
    meanings = {'400': 'Некоректні поля, фільтр або бізнес-правило.', '403': 'Немає сесії, прав або коректного CSRF.', '404': 'Об’єкт або сторінка не знайдені / недоступні.', '405': 'Метод не підтримується.', '406': 'Непідтримуваний Accept.', '415': 'Непідтримуваний Content-Type.', '429': 'Перевищено 600 запитів за хвилину для користувача; Retry-After.', '500': 'Неочікувана помилка сервера; формат залежить від DEBUG і сервера.'}
    custom = {'vehicles': [('customer','integer','ID клієнта, лише цифри.')], 'orders': [('status','string','Точний статус; невідоме значення дає порожній результат.'),('overdue','string','Тільки значення true вмикає прострочення.'),('vehicle','integer','ID автомобіля, лише цифри.'),('number','string','Номер ST-0001 або 1; точний збіг.')]}
    for path, operations in result['paths'].items():
        for method, operation in operations.items():
            if method not in ['get','post','put','patch','delete']: continue
            key = method.upper()+' '+path
            if path == '/api/schema/': continue
            if '/history/' in path:
                operation['parameters'] = [p for p in operation.get('parameters',[]) if p['in']!='query']
                operation['responses']['200']['content']['application/json']['schema'] = {'type':'array','items':{'$ref':'#/components/schemas/Event'}}
            if '/comment/' in path and '200' in operation['responses']:
                operation['responses']['201'] = operation['responses'].pop('200')
            resource=path.split('/')[2]
            if resource in custom and method != 'post' and (path.endswith('/'+resource+'/') or path.endswith('/{id}/')):
                for name,typ,desc in custom[resource]:
                    operation.setdefault('parameters',[]).append({'in':'query','name':name,'required':False,'description':desc,'schema':{'type':typ}})
            if method in ['post','put','patch','delete']:
                operation.setdefault('parameters',[]).append({'in':'header','name':'X-CSRFToken','required':True,'description':'Актуальний CSRF після входу; cookie sessionid і csrftoken надсилаються разом.','schema':{'type':'string'}})
            operation['description'] = ('Потрібна сесія. Механік читає лише призначені йому замовлення та пов’язані записи. ' if resource!='session' else 'Дані поточного користувача; mechanics порожній для механіка. ')+('Зміни customers/vehicles/items доступні лише адміністратору.' if resource in ['customers','vehicles','items'] else 'Детальні правила ролей і статусів: docs/14-api.md.')
            captured=examples['operations'].get(key)
            if captured:
                code=str(captured['status'])
                response=operation['responses'].setdefault(code,{'description':'Успішно'})
                response['description']='Успішна відповідь, приклад із ізольованої демонстраційної БД.'
                if captured['response'] is not None:
                    response.setdefault('content',{}).setdefault('application/json',{})['example']=captured['response']
                if captured['request'] is not None:
                    operation['requestBody']['content']['application/json']['example']=captured['request']
            for code,desc in meanings.items():
                if code=='415' and method not in ['post','put','patch']:continue
                if code=='500':operation['responses'].setdefault(code,{'description':desc});continue
                operation['responses'].setdefault(code,{'description':desc,'content':{'application/json':{'schema':error_schema}}})
    return result
