"""
Registration and login forms.

The role is always assigned on the server (RENTER for the renter form,
OWNER for the owner form). No form field lets a visitor choose ADMIN.
"""

from django import forms
from django.contrib.auth.forms import PasswordResetForm as DjangoPasswordResetForm, SetPasswordForm as DjangoSetPasswordForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import OwnerProfile, RenterProfile, User, VerificationDocument

MAX_PROFILE_PICTURE_SIZE = 5 * 1024 * 1024  # 5 MB


class BaseRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='At least 8 characters, not too similar to your other details.',
    )
    password2 = forms.CharField(
        label='Confirm password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    terms_accepted = forms.BooleanField(
        label='I agree to the Terms of Service and the Privacy Notice.',
    )
    profile_picture = forms.ImageField(
        label='Profile picture (optional)', required=False,
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('Passwords do not match.')
        if password2:
            candidate = User(
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
                email=self.cleaned_data.get('email', ''),
            )
            try:
                validate_password(password2, candidate)
            except ValidationError as exc:
                raise ValidationError(list(exc.messages))
        return password2

    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture and picture.size > MAX_PROFILE_PICTURE_SIZE:
            raise ValidationError('Profile picture must be 5 MB or smaller.')
        return picture

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        user.role = self.ROLE
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            self.save_profile(user)
        return user

    def save_profile(self, user):
        raise NotImplementedError


class RenterRegistrationForm(BaseRegistrationForm):
    ROLE = User.Role.RENTER

    date_of_birth = forms.DateField(
        label='Date of birth', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    employment_status = forms.ChoiceField(
        label='Employment status',
        choices=RenterProfile._meta.get_field('employment_status').choices,
        required=False,
    )

    class Meta(BaseRegistrationForm.Meta):
        fields = BaseRegistrationForm.Meta.fields + [
            'profile_picture', 'date_of_birth', 'employment_status',
        ]

    def save_profile(self, user):
        RenterProfile.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            date_of_birth=self.cleaned_data.get('date_of_birth'),
            employment_status=self.cleaned_data.get('employment_status', ''),
            profile_picture=self.cleaned_data.get('profile_picture'),
        )


class OwnerRegistrationForm(BaseRegistrationForm):
    ROLE = User.Role.OWNER

    business_name = forms.CharField(
        label='Business name (optional)', max_length=200, required=False,
    )

    class Meta(BaseRegistrationForm.Meta):
        fields = BaseRegistrationForm.Meta.fields + [
            'profile_picture', 'business_name',
        ]

    def save_profile(self, user):
        OwnerProfile.objects.create(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            business_name=self.cleaned_data.get('business_name', ''),
            profile_picture=self.cleaned_data.get('profile_picture'),
        )


class EmailLoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'you@example.com'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Enter your password'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class PasswordResetForm(DjangoPasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-control', 'placeholder': 'you@example.com'})


class SetPasswordForm(DjangoSetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter a new password'})


class ProfileEditForm(forms.ModelForm):
    """Edit personal information and profile picture."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('An account with this email already exists.')
        return email


class PasswordChangeForm(forms.Form):
    """Change the user's password."""

    old_password = forms.CharField(
        label='Current password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='At least 8 characters, not too similar to your other details.',
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password')
        if old_password and not self.user.check_password(old_password):
            raise ValidationError('Your current password is incorrect.')
        return old_password

    def clean_new_password2(self):
        old_password = self.cleaned_data.get('old_password')
        new_password1 = self.cleaned_data.get('new_password1')
        new_password2 = self.cleaned_data.get('new_password2')
        if new_password1 and new_password2 and new_password1 != new_password2:
            raise ValidationError('Passwords do not match.')
        if old_password and new_password1 and old_password == new_password1:
            raise ValidationError('New password must be different from your current password.')
        if new_password2:
            candidate = User(
                first_name=self.user.first_name,
                last_name=self.user.last_name,
                email=self.user.email,
            )
            try:
                validate_password(new_password2, candidate)
            except ValidationError as exc:
                raise ValidationError(list(exc.messages))
        return new_password2


class BookingRequestForm(forms.Form):
    move_in_date = forms.DateField(
        label='Preferred move-in date', required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Optional — the host will confirm the actual date with you.',
    )
    message = forms.CharField(
        label='Introduce yourself', required=False, max_length=2000,
        widget=forms.Textarea(attrs={
            'rows': 6, 'placeholder': 'Tell the host about yourself and your plans for moving in.',
        }),
        help_text='A friendly, honest introduction gets faster responses.',
    )

    def __init__(self, room, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.earliest_date = max(timezone.localdate(), room.available_from or timezone.localdate())
        self.fields['move_in_date'].widget.attrs['min'] = self.earliest_date.isoformat()
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_move_in_date(self):
        value = self.cleaned_data.get('move_in_date')
        if value and value < self.earliest_date:
            raise ValidationError(f'Choose a move-in date on or after {self.earliest_date:%b %d, %Y}.')
        return value


class VerificationDocumentForm(forms.ModelForm):
    """Submit an identity verification document."""

    class Meta:
        model = VerificationDocument
        fields = ['document_type', 'file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['file'].widget.attrs['accept'] = '.jpg,.jpeg,.png,.pdf'

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            max_size = 10 * 1024 * 1024  # 10 MB
            if file.size > max_size:
                raise ValidationError('Document must be 10 MB or smaller.')
        return file
