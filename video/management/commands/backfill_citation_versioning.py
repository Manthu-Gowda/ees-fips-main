from django.core.management.base import BaseCommand
from django.db import transaction

from video.models import Citation, CitationVersioning
from video.citations.versioning_utils import build_versions_for_citation


class Command(BaseCommand):
    help = "Backfill CitationVersioning table using full version reconstruction."

    def add_arguments(self, parser):
        parser.add_argument(
            "--station",
            type=int,
            default=None,
            help="Backfill only a specific station (e.g. 38 or 44).",
        )

        parser.add_argument(
            "--batch",
            type=int,
            default=2000,
            help="Batch size for efficient processing.",
        )

    def handle(self, *args, **options):

        station_id = options["station"]
        batch_size = options["batch"]

        qs = Citation.objects.all().order_by("id")

        if station_id:
            qs = qs.filter(station_id=station_id)

        total = qs.count()
        self.stdout.write(self.style.WARNING(f"Total citations to process: {total}"))

        index = 0

        while True:

            citations = list(qs[index:index + batch_size])
            if not citations:
                break

            with transaction.atomic():

                for citation in citations:

                    # Delete old version record (you said you will clear table first)
                    CitationVersioning.objects.filter(citation=citation).delete()

                    # Build all versions for this citation
                    versions = build_versions_for_citation(citation)

                    if not versions:
                        continue

                    # Latest version is first entry
                    latest = versions[0]

                    CitationVersioning.objects.create(
                        citation=citation,
                        current_version_number=latest["version_number"],
                        versions=versions,  # FULL HISTORY (latest -> oldest)
                        latest_status=latest["status"],
                        latest_approved_date=latest["approvedDate"],
                        isAllowEdit=(latest["status"] not in ["PIH", "CE", "X"]),
                    )

            index += batch_size
            self.stdout.write(
                self.style.SUCCESS(f"Processed {min(index, total)} / {total}")
            )

        self.stdout.write(self.style.SUCCESS("Backfill completed successfully."))