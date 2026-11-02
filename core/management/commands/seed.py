from django.core.management.base import BaseCommand

from core.seed import seed_all


class Command(BaseCommand):
    help = "Create or refresh the KnowGSC demo content."

    def handle(self, *args, **options):
        counts = seed_all()
        summary = ", ".join(f"{key}={value}" for key, value in counts.items())
        self.stdout.write(self.style.SUCCESS(f"KnowGSC content seeded: {summary}"))
