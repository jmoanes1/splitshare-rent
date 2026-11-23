import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
import inspect
from django.contrib.auth.views import PasswordResetView
print(inspect.getsource(PasswordResetView.send_mail))
