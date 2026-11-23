"""Automated tests for Phase 1: accounts, auth, and role dashboards."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import (
    OwnerProfile, RenterProfile, User, VerificationDocument, VerificationStatus,
)

STRONG_PASSWORD = 'Str0ng!Pass99'


def make_user(email='user@example.com', password=STRONG_PASSWORD, **overrides):
    return User.objects.create_user(email=email, password=password, **overrides)


def make_owner(email='owner@example.com'):
    return User.objects.create_user(
        email=email, password=STRONG_PASSWORD, role=User.Role.OWNER,
        first_name='Juan', last_name='Dela Cruz',
    )


class DatabaseConnectionTests(TestCase):
    def test_database_connection(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_user_table_query_runs(self):
        self.assertIsInstance(User.objects.count(), int)


class CustomUserTests(TestCase):
    def test_custom_user_creation(self):
        user = make_user('juan@example.com', first_name='Juan', last_name='Dela Cruz')
        user.refresh_from_db()
        self.assertEqual(user.email, 'juan@example.com')
        self.assertEqual(user.role, User.Role.RENTER)
        self.assertTrue(user.check_password(STRONG_PASSWORD))
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.date_joined)
        self.assertIsNone(user.last_login)

    def test_username_is_derived_from_email(self):
        user = make_user('maria@example.com')
        self.assertEqual(user.username, 'maria@example.com')

    def test_create_user_cannot_create_admin(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='bad@example.com', password=STRONG_PASSWORD, role=User.Role.ADMIN,
            )

    def test_create_superuser_has_admin_role_and_permissions(self):
        admin = User.objects.create_superuser(email='admin@example.com', password=STRONG_PASSWORD)
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_owner_role_creation(self):
        user = make_user('owner@example.com', role=User.Role.OWNER)
        self.assertTrue(user.is_owner)
        self.assertFalse(user.is_renter)


class RegistrationTests(TestCase):
    def renter_payload(self, email='renter@example.com', **overrides):
        payload = {
            'first_name': 'Ana',
            'last_name': 'Reyes',
            'email': email,
            'phone_number': '09171234567',
            'password1': STRONG_PASSWORD,
            'password2': STRONG_PASSWORD,
            'terms_accepted': 'on',
        }
        payload.update(overrides)
        return payload

    def test_renter_registration_creates_user_and_profile(self):
        response = self.client.post(reverse('register_renter'), self.renter_payload())
        self.assertRedirects(response, reverse('renter_dashboard'))
        user = User.objects.get(email='renter@example.com')
        self.assertEqual(user.role, User.Role.RENTER)
        self.assertTrue(RenterProfile.objects.filter(user=user).exists())

    def test_owner_registration_creates_user_and_profile(self):
        response = self.client.post(
            reverse('register_owner'),
            self.renter_payload(email='host@example.com'),
        )
        self.assertRedirects(response, reverse('owner_dashboard'))
        user = User.objects.get(email='host@example.com')
        self.assertEqual(user.role, User.Role.OWNER)
        self.assertTrue(OwnerProfile.objects.filter(user=user).exists())

    def test_registration_cannot_self_assign_admin_role(self):
        self.client.post(
            reverse('register_renter'),
            self.renter_payload(role=User.Role.ADMIN, is_staff='on', is_superuser='on'),
        )
        user = User.objects.get(email='renter@example.com')
        self.assertEqual(user.role, User.Role.RENTER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_duplicate_email_prevention(self):
        make_user('taken@example.com')
        response = self.client.post(
            reverse('register_renter'), self.renter_payload(email='taken@example.com'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email='taken@example.com').count(), 1)

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(
            reverse('register_renter'),
            self.renter_payload(password2='Different!Pass99'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='renter@example.com').exists())

    def test_terms_must_be_accepted(self):
        payload = self.renter_payload()
        del payload['terms_accepted']
        response = self.client.post(reverse('register_renter'), payload)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = make_user('login@example.com')

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            reverse('login'),
            {'email': 'login@example.com', 'password': STRONG_PASSWORD},
        )
        self.assertRedirects(response, reverse('renter_dashboard'))
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_login_with_invalid_credentials(self):
        response = self.client.post(
            reverse('login'),
            {'email': 'login@example.com', 'password': 'wrong-password'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid email or password')

    def test_login_with_unknown_email(self):
        response = self.client.post(
            reverse('login'),
            {'email': 'nobody@example.com', 'password': STRONG_PASSWORD},
        )
        self.assertContains(response, 'Invalid email or password')

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            reverse('login'),
            {'email': 'login@example.com', 'password': STRONG_PASSWORD},
        )
        self.assertContains(response, 'Invalid email or password')

    def test_logout(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)


class RoleBasedAccessTests(TestCase):
    def setUp(self):
        self.renter = make_user('renter@example.com', role=User.Role.RENTER)
        self.owner = make_user('owner@example.com', role=User.Role.OWNER)
        self.admin = User.objects.create_superuser(
            email='sysadmin@example.com', password=STRONG_PASSWORD,
        )

    def test_renter_can_access_renter_dashboard(self):
        self.client.force_login(self.renter)
        response = self.client.get(reverse('renter_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'renter@example.com')

    def test_owner_can_access_owner_dashboard(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('owner_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'owner@example.com')

    def test_admin_can_access_admin_dashboard(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total users')
        self.assertEqual(response.context['stats']['total_users'], 3)

    def test_renter_cannot_access_owner_or_admin_dashboard(self):
        self.client.force_login(self.renter)
        for name in ('owner_dashboard', 'admin_dashboard'):
            self.assertRedirects(
                self.client.get(reverse(name)), reverse('dashboard'),
                fetch_redirect_response=False,
            )

    def test_owner_cannot_access_renter_or_admin_dashboard(self):
        self.client.force_login(self.owner)
        for name in ('renter_dashboard', 'admin_dashboard'):
            self.assertRedirects(
                self.client.get(reverse(name)), reverse('dashboard'),
                fetch_redirect_response=False,
            )

    def test_admin_cannot_access_renter_or_owner_dashboard(self):
        self.client.force_login(self.admin)
        for name in ('renter_dashboard', 'owner_dashboard'):
            self.assertRedirects(
                self.client.get(reverse(name)), reverse('dashboard'),
                fetch_redirect_response=False,
            )

    def test_anonymous_redirected_to_login(self):
        for name in ('renter_dashboard', 'owner_dashboard', 'admin_dashboard', 'dashboard'):
            url = reverse(name)
            self.assertRedirects(self.client.get(url), f'/accounts/login/?next={url}')

    def test_dashboard_router_sends_users_to_their_own_dashboard(self):
        for user, template in (
            (self.renter, 'dashboard/renter.html'),
            (self.owner, 'dashboard/owner.html'),
            (self.admin, 'dashboard/admin.html'),
        ):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(reverse('dashboard'))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.context['user'], user)
                self.client.logout()

    def test_renter_cannot_use_admin_site(self):
        self.client.force_login(self.renter)
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_superuser_can_use_admin_site(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/').status_code, 200)


class ProfileManagementTests(TestCase):
    def setUp(self):
        self.user = make_user('profe@example.com')
        self.client.force_login(self.user)

    def test_profile_page_loads(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1>My profile</h1>', html=True)
        self.assertContains(response, 'profe@example.com')

    def test_profile_edit_loads(self):
        response = self.client.get(reverse('profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h1>Edit profile</h1>', html=True)

    def test_profile_edit_updates_info(self):
        response = self.client.post(
            reverse('profile_edit'),
            {
                'first_name': 'Ana',
                'last_name': 'Reyes',
                'email': 'ana@example.com',
                'phone_number': '09171234567',
            },
        )
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Ana')
        self.assertEqual(self.user.last_name, 'Reyes')
        self.assertEqual(self.user.email, 'ana@example.com')
        self.assertEqual(self.user.phone_number, '09171234567')

    def test_profile_edit_duplicate_email_rejected(self):
        make_user('other@example.com')
        response = self.client.post(
            reverse('profile_edit'),
            {
                'first_name': 'Jhon',
                'last_name': 'Doe',
                'email': 'other@example.com',
                'phone_number': '09171234567',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].errors['email'],
            ['An account with this email already exists.'],
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'profe@example.com')

    def test_password_change_works(self):
        response = self.client.post(
            reverse('password_change'),
            {
                'old_password': STRONG_PASSWORD,
                'new_password1': 'NewStr0ng!Pass100',
                'new_password2': 'NewStr0ng!Pass100',
            },
        )
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStr0ng!Pass100'))

    def test_password_change_wrong_old_password(self):
        response = self.client.post(
            reverse('password_change'),
            {
                'old_password': 'wrongpassword',
                'new_password1': 'NewStr0ng!Pass100',
                'new_password2': 'NewStr0ng!Pass100',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your current password is incorrect')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(STRONG_PASSWORD))


class VerificationTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.owner_profile = OwnerProfile.objects.create(
            user=self.owner,
            first_name=self.owner.first_name,
            last_name=self.owner.last_name,
        )
        self.renter = make_user('renter@example.com', role=User.Role.RENTER)
        self.admin = User.objects.create_superuser(
            email='admin@example.com', password=STRONG_PASSWORD,
        )
        self.client.force_login(self.owner)

    def test_verification_submit_creates_document(self):
        response = self.client.post(
            reverse('verification_submit'),
            {
                'document_type': 'GOVERNMENT_ID',
                'file': SimpleUploadedFile(
                    'id.jpg', b'fake-image-data', content_type='image/jpeg',
                ),
            },
        )
        self.assertRedirects(response, reverse('profile'))
        self.assertTrue(self.owner.verification_documents.exists())

    def test_verification_submit_prevents_duplicate(self):
        self.client.post(
            reverse('verification_submit'),
            {
                'document_type': 'GOVERNMENT_ID',
                'file': SimpleUploadedFile(
                    'id.jpg', b'fake-image-data', content_type='image/jpeg',
                ),
            },
        )
        response = self.client.post(
            reverse('verification_submit'),
            {
                'document_type': 'SUPPORTING',
                'file': SimpleUploadedFile(
                    'sup.pdf', b'fake-pdf', content_type='application/pdf',
                ),
            },
        )
        self.assertRedirects(response, reverse('profile'))
        self.assertEqual(self.owner.verification_documents.count(), 1)

    def test_verification_review_not_accessible_to_renter(self):
        self.client.logout()
        self.client.force_login(self.renter)
        response = self.client.get(reverse('verification_review'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_verification_review_action_approve(self):
        doc = VerificationDocument.objects.create(
            user=self.owner,
            document_type='GOVERNMENT_ID',
            file=SimpleUploadedFile('id.jpg', b'fake', content_type='image/jpeg'),
            status=VerificationStatus.PENDING,
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('verification_review_action', args=[doc.id, 'approve']),
        )
        self.assertRedirects(response, reverse('verification_review'))
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'APPROVED')
        self.assertIsNotNone(doc.reviewed_by)
        self.assertIsNotNone(doc.reviewed_at)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.owner_profile.verification_status, 'APPROVED')

    def test_verification_review_action_reject(self):
        doc = VerificationDocument.objects.create(
            user=self.owner,
            document_type='GOVERNMENT_ID',
            file=SimpleUploadedFile('id.jpg', b'fake', content_type='image/jpeg'),
            status=VerificationStatus.PENDING,
        )
        self.client.force_login(self.admin)
        self.client.post(
            reverse('verification_review_action', args=[doc.id, 'reject']),
            {'rejection_reason': 'Missing information.'},
        )
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'REJECTED')
        self.assertEqual(doc.rejection_reason, 'Missing information.')

    def test_verification_review_action_invalid(self):
        doc = VerificationDocument.objects.create(
            user=self.owner,
            document_type='GOVERNMENT_ID',
            file=SimpleUploadedFile('id.jpg', b'fake', content_type='image/jpeg'),
            status=VerificationStatus.PENDING,
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('verification_review_action', args=[doc.id, 'invalid_action']),
        )
        self.assertEqual(response.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.status, 'PENDING')


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = make_user('reset@example.com', password='OldStr0ng!Pass100')

    def test_password_reset_request_sends_email(self):
        response = self.client.post(
            reverse('password_reset'),
            {'email': 'reset@example.com'},
        )
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['reset@example.com'])
        self.assertEqual(email.subject, 'Reset your ShareSplit Rent password')
        self.assertIn('You requested a password reset for your ShareSplit Rent account.', email.body)
        self.assertRegex(
            email.body,
            r'http://testserver/accounts/password/reset/confirm/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/',
        )

    def test_password_reset_confirm_invalid_token(self):
        response = self.client.get(
            reverse('password_reset_confirm', args=['invalid-uid', 'invalid-token']),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This link is no longer valid')


class PublicPageTests(TestCase):
    def test_homepage_loads(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<h1>Find your space.<br><em>Share more.</em> Live better.</h1>',
            html=True,
        )

    def test_about_page_loads(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'About ShareSplit Rent')

    def test_login_and_register_pages_load(self):
        for name in ('login', 'register_renter', 'register_owner'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_404_page(self):
        response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)
