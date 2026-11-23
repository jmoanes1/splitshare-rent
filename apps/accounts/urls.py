from django.urls import path

from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)

from apps.accounts import views
from apps.accounts.forms import PasswordResetForm, SetPasswordForm

urlpatterns = [
    path('register/renter/', views.register_renter, name='register_renter'),
    path('register/owner/', views.register_owner, name='register_owner'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('password/change/', views.password_change, name='password_change'),
    path(
        'password/reset/',
        PasswordResetView.as_view(
            form_class=PasswordResetForm,
            template_name='accounts/password_reset.html',
            email_template_name='accounts/email/password_reset_email.txt',
            subject_template_name='accounts/email/password_reset_subject.txt',
        ),
        name='password_reset',
    ),
    path(
        'password/reset/done/',
        PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'password/reset/confirm/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(
            form_class=SetPasswordForm,
            template_name='accounts/password_reset_confirm.html',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password/reset/complete/',
        PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('email/verification/', views.email_verification, name='email_verification'),
    path('email/send/', views.email_verification_send, name='email_verification_send'),
    path('email/verify/<str:token>/', views.email_verify, name='email_verify'),
    path(
        'verification/document/<int:document_id>/',
        views.verification_document, name='verification_document',
    ),
    path(
        'verification/submit/', views.verification_submit, name='verification_submit',
    ),
    path(
        'verification/review/', views.verification_review, name='verification_review',
    ),
    path(
        'verification/review/<int:document_id>/<str:action>/',
        views.verification_review_action,
        name='verification_review_action',
    ),
]
