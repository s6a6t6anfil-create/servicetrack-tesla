"""Prepare isolated fictional data for a presentation; never alter the main DB."""
import argparse
import os
from pathlib import Path
import secrets
import socket
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prepare-only', action='store_true')
parser.add_argument('--session', type=Path, help='Resume a previously prepared directory inside .demo')
parser.add_argument('--port', type=int, default=8954)
args = parser.parse_args()
if not 1024 <= args.port <= 65535:
    parser.error('Port must be 1024..65535.')
if not args.prepare_only:
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', args.port))
        except OSError:
            parser.error('Port is busy. Pick another --port; do not stop another project.')
base = ROOT / '.demo'
base.mkdir(mode=0o700, exist_ok=True)
if args.session:
    session = args.session.resolve()
    if session.parent != base.resolve() or not (session / 'demo.sqlite3').is_file():
        parser.error('Session must be a prepared directory directly inside .demo.')
else:
    session = Path(tempfile.mkdtemp(prefix='rehearsal-', dir=base))
import config.settings as defaults
settings = types.ModuleType('presentation_settings')
for name in dir(defaults):
    if name.isupper():
        setattr(settings, name, getattr(defaults, name))
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': session / 'demo.sqlite3'}}
settings.ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
sys.modules['presentation_settings'] = settings
os.environ['DJANGO_SETTINGS_MODULE'] = 'presentation_settings'
import django
django.setup()
from django.core.management import call_command
if not args.session:
    call_command('migrate', verbosity=0)
    password = secrets.token_urlsafe(18)
    os.environ['DEMO_PASSWORD'] = password
    call_command('seed_demo', verbosity=0)
    credentials = session / 'Вхід.txt'
    fd = os.open(credentials, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write('Лише локальна демонстрація. Не публікувати.\nАдміністратор: admin\nМеханік: mechanic\nПароль обох: ' + password + '\n')
    os.environ.pop('DEMO_PASSWORD', None)
call_command('check')
print('Session:', session, flush=True)
print('Credentials:', session / 'Вхід.txt', flush=True)
if not args.prepare_only:
    print(f'Demo: http://127.0.0.1:{args.port}/ (Ctrl+C stops this demo only)', flush=True)
    call_command('runserver', f'127.0.0.1:{args.port}', use_reloader=False)
