from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.tokens import default_token_generator
from django.core import mail, signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.models import RenterProfile, User, VerificationDocument
from apps.properties.models import Booking, Property, Room, SavedListing


class MarketplaceFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user('host@tests.example', 'Str0ng!Pass99', role='OWNER')
        cls.renter = User.objects.create_user('renter@tests.example', 'Str0ng!Pass99')
        cls.other = User.objects.create_user('other@tests.example', 'Str0ng!Pass99')
        cls.property = Property.objects.create(
            owner=cls.owner, title='Shared home', description='A comfortable home',
            region='NCR', province='Metro Manila', city='Makati',
            status=Property.Status.APPROVED, is_published=True,
        )
        cls.room = Room.objects.create(property_listing=cls.property, name='Sunny room', monthly_rent=8500)

    def setUp(self):
        self.client.force_login(self.renter)

    def test_booking_creates_request_and_preserves_message(self):
        response = self.client.post(reverse('booking_create', args=[self.room.pk]), {
            'message': 'I would like a viewing.', 'move_in_date': timezone.localdate().isoformat(),
        })
        self.assertRedirects(response, reverse('renter_dashboard'))
        self.assertEqual(Booking.objects.get().message, 'I would like a viewing.')
        self.assertEqual(Booking.objects.get().status, Booking.Status.PENDING)

    def test_duplicate_request_does_not_create_second_booking(self):
        url = reverse('booking_create', args=[self.room.pk])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(Booking.objects.count(), 1)

    def test_reserved_room_cannot_be_booked(self):
        self.room.availability = Room.Availability.RESERVED
        self.room.save()
        self.client.post(reverse('booking_create', args=[self.room.pk]))
        self.assertFalse(Booking.objects.exists())

    def test_owner_cannot_submit_booking(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('booking_create', args=[self.room.pk]))
        self.assertFalse(Booking.objects.exists())

    def test_past_and_malformed_dates_show_field_errors(self):
        for value in ['bad-date', (timezone.localdate() - timedelta(days=1)).isoformat()]:
            response = self.client.post(reverse('booking_create', args=[self.room.pk]), {
                'move_in_date': value, 'message': 'Keep my introduction',
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn('move_in_date', response.context['form'].errors)
            self.assertContains(response, 'Keep my introduction')
        self.assertFalse(Booking.objects.exists())

    def test_date_cannot_precede_availability(self):
        self.room.available_from = timezone.localdate() + timedelta(days=7)
        self.room.save()
        response = self.client.post(reverse('booking_create', args=[self.room.pk]), {
            'move_in_date': timezone.localdate().isoformat(),
        })
        self.assertIn('move_in_date', response.context['form'].errors)

    def test_host_accepts_only_one_request_per_room(self):
        first = Booking.objects.create(room=self.room, renter=self.renter)
        second = Booking.objects.create(room=self.room, renter=self.other)
        self.client.force_login(self.owner)
        self.client.post(reverse('booking_action', args=[first.pk]), {'action': 'accept'})
        self.client.post(reverse('booking_action', args=[second.pk]), {'action': 'accept'})
        first.refresh_from_db()
        second.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(first.status, Booking.Status.ACCEPTED)
        self.assertEqual(second.status, Booking.Status.PENDING)
        self.assertEqual(self.room.availability, Room.Availability.RESERVED)

    def test_completed_request_cannot_change_state(self):
        booking = Booking.objects.create(room=self.room, renter=self.renter, status=Booking.Status.ACCEPTED)
        self.client.force_login(self.owner)
        self.client.post(reverse('booking_action', args=[booking.pk]), {'action': 'reject'})
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.ACCEPTED)

    def test_other_owner_cannot_review_request(self):
        booking = Booking.objects.create(room=self.room, renter=self.renter)
        another_owner = User.objects.create_user('another-host@tests.example', role='OWNER')
        self.client.force_login(another_owner)
        response = self.client.post(reverse('booking_action', args=[booking.pk]), {'action': 'accept'})
        self.assertEqual(response.status_code, 404)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_cancel_pending_request(self):
        booking = Booking.objects.create(room=self.room, renter=self.renter)
        self.client.post(reverse('booking_cancel', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_other_renter_cannot_cancel_request(self):
        booking = Booking.objects.create(room=self.room, renter=self.other)
        response = self.client.post(reverse('booking_cancel', args=[booking.pk]))
        self.assertEqual(response.status_code, 404)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PENDING)

    def test_accepted_booking_cannot_be_cancelled(self):
        booking = Booking.objects.create(room=self.room, renter=self.renter, status=Booking.Status.ACCEPTED)
        self.client.post(reverse('booking_cancel', args=[booking.pk]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.ACCEPTED)

    def test_saved_listing_toggle(self):
        url = reverse('toggle_saved', args=[self.room.pk])
        self.client.post(url)
        self.assertTrue(SavedListing.objects.filter(renter=self.renter, room=self.room).exists())
        self.client.post(url)
        self.assertFalse(SavedListing.objects.exists())

    def test_saved_redirect_cannot_leave_site(self):
        response = self.client.post(reverse('toggle_saved', args=[self.room.pk]), {'next': '//external.example/'})
        self.assertRedirects(response, reverse('room_detail', args=[self.room.pk]))

    def test_invalid_budget_does_not_crash_listings(self):
        for value in ['NaN', 'Infinity', '-1', 'invalid', '1e500']:
            response = self.client.get(reverse('browse_rooms'), {'max_price': value})
            self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('browse_rooms'), {'max_price': 'NaN'})
        self.assertContains(response, 'Enter a valid non-negative monthly budget.')

    def test_dashboard_renders_booking_saved_and_rental_information(self):
        Booking.objects.create(room=self.room, renter=self.renter, status=Booking.Status.ACCEPTED)
        SavedListing.objects.create(room=self.room, renter=self.renter)
        response = self.client.get(reverse('renter_dashboard'))
        self.assertEqual(response.context['active_rentals'].count(), 1)
        self.assertEqual(response.context['saved_rooms'].count(), 1)
        self.assertContains(response, self.room.name)


class AccountCompletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('account@tests.example', 'Str0ng!Pass99')
        RenterProfile.objects.create(user=cls.user, first_name='Ana', last_name='Reyes')

    def test_sequential_registrations_have_distinct_usernames(self):
        for email in ['first@tests.example', 'second@tests.example']:
            response = self.client.post(reverse('register_renter'), {
                'first_name': 'New', 'last_name': 'Renter', 'email': email,
                'password1': 'Str0ng!Pass99', 'password2': 'Str0ng!Pass99', 'terms_accepted': 'on',
            })
            self.assertRedirects(response, reverse('renter_dashboard'))
            self.assertEqual(User.objects.get(email=email).username, email)
        self.assertEqual(len(mail.outbox), 2)

    def test_login_returns_to_room(self):
        response = self.client.post(reverse('login'), {
            'email': self.user.email, 'password': 'Str0ng!Pass99', 'next': '/properties/browse/',
        })
        self.assertRedirects(response, '/properties/browse/')

    def test_login_rejects_external_redirect(self):
        response = self.client.post(reverse('login'), {
            'email': self.user.email, 'password': 'Str0ng!Pass99', 'next': '//external.example/',
        })
        self.assertRedirects(response, reverse('renter_dashboard'))

    def test_email_confirmation_and_tampered_link(self):
        token = signing.dumps({'user_id': self.user.pk, 'email': self.user.email}, salt='email-verification')
        response = self.client.get(reverse('email_verify', args=[token]))
        self.assertContains(response, 'Email verified')
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        response = self.client.get(reverse('email_verify', args=[token + 'tampered']))
        self.assertContains(response, 'This link is no longer valid')

    def test_expired_verification_link(self):
        with patch('django.core.signing.time.time', return_value=0):
            token = signing.dumps({'user_id': self.user.pk, 'email': self.user.email}, salt='email-verification')
        response = self.client.get(reverse('email_verify', args=[token]))
        self.assertContains(response, 'This link is no longer valid')
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_profile_changes_sync_and_invalidate_old_verification(self):
        token = signing.dumps({'user_id': self.user.pk, 'email': self.user.email}, salt='email-verification')
        self.client.force_login(self.user)
        self.client.post(reverse('profile_edit'), {
            'first_name': 'Updated', 'last_name': 'Name', 'email': 'updated@tests.example', 'phone_number': '09170000000',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.renter_profile.first_name, 'Updated')
        self.assertFalse(self.user.email_verified)
        response = self.client.get(reverse('email_verify', args=[token]))
        self.assertContains(response, 'This link is no longer valid')

    def test_complete_password_reset_and_single_use_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        url = reverse('password_reset_confirm', args=[uid, token])
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Set a new password')
        response = self.client.post(response.request['PATH_INFO'], {
            'new_password1': 'ChangedStr0ng!Pass101', 'new_password2': 'ChangedStr0ng!Pass101',
        }, follow=True)
        self.assertContains(response, 'Password updated')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('ChangedStr0ng!Pass101'))
        self.client.logout()
        self.assertContains(self.client.get(url, follow=True), 'This link is no longer valid')

    def test_document_is_private(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            doc = VerificationDocument.objects.create(
                user=self.user, document_type='GOVERNMENT_ID',
                file=SimpleUploadedFile('private.pdf', b'%PDF-test'),
            )
            url = reverse('verification_document', args=[doc.pk])
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(self.user)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            response.close()
            other = User.objects.create_user('other@tests.example')
            self.client.force_login(other)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.get(doc.file.url).status_code, 404)

    @override_settings(DEBUG=False)
    def test_branded_error_pages(self):
        response = self.client.get('/not-a-real-page/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'ShareSplit', status_code=404)
