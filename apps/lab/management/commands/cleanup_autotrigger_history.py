from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.lab.models import AutoTriggerHistory


class Command(BaseCommand):
    help = (
        "Safely archives Auto Trigger history/run data without deleting "
        "Auto Trigger generated patients or clinical records."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force archive eligible completed/failed/partially completed runs."
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        now = timezone.localtime(timezone.now())

        self.stdout.write(
            self.style.NOTICE(
                f"Starting Auto Trigger History Cleanup: "
                f"{now.strftime('%Y-%m-%d %I:%M:%S %p')}"
            )
        )

        # ---------------------------------------------------------
        # IMPORTANT:
        # Only archive finished automation runs.
        # NEVER archive an actively running automation.
        # ---------------------------------------------------------

        eligible_statuses = [
            "Completed",
            "Partially Completed",
            "Failed",
        ]

        history_qs = AutoTriggerHistory.objects.filter(
            status__in=eligible_statuses
        ).exclude(
            status="Archived"
        )

        # If the cleanup is not forced, archive only runs from
        # previous laboratory days / historical runs.
        #
        # We intentionally do NOT delete any records.
        if not force:
            today = now.date()

            history_qs = history_qs.filter(
                from_date__lt=today
            )

        archived_count = history_qs.update(
            status="Archived"
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\n"
                "==================================================\n"
                "AUTO TRIGGER CLEANUP COMPLETED\n"
                "==================================================\n"
                f"Cleanup Time       : "
                f"{now.strftime('%Y-%m-%d %I:%M:%S %p')}\n"
                f"Runs Archived      : {archived_count}\n"
                "\n"
                "PATIENT DATA PROTECTION\n"
                "----------------------\n"
                "Patient Master      : NOT DELETED\n"
                "Patient IDs         : NOT DELETED\n"
                "OP Numbers          : NOT DELETED\n"
                "Departments         : NOT DELETED\n"
                "Patient Type D      : NOT DELETED\n"
                "Diagnosis           : NOT DELETED\n"
                "Investigation       : NOT DELETED\n"
                "Lab Orders          : NOT DELETED\n"
                "Clinical Records    : NOT DELETED\n"
                "Billing Records     : NOT DELETED\n"
                "Audit Records       : NOT DELETED\n"
                "\n"
                "Auto Trigger History has been archived safely.\n"
                "=================================================="
            )
        )