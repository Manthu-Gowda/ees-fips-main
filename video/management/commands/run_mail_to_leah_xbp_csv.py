from django.core.management.base import BaseCommand
from video.tasks import run_mail_to_leah_xbp_csv

class Command(BaseCommand):
    def handle(self, *args, **options):
        run_mail_to_leah_xbp_csv()
        self.stdout.write(self.style.SUCCESS('Mail to Leah and XBP CSV run successfully!'))