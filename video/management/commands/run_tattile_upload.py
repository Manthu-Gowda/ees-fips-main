from django.core.management.base import BaseCommand
from video.tasks import run_tattile_upload

class Command(BaseCommand):
    def handle(self, *args, **options):
        run_tattile_upload()
        self.stdout.write(self.style.SUCCESS('Tattile upload run successfully!'))