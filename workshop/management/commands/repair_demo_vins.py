from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from workshop.models import Vehicle

class Command(BaseCommand):
    help = 'Dry-run by default; --apply repairs only the four marked legacy demo VINs.'
    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
    @transaction.atomic
    def handle(self, *args, **options):
        updates=[]
        for i in range(1,5):
            old=f'DEMO00000000000{i:02}'
            new=f'DEMX00000000000{i:02}'
            vehicle=Vehicle.objects.filter(vin=old,customer__notes='Вигадані демонстраційні дані').first()
            if vehicle:
                if Vehicle.objects.filter(vin=new).exists():
                    raise CommandError('Target VIN exists; no data changed.')
                updates.append((vehicle,new))
        for vehicle,new in updates:
            if options['apply']:
                vehicle.vin=new
                vehicle.save(update_fields=['vin'])
        self.stdout.write(f'{"Repaired" if options["apply"] else "Would repair"}: {len(updates)} marked demo VINs.')
