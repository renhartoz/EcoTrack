from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Reset public database schema."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE;")
            cursor.execute("CREATE SCHEMA public;")
        self.stdout.write(self.style.SUCCESS("Public schema reset successfully."))
