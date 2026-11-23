import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
import inspect
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import PasswordResetForm
print(inspect.getsource(PasswordResetForm.send_mail))
