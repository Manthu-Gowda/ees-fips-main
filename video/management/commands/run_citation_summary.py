from django.core.management.base import BaseCommand
from video.tasks import run_citation_summary

class Command(BaseCommand):
    def handle(self, *args, **options):
        run_citation_summary()
        self.stdout.write(self.style.SUCCESS('Citation summary run successfully!'))