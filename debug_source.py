import inspect
from django.contrib.auth.views import PasswordResetView
print(inspect.getsource(PasswordResetView.send_mail))
