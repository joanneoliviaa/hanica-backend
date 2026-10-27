import os

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = (
        "Seed akun pengguna awal (sistem tidak menyediakan fitur registrasi). "
        "Contoh: python manage.py seed_users --username admin --password 'RahasiaKuat123'"
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("SEED_USERNAME"))
        parser.add_argument("--password", default=os.environ.get("SEED_PASSWORD"))
        parser.add_argument("--email", default=os.environ.get("SEED_EMAIL", ""))
        parser.add_argument(
            "--superuser",
            action="store_true",
            help="Jadikan superuser (bisa masuk /admin untuk mengelola akun lain).",
        )

    def handle(self, *args, **opts):
        username, password = opts["username"], opts["password"]
        if not username or not password:
            raise CommandError(
                "Isi --username dan --password (atau env SEED_USERNAME / SEED_PASSWORD)."
            )

        user, created = User.objects.get_or_create(
            username=username, defaults={"email": opts["email"]}
        )
        user.set_password(password)  # password di-hash otomatis oleh Django
        if opts["superuser"]:
            user.is_staff = True
            user.is_superuser = True
        user.save()

        status = "dibuat" if created else "sudah ada, password diperbarui"
        self.stdout.write(self.style.SUCCESS(f"User '{username}' {status}."))
