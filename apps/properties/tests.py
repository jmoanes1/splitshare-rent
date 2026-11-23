"""Phase 2 tests: properties, rooms, browse, room detail, become a host."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.properties.models import Property, PropertyImage, Room, RoomImage

STRONG_PASSWORD = 'Str0ng!Pass99'


def make_owner(email='owner@example.com'):
    return User.objects.create_user(
        email=email, password=STRONG_PASSWORD, role=User.Role.OWNER,
        first_name='Juan', last_name='Dela Cruz',
    )


def make_property(owner, **kwargs):
    defaults = {
        'title': 'Test Property',
        'description': 'A test property',
        'property_type': Property.PropertyType.HOUSE,
        'region': 'NCR',
        'province': 'Metro Manila',
        'city': 'Quezon City',
        'barangay': 'Barangay Test',
        'status': Property.Status.APPROVED,
        'is_published': True,
    }
    defaults.update(kwargs)
    return Property.objects.create(owner=owner, **defaults)


def make_room(property_listing, **kwargs):
    defaults = {
        'name': 'Test Room',
        'description': 'A test room',
        'room_type': Room.RoomType.PRIVATE,
        'monthly_rent': Decimal('15000.00'),
        'furnished': True,
        'max_occupants': 1,
        'bathroom_type': 'SHARED',
        'availability': Room.Availability.AVAILABLE,
    }
    defaults.update(kwargs)
    return Room.objects.create(property_listing=property_listing, **defaults)


class PropertyModelTests(TestCase):
    def setUp(self):
        self.owner = make_owner()

    def test_property_creation(self):
        prop = make_property(self.owner)
        self.assertEqual(prop.title, 'Test Property')
        self.assertEqual(prop.owner, self.owner)
        self.assertEqual(prop.status, Property.Status.APPROVED)
        self.assertTrue(prop.is_published)
        self.assertEqual(str(prop), 'Test Property')

    def test_property_location_property(self):
        prop = make_property(self.owner, barangay='Brgy 1', city='Quezon City', province='Metro Manila', region='NCR')
        self.assertIn('Quezon City', prop.location)
        self.assertIn('Metro Manila', prop.location)

    def test_property_main_image_none(self):
        prop = make_property(self.owner)
        self.assertIsNone(prop.main_image)

    def test_property_str(self):
        prop = make_property(self.owner, title='My House')
        self.assertEqual(str(prop), 'My House')


class RoomModelTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.property = make_property(self.owner)

    def test_room_creation(self):
        room = make_room(self.property)
        self.assertEqual(room.name, 'Test Room')
        self.assertEqual(room.property_listing, self.property)
        self.assertEqual(room.monthly_rent, Decimal('15000.00'))
        self.assertEqual(str(room), 'Test Room -- Test Property')

    def test_room_is_bookable(self):
        room = make_room(self.property)
        self.assertTrue(room.is_bookable)

    def test_room_not_bookable_when_unavailable(self):
        room = make_room(self.property, availability=Room.Availability.OCCUPIED)
        self.assertFalse(room.is_bookable)

    def test_room_not_bookable_when_property_not_approved(self):
        self.property.status = Property.Status.DRAFT
        self.property.save()
        room = make_room(self.property)
        self.assertFalse(room.is_bookable)

    def test_room_main_image_none(self):
        room = make_room(self.property)
        self.assertIsNone(room.main_image)


class PropertyImageModelTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.property = make_property(self.owner)

    def test_property_image_creation(self):
        img = PropertyImage.objects.create(
            property=self.property, caption='Main photo', is_main=True,
        )
        self.assertEqual(img.property, self.property)
        self.assertTrue(img.is_main)
        self.assertEqual(str(img.property), 'Test Property')


class RoomImageModelTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.property = make_property(self.owner)
        self.room = make_room(self.property)

    def test_room_image_creation(self):
        img = RoomImage.objects.create(room=self.room, caption='Room photo')
        self.assertEqual(img.room, self.room)
        self.assertEqual(str(img.room), 'Test Room -- Test Property')


class BrowseRoomsViewTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.prop = make_property(self.owner, city='Quezon City', province='Metro Manila')
        make_room(self.prop, monthly_rent=Decimal('12000.00'), furnished=True)
        make_room(self.prop, monthly_rent=Decimal('18000.00'), furnished=False)
        self.prop2 = make_property(
            self.owner, title='Second Property', city='Cebu City', province='Cebu',
        )
        make_room(self.prop2, monthly_rent=Decimal('10000.00'), furnished=True)

    def test_browse_rooms_loads(self):
        response = self.client.get(reverse('browse_rooms'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Browse available rooms')
        self.assertEqual(len(response.context['rooms']), 3)

    def test_browse_rooms_only_shows_available(self):
        make_room(self.prop, availability=Room.Availability.OCCUPIED)
        response = self.client.get(reverse('browse_rooms'))
        self.assertEqual(len(response.context['rooms']), 3)

    def test_browse_rooms_filter_by_city(self):
        response = self.client.get(reverse('browse_rooms') + '?city=Cebu City')
        self.assertEqual(len(response.context['rooms']), 1)
        self.assertEqual(response.context['rooms'][0].property_listing.city, 'Cebu City')

    def test_browse_rooms_filter_by_max_price(self):
        response = self.client.get(reverse('browse_rooms') + '?max_price=12000')
        self.assertEqual(len(response.context['rooms']), 2)
        for room in response.context['rooms']:
            self.assertLessEqual(room.monthly_rent, Decimal('12000.00'))

    def test_browse_rooms_filter_by_furnished(self):
        response = self.client.get(reverse('browse_rooms') + '?furnished=true')
        self.assertEqual(len(response.context['rooms']), 2)
        for room in response.context['rooms']:
            self.assertTrue(room.furnished)

    def test_browse_rooms_filter_by_room_type(self):
        response = self.client.get(reverse('browse_rooms') + '?room_type=SHARED')
        self.assertEqual(len(response.context['rooms']), 0)

    def test_browse_rooms_search_by_location(self):
        response = self.client.get(reverse('browse_rooms') + '?q=Cebu')
        self.assertEqual(len(response.context['rooms']), 1)

    def test_browse_rooms_sort_price_asc(self):
        response = self.client.get(reverse('browse_rooms') + '?sort=price_asc')
        rents = [r.monthly_rent for r in response.context['rooms']]
        self.assertEqual(rents, sorted(rents))

    def test_browse_rooms_pagination(self):
        for i in range(15):
            make_room(self.prop, name=f'Room {i}', monthly_rent=Decimal('10000.00'))
        response = self.client.get(reverse('browse_rooms') + '?page=1')
        self.assertEqual(len(response.context['rooms']), 12)
        self.assertTrue(response.context['page_obj'].has_next())


class RoomDetailViewTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.property = make_property(self.owner)
        self.room = make_room(self.property)

    def test_room_detail_loads(self):
        response = self.client.get(reverse('room_detail', args=[self.room.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.room.name)
        self.assertContains(response, '₱15,000')

    def test_room_detail_404_for_nonexistent(self):
        response = self.client.get(reverse('room_detail', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_room_detail_404_for_unpublished_property(self):
        self.property.is_published = False
        self.property.save()
        response = self.client.get(reverse('room_detail', args=[self.room.id]))
        self.assertEqual(response.status_code, 404)


class BecomeAHostViewTests(TestCase):
    def test_become_a_host_loads(self):
        response = self.client.get(reverse('become_a_host'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Become a host')
        self.assertContains(response, 'Register as a host')
        self.assertContains(response, f'href="{reverse("register_owner")}"')


class HomepageFeaturedRoomsTests(TestCase):
    def setUp(self):
        self.owner = make_owner()
        self.property = make_property(self.owner)
        self.room = make_room(self.property)

    def test_homepage_shows_featured_rooms(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Featured rooms')
        self.assertContains(response, self.room.name)

    def test_homepage_does_not_show_unavailable_rooms(self):
        make_room(self.property, availability=Room.Availability.OCCUPIED, name='Occupied Room')
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, 'Occupied Room')
