from django.core.management.base import BaseCommand
from video.tasks import run_midnight_cleanup

class Command(BaseCommand):
    def handle(self, *args, **options):
        run_midnight_cleanup()
        self.stdout.write(self.style.SUCCESS('Midnight cleanup completed successfully!'))