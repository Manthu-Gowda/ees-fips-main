from django.core.management.base import BaseCommand
from video.tasks import run_daily_report

class Command(BaseCommand):
    def handle(self, *args, **options):
        run_daily_report()
        self.stdout.write(self.style.SUCCESS('Daily report run successfully!'))