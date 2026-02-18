from django.core.management.base import BaseCommand
from video.tasks import run_tattile_reject

class Command(BaseCommand):
    def handle(self, *args, **options):
        run_tattile_reject()
        self.stdout.write(self.style.SUCCESS('Tattile reject run successfully!'))