import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
os.chdir(r"c:\Users\NEC\Desktop\PadShare")
import django
django.setup()
from apps.accounts.models import User
User.objects.create_superuser(email="admin@sharedspace.ph", password="Admin!2024", role="ADMIN")
print("Admin created successfully")