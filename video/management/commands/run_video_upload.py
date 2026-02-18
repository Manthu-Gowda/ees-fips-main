from django.core.management.base import BaseCommand
from video.tasks import run_video_upload

class Command(BaseCommand):
    def handle(self, *args, **options):
        run_video_upload()
        self.stdout.write(self.style.SUCCESS('Video upload run successfully!'))