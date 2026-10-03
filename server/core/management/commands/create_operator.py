import getpass
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from core.models import BankSampah

User = get_user_model()

class Command(BaseCommand):
    help = "Create an operator user linked to a BankSampah."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--bank", required=True)
        parser.add_argument("--city", default=None)
        parser.add_argument("--password", default=None)

    def handle(self, *args, **options):
        username = options["username"].strip()
        bank_name = options["bank"].strip()
        city = options["city"].strip() if options["city"] else None
        password = options["password"]

        if not password:
            password = getpass.getpass("Password: ")
            confirm_password = getpass.getpass("Confirm password: ")
            if password != confirm_password:
                raise CommandError("Passwords do not match.")

        if User.objects.filter(username=username).exists():
            raise CommandError(f"User with username '{username}' already exists.")

        bank, _ = BankSampah.objects.get_or_create(
            name=bank_name,
            defaults={"city": city, "is_demo": False},
        )

        user = User.objects.create_user(
            username=username,
            password=password,
            bank_sampah=bank,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created operator '{user.username}' for bank '{bank.name}'."
            )
        )
