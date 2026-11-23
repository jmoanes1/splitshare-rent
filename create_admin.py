import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.accounts.models import User

admin_email = "admin@sharedspace.ph"
admin_pass = "Admin!2024"

user, created = User.objects.get_or_create(
    email=admin_email,
    defaults={
        "username": admin_email,
        "first_name": "Admin",
        "last_name": "User",
        "role": User.Role.ADMIN,
        "is_staff": True,
        "is_superuser": True,
        "email_verified": True,
    }
)

user.set_password(admin_pass)
user.role = User.Role.ADMIN
user.is_staff = True
user.is_superuser = True
user.email_verified = True
user.save()

print(f"Admin account '{admin_email}' successfully configured.")
