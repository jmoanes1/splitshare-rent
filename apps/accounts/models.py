"""
Custom User and profile models for SharedSpace Philippines.

IMPORTANT: This custom User model must exist BEFORE the first migration
is applied. It replaces django.contrib.auth.User (AUTH_USER_MODEL).
Roles are RENTER / OWNER / ADMIN. Users can never register as ADMIN;
administrators are created via `createsuperuser`.
"""

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager that authenticates by email and forces a valid role."""

    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        email = self.normalize_email(email)
        if not email:
            raise ValueError('An email address is required.')
        # AbstractUser still requires a username; derive it from the
        # (unique) email so registration only asks for an email.
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', self.model.Role.RENTER)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        if extra_fields.get('role') == self.model.Role.ADMIN:
            raise ValueError('Use create_superuser() to create administrators.')
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', self.model.Role.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('role') != self.model.Role.ADMIN:
            raise ValueError('Superusers must have the ADMIN role.')
        if not extra_fields.get('is_staff'):
            raise ValueError('Superuser must have is_staff=True.')
        if not extra_fields.get('is_superuser'):
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        RENTER = 'RENTER', 'Renter'
        OWNER = 'OWNER', 'Property Owner'
        ADMIN = 'ADMIN', 'Administrator'

    email = models.EmailField('email address', unique=True)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(
        'role', max_length=10, choices=Role.choices, default=Role.RENTER,
        db_index=True,
    )
    phone_number = models.CharField('phone number', max_length=20, blank=True)
    # Timestamps beyond AbstractUser.date_joined / last_login.
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.email

    @property
    def is_renter(self):
        return self.role == self.Role.RENTER

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    def get_full_name(self):
        return super().get_full_name() or self.email


class VerificationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class RenterProfile(models.Model):
    """Extra renter details kept separate from the shared User account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='renter_profile',
    )
    first_name = models.CharField('first name', max_length=150)
    last_name = models.CharField('last name', max_length=150)
    phone_number = models.CharField('phone number', max_length=20, blank=True)
    date_of_birth = models.DateField('date of birth', null=True, blank=True)
    employment_status = models.CharField(
        'employment status', max_length=20, blank=True,
        choices=[
            ('EMPLOYED', 'Employed'),
            ('SELF_EMPLOYED', 'Self-employed'),
            ('STUDENT', 'Student'),
            ('UNEMPLOYED', 'Unemployed'),
            ('RETIRED', 'Retired'),
            ('OTHER', 'Other'),
        ],
    )
    profile_picture = models.ImageField(
        'profile picture', upload_to='profiles/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        blank=True,
    )
    verification_status = models.CharField(
        'verification status', max_length=10,
        choices=VerificationStatus.choices, default=VerificationStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.user.email})'


class OwnerProfile(models.Model):
    """Extra property-owner details; business name is optional."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='owner_profile',
    )
    first_name = models.CharField('first name', max_length=150)
    last_name = models.CharField('last name', max_length=150)
    phone_number = models.CharField('phone number', max_length=20, blank=True)
    business_name = models.CharField('business name', max_length=200, blank=True)
    profile_picture = models.ImageField(
        'profile picture', upload_to='profiles/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        blank=True,
    )
    verification_status = models.CharField(
        'verification status', max_length=10,
        choices=VerificationStatus.choices, default=VerificationStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.user.email})'


class DocumentType(models.TextChoices):
    GOVERNMENT_ID = 'GOVERNMENT_ID', 'Government-issued ID'
    SUPPORTING = 'SUPPORTING', 'Supporting Document'


class VerificationDocument(models.Model):
    """Identity documents submitted for verification.

    Files are stored privately under media/verification_documents/ and are
    only accessible to the account holder and authorised administrators.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='verification_documents',
    )
    document_type = models.CharField(
        'document type', max_length=20, choices=DocumentType.choices,
    )
    file = models.FileField(
        'document file', upload_to='verification_documents/',
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'pdf'])],
    )
    status = models.CharField(
        'status', max_length=10,
        choices=VerificationStatus.choices, default=VerificationStatus.PENDING,
        db_index=True,
    )
    rejection_reason = models.TextField('rejection reason', blank=True)
    submitted_at = models.DateTimeField(default=timezone.now, editable=False)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_documents',
        limit_choices_to={'is_staff': True},
    )

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user.email} — {self.get_document_type_display()} ({self.status})'
