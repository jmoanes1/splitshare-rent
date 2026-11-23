"""
Account views: registration (renter/owner), login, logout.

Roles are assigned by the server in the forms; visitors can never
register as administrators.
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import send_mail
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from types import SimpleNamespace
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.decorators import admin_required, owner_required, renter_required
from apps.accounts.forms import (
    EmailLoginForm,
    OwnerRegistrationForm,
    PasswordChangeForm,
    ProfileEditForm,
    RenterRegistrationForm,
    VerificationDocumentForm,
)
from apps.accounts.models import User, VerificationDocument, VerificationStatus


def _send_verification_email(request, user):
    token = signing.dumps({'user_id': user.pk, 'email': user.email}, salt='email-verification')
    url = request.build_absolute_uri(reverse('email_verify', args=[token]))
    send_mail(
        'Verify your ShareSplit Rent email',
        f'Confirm your email address to complete your ShareSplit Rent account.\n\n{url}\n\n'
        'This link expires in 24 hours. If you did not create this account, ignore this email.',
        None,
        [user.email],
    )


@login_required
def email_verification(request):
    return render(request, 'accounts/email_verification.html')


@login_required
@require_POST
def email_verification_send(request):
    if not request.user.email_verified:
        _send_verification_email(request, request.user)
        messages.success(request, 'A verification link has been sent to your email address.')
    return redirect('email_verification')


def email_verify(request, token):
    try:
        payload = signing.loads(token, salt='email-verification', max_age=86400)
    except signing.BadSignature:
        return render(request, 'accounts/email_verification.html', {'verification_invalid': True})
    user = User.objects.filter(pk=payload['user_id'], email=payload['email']).first()
    if user is None:
        return render(request, 'accounts/email_verification.html', {'verification_invalid': True})
    user.email_verified = True
    user.save(update_fields=['email_verified'])
    return render(request, 'accounts/email_verification.html', {'verification_complete': True})


@login_required
def verification_document(request, document_id):
    document = get_object_or_404(VerificationDocument, pk=document_id)
    if document.user_id != request.user.pk and not (
        request.user.is_admin_role or request.user.is_staff
    ):
        raise Http404
    try:
        response = FileResponse(document.file.open('rb'), as_attachment=True)
    except FileNotFoundError:
        raise Http404
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def private_media(request, path):
    raise Http404


def _dashboard_redirect(user):
    """Send a freshly authenticated/registered user to their dashboard."""
    if user.role == 'OWNER':
        return redirect('owner_dashboard')
    if user.role == 'ADMIN' or user.is_staff or user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('renter_dashboard')


def register_renter(request):
    form = RenterRegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        _send_verification_email(request, user)
        messages.success(request, 'Welcome to ShareSplit Rent! Check your inbox to verify your email.')
        return _dashboard_redirect(user)
    return render(request, 'accounts/register_renter.html', {'form': form})


def register_owner(request):
    form = OwnerRegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        _send_verification_email(request, user)
        messages.success(request, 'Welcome to ShareSplit Rent! Check your inbox to verify your email.')
        return _dashboard_redirect(user)
    return render(request, 'accounts/register_owner.html', {'form': form})


def user_login(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')
    form = EmailLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return _dashboard_redirect(user)
        messages.error(request, 'Invalid email or password.')
    return render(request, 'accounts/login.html', {'form': form, 'next_url': next_url})


@require_POST
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')


# --- Profile management ------------------------------------------------------

@login_required
def profile(request):
    """View and edit the current user's profile."""
    profile_obj = None
    if request.user.is_renter:
        profile_obj = getattr(request.user, 'renter_profile', None)
    elif request.user.is_owner:
        profile_obj = getattr(request.user, 'owner_profile', None)

    # If no profile record exists yet, build a lightweight placeholder so
    # the profile template can still render the user's core info.
    if profile_obj is None:
        profile_obj = SimpleNamespace(
            first_name=request.user.first_name,
            last_name=request.user.last_name,
            phone_number=request.user.phone_number,
            date_of_birth=None,
            employment_status='',
            business_name='',
            profile_picture='',
            verification_status='PENDING',
        )

    documents = request.user.verification_documents.all()
    return render(request, 'accounts/profile.html', {
        'profile': profile_obj,
        'documents': documents,
    })


@login_required
def profile_edit(request):
    """Edit personal information (first name, last name, phone, email)."""
    previous_email = request.user.email
    form = ProfileEditForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        if user.email != previous_email:
            user.email_verified = False
            user.save(update_fields=['email_verified'])
            _send_verification_email(request, user)
        profile_obj = getattr(user, 'renter_profile', None) or getattr(user, 'owner_profile', None)
        if profile_obj:
            profile_obj.first_name = user.first_name
            profile_obj.last_name = user.last_name
            profile_obj.phone_number = user.phone_number
            profile_obj.save(update_fields=['first_name', 'last_name', 'phone_number'])
        messages.success(request, 'Your profile has been updated.')
        return redirect('profile')
    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def password_change(request):
    """Change the user's password with old-password verification."""
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        request.user.set_password(form.cleaned_data['new_password2'])
        request.user.save()
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Your password has been changed.')
        return redirect('profile')
    return render(request, 'accounts/password_change.html', {'form': form})


# --- Identity verification --------------------------------------------------

@login_required
def verification_submit(request):
    """Submit an identity verification document."""
    # Prevent duplicate pending submissions.
    if request.user.verification_documents.filter(
        status=VerificationStatus.PENDING,
    ).exists():
        messages.info(request, 'You already have a document under review.')
        return redirect('profile')

    form = VerificationDocumentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        document = form.save(commit=False)
        document.user = request.user
        document.status = VerificationStatus.PENDING
        document.save()
        messages.success(request, 'Your document has been submitted for review.')
        return redirect('profile')
    return render(request, 'accounts/verification_submit.html', {'form': form})


# --- Admin verification review ---------------------------------------------

@admin_required
def verification_review(request):
    """Admin view: list all verification documents for review."""
    documents = VerificationDocument.objects.select_related('user').all()
    return render(request, 'accounts/verification_review.html', {'documents': documents})


@admin_required
@require_POST
def verification_review_action(request, document_id, action):
    """Approve or reject a verification document."""
    document = get_object_or_404(VerificationDocument, id=document_id)
    if action not in ('approve', 'reject'):
        messages.error(request, 'Invalid action.')
        return redirect('verification_review')

    from django.utils import timezone
    document.status = (
        VerificationStatus.APPROVED
        if action == 'approve'
        else VerificationStatus.REJECTED
    )
    document.reviewed_at = timezone.now()
    document.reviewed_by = request.user
    if action == 'reject':
        document.rejection_reason = request.POST.get('rejection_reason', '')
    document.save()

    # Update the profile verification status too.
    profile = (
        getattr(document.user, 'renter_profile', None)
        or getattr(document.user, 'owner_profile', None)
    )
    if profile:
        profile.verification_status = document.status
        profile.save()

    messages.success(
        request,
        f'Document {document.id} has been {action}d.',
    )
    return redirect('verification_review')


@admin_required
@require_POST
def admin_delete_user(request, user_id):
    """Admin view: safely delete a user account."""
    user_to_delete = get_object_or_404(User, id=user_id)
    if user_to_delete == request.user:
        messages.error(request, 'You cannot delete your own admin account.')
        return redirect('admin_dashboard')

    email = user_to_delete.email
    full_name = user_to_delete.get_full_name() or email
    user_to_delete.delete()
    messages.success(request, f'User account "{full_name}" ({email}) has been permanently deleted.')
    return redirect('admin_dashboard')


