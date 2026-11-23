"""Seed demo marketplace data for local development. Idempotent: skips if properties exist.

Run: ./venv/Scripts/python.exe seed_demo.py
Demo logins (password for all demo accounts: DemoPass123!):
  renter: demo.renter@example.com
  host:   maria.santos@example.com
  admin:  admin.demo@sharesplitrent.ph
"""
import os
import shutil
from datetime import date, timedelta
from pathlib import Path

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.utils import timezone

from apps.accounts.models import User, RenterProfile, OwnerProfile, VerificationDocument
from apps.properties.models import Property, PropertyImage, Room, RoomImage, Booking, SavedListing

BASE = Path(settings.BASE_DIR)
DEMO_PASSWORD = 'DemoPass123!'

if Property.objects.exists():
    print('Properties already exist — skipping seed.')
    raise SystemExit(0)


def copy_image(src_rel, dest_rel):
    src = BASE / 'static' / src_rel
    dest = BASE / 'media' / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copyfile(src, dest)
    return dest_rel


def make_owner(email, first, last, phone, business='', verified=True):
    user, created = User.objects.get_or_create(email=email, defaults={
        'username': email, 'first_name': first, 'last_name': last,
        'phone_number': phone, 'role': User.Role.OWNER,
    })
    if created:
        user.set_password(DEMO_PASSWORD)
        user.save()
    OwnerProfile.objects.get_or_create(user=user, defaults={
        'first_name': first, 'last_name': last, 'phone_number': phone,
        'business_name': business,
        'verification_status': 'APPROVED' if verified else 'PENDING',
    })
    return user


maria = make_owner('maria.santos@example.com', 'Maria', 'Santos', '+63 917 555 0101', 'Santos Family Homes')
jose = make_owner('jose.reyes@example.com', 'Jose', 'Reyes', '+63 918 555 0202', 'Reyes Properties')
ana = make_owner('ana.cruz@example.com', 'Ana', 'Cruz', '+63 919 555 0303', verified=False)

renter, created = User.objects.get_or_create(email='demo.renter@example.com', defaults={
    'username': 'demo.renter@example.com', 'first_name': 'Demo', 'last_name': 'Renter',
    'phone_number': '+63 917 555 0404', 'role': User.Role.RENTER,
})
if created:
    renter.set_password(DEMO_PASSWORD)
    renter.save()
RenterProfile.objects.get_or_create(user=renter, defaults={
    'first_name': 'Demo', 'last_name': 'Renter', 'phone_number': '+63 917 555 0404',
    'date_of_birth': date(1998, 5, 14), 'employment_status': 'EMPLOYED',
    'verification_status': 'APPROVED',
})

admin, created = User.objects.get_or_create(email='admin.demo@sharesplitrent.ph', defaults={
    'username': 'admin.demo@sharesplitrent.ph', 'first_name': 'Demo', 'last_name': 'Admin',
    'role': User.Role.ADMIN, 'is_staff': True, 'is_superuser': True,
})
if created:
    admin.set_password(DEMO_PASSWORD)
    admin.save()

PROPERTIES = [
    {
        'owner': maria, 'title': 'Sunny Kalayaan Townhouse', 'type': 'TOWNHOUSE',
        'region': 'NCR', 'province': 'Metro Manila', 'city': 'Quezon City', 'barangay': 'Diliman',
        'street_address': '12 Kalayaan Ave', 'floors': 2, 'parking': True,
        'description': 'A bright, well-kept townhouse near UP Diliman and the MRT. The household is quiet, friendly, and used to hosting students and young professionals. Shared kitchen, living room, and laundry area are always clean.',
        'amenities': 'Wi-Fi, shared kitchen, laundry area, living room, dining area',
        'facilities': 'Parking, garden, CCTV at entrance',
        'rules': 'No smoking indoors, quiet hours 10 PM - 7 AM, visitors until 9 PM only, keep shared areas clean',
        'img': 'images/rooms/room-1.jpg',
        'rooms': [
            {'name': 'Private Room with Study Desk', 'img': 'images/rooms/room-1.jpg', 'type': 'PRIVATE',
             'rent': 6500, 'size': 12, 'occupants': 1, 'bath': 'SHARED', 'furnished': True,
             'amenities': 'Single bed, study desk, chair, wardrobe, electric fan, window',
             'desc': 'A cozy private room with a dedicated study desk beside the window — perfect for students or remote workers. Bed, wardrobe, and fan included; just bring your linens.'},
            {'name': "Master's Room with Aircon", 'img': 'images/rooms/room-2.jpg', 'type': 'MASTERS',
             'rent': 9500, 'size': 18, 'occupants': 2, 'bath': 'PRIVATE', 'furnished': True,
             'amenities': 'Queen bed, air conditioner, private bathroom, wardrobe, bedside lamps',
             'desc': "The largest room in the house with its own bathroom and a quiet split-type aircon. Ideal for a couple or anyone who wants extra space and privacy."},
        ],
    },
    {
        'owner': jose, 'title': 'The Grid Residences', 'type': 'CONDO',
        'region': 'NCR', 'province': 'Metro Manila', 'city': 'Makati', 'barangay': 'Poblacion',
        'street_address': '88 Polaris St', 'floors': 1, 'parking': False,
        'description': 'A modern condo unit in the heart of Makati, walking distance to offices, cafes, and the weekend market. Building security is 24/7 with keycard access.',
        'amenities': 'Wi-Fi, air conditioning, shared kitchen, refrigerator, microwave',
        'facilities': 'Building gym, swimming pool, 24/7 security, elevator',
        'rules': 'No pets, no smoking, quiet hours 10 PM - 6 AM, register visitors with building security',
        'img': 'images/rooms/room-3.jpg',
        'rooms': [
            {'name': 'City-View Double Room', 'img': 'images/rooms/room-3.jpg', 'type': 'PRIVATE',
             'rent': 12000, 'size': 16, 'occupants': 2, 'bath': 'SHARED', 'furnished': True,
             'amenities': 'Double bed, air conditioner, work desk, floating shelves, city view',
             'desc': 'Wake up to the Makati skyline. A fully furnished double room with fast Wi-Fi and a proper work desk — everything within walking distance of the CBD.'},
            {'name': 'Compact Solo Room', 'img': 'images/rooms/room-5.jpg', 'type': 'PRIVATE',
             'rent': 8500, 'size': 9, 'occupants': 1, 'bath': 'SHARED', 'furnished': True,
             'amenities': 'Single bed, air conditioner, wardrobe, linen curtains',
             'desc': 'A calm, minimalist solo room for one person. Small but thoughtfully laid out, with the same building amenities as the larger rooms.'},
        ],
    },
    {
        'owner': maria, 'title': 'Cebu Shared Haven', 'type': 'APARTMENT',
        'region': 'Central Visayas', 'province': 'Cebu', 'city': 'Cebu City', 'barangay': 'Lahug',
        'street_address': '5 Archers St', 'floors': 1, 'parking': False,
        'description': 'A relaxed apartment near IT Park with a small balcony garden. The household shares cooking duties on weekends and keeps common areas tidy.',
        'amenities': 'Wi-Fi, shared kitchen, balcony, refrigerator, washing machine',
        'facilities': 'Balcony garden, bike parking',
        'rules': 'No smoking, share kitchen cleanup roster, quiet hours 11 PM - 6 AM',
        'img': 'images/rooms/room-5.jpg',
        'rooms': [
            {'name': 'Minimalist Private Room', 'img': 'images/rooms/room-5.jpg', 'type': 'PRIVATE',
             'rent': 7000, 'size': 11, 'occupants': 1, 'bath': 'SHARED', 'furnished': True,
             'amenities': 'Platform bed, monstera plant, jute rug, linen curtains, wardrobe',
             'desc': 'A serene, Scandinavian-inspired room with morning light and plenty of calm. Five minutes from IT Park by foot.'},
            {'name': 'Twin Shared Room for Students', 'img': 'images/rooms/room-4.jpg', 'type': 'SHARED',
             'rent': 4500, 'size': 14, 'occupants': 2, 'bath': 'SHARED', 'furnished': True,
             'amenities': 'Two single beds, two study desks, corkboard, wardrobe, electric fan',
             'desc': 'A friendly twin room designed for two students — each with a bed and study desk. Split the rent and share the journey.'},
        ],
    },
    {
        'owner': ana, 'title': 'Davao Tropical Home', 'type': 'HOUSE',
        'region': 'Davao Region', 'province': 'Davao del Sur', 'city': 'Davao City', 'barangay': 'Ecoland',
        'street_address': '23 Palm Drive', 'floors': 1, 'parking': True,
        'description': 'A family home with a lush garden, capiz windows, and the warmest host in Ecoland. Breakfast is often shared on weekends. Near schools, malls, and the airport road.',
        'amenities': 'Wi-Fi, shared kitchen, garden, living room, drinking water station',
        'facilities': 'Parking, garden, outdoor seating',
        'rules': 'Family household — respect quiet hours 9 PM - 6 AM, no overnight guests without notice, help keep the garden tidy',
        'img': 'images/rooms/room-6.jpg',
        'rooms': [
            {'name': 'Tropical Private Room', 'img': 'images/rooms/room-6.jpg', 'type': 'PRIVATE',
             'rent': 6000, 'size': 12, 'occupants': 1, 'bath': 'SHARED', 'furnished': True,
             'amenities': 'Rattan headboard bed, capiz window, wardrobe, bench, electric fan',
             'desc': 'A warm island-style room with beautiful capiz light in the mornings. The garden is yours to enjoy with your morning coffee.'},
            {'name': "Garden View Master's", 'img': 'images/rooms/room-2.jpg', 'type': 'MASTERS',
             'rent': 8000, 'size': 17, 'occupants': 2, 'bath': 'PRIVATE', 'furnished': True,
             'amenities': 'Queen bed, air conditioner, private bathroom, garden view, wardrobe',
             'desc': "A spacious master's room overlooking the garden, with its own bathroom and aircon. Quiet wing of the house, away from the street."},
        ],
    },
    {
        'owner': jose, 'title': 'BGC Skyline Suites', 'type': 'CONDO',
        'region': 'NCR', 'province': 'Metro Manila', 'city': 'Taguig', 'barangay': 'Bonifacio Global City',
        'street_address': 'One Skyline Tower, 5th Ave', 'floors': 1, 'parking': False,
        'description': 'A premium condo share in BGC with floor-to-ceiling windows, concierge, and everything the high street offers at your doorstep.',
        'amenities': 'Wi-Fi, air conditioning, shared kitchen, smart TV, washer-dryer',
        'facilities': 'Infinity pool, gym, concierge, 24/7 security',
        'rules': 'No smoking, no pets, quiet hours 10 PM - 7 AM, follow building guest policy',
        'img': 'images/rooms/room-3.jpg',
        'rooms': [
            {'name': 'Skyline Studio Room', 'img': 'images/rooms/room-3.jpg', 'type': 'PRIVATE',
             'rent': 15000, 'size': 20, 'occupants': 2, 'bath': 'PRIVATE', 'furnished': True,
             'amenities': 'Double bed, air conditioner, private bathroom, desk, skyline view',
             'desc': 'The best view in the share — a studio-style private room with its own bathroom and a golden-hour skyline. Premium building amenities included.'},
        ],
    },
    {
        'owner': maria, 'title': 'QC Student House', 'type': 'HOUSE',
        'region': 'NCR', 'province': 'Metro Manila', 'city': 'Quezon City', 'barangay': 'Kamias',
        'street_address': '45 Anonas Ext', 'floors': 2, 'parking': False,
        'description': 'A budget-friendly student house a jeepney ride from UP, Ateneo, and Miriam. Study-friendly common area, unlimited drinking water, and a host who checks in on everyone.',
        'amenities': 'Wi-Fi, shared kitchen, study area, drinking water, laundry line',
        'facilities': 'Study area, bike rack',
        'rules': 'Student-focused house, quiet study hours 7 PM - 10 PM, no smoking, clean-as-you-go in kitchen',
        'img': 'images/rooms/room-4.jpg',
        'rooms': [
            {'name': 'Twin Shared Room', 'img': 'images/rooms/room-4.jpg', 'type': 'SHARED',
             'rent': 4000, 'size': 13, 'occupants': 2, 'bath': 'SHARED', 'furnished': True,
             'amenities': 'Two single beds, two desks, wardrobe, electric fan, corkboard',
             'desc': 'The most affordable way to live near the universities. A clean twin room with your own bed and desk — bring a friend or meet one here.'},
            {'name': 'Budget Private Room', 'img': 'images/rooms/room-1.jpg', 'type': 'PRIVATE',
             'rent': 5500, 'size': 10, 'occupants': 1, 'bath': 'SHARED', 'furnished': True,
             'amenities': 'Single bed, desk, wardrobe, electric fan, window',
             'desc': 'A simple, sunny private room at a student-friendly price. Everything you need to focus, nothing you don’t.'},
        ],
    },
]

all_rooms = []
for spec in PROPERTIES:
    prop = Property.objects.create(
        owner=spec['owner'], title=spec['title'], description=spec['description'],
        property_type=spec['type'], region=spec['region'], province=spec['province'],
        city=spec['city'], barangay=spec['barangay'], street_address=spec['street_address'],
        number_of_floors=spec['floors'], parking_available=spec['parking'],
        house_rules=spec['rules'], property_amenities=spec['amenities'],
        shared_facilities=spec['facilities'],
        status=Property.Status.APPROVED, is_published=True,
    )
    pimg = copy_image(spec['img'], f"properties/demo-{prop.id}.jpg")
    PropertyImage.objects.create(property=prop, image=pimg, is_main=True, caption=spec['title'])
    for r in spec['rooms']:
        room = Room.objects.create(
            property_listing=prop, name=r['name'], description=r['desc'],
            room_type=r['type'], monthly_rent=r['rent'], room_size=r['size'],
            furnished=r['furnished'], max_occupants=r['occupants'], bathroom_type=r['bath'],
            room_amenities=r['amenities'], availability=Room.Availability.AVAILABLE,
            available_from=date.today() + timedelta(days=7),
        )
        rimg = copy_image(r['img'], f"rooms/demo-{room.id}.jpg")
        RoomImage.objects.create(room=room, image=rimg, is_main=True, caption=r['name'])
        all_rooms.append(room)

# Demo activity for the renter: one accepted rental, one pending request, two saves.
accepted_room = next(r for r in all_rooms if r.name == "Garden View Master's")
pending_room = next(r for r in all_rooms if r.name == 'City-View Double Room')

Booking.objects.create(
    room=accepted_room, renter=renter, status=Booking.Status.ACCEPTED,
    message='Hi! I will be working in Davao for a year and would love a quiet room with a garden view.',
    move_in_date=date.today() + timedelta(days=14),
    requested_at=timezone.now() - timedelta(days=6),
    responded_at=timezone.now() - timedelta(days=4),
)
accepted_room.availability = Room.Availability.RESERVED
accepted_room.save(update_fields=['availability', 'updated_at'])

Booking.objects.create(
    room=pending_room, renter=renter, status=Booking.Status.PENDING,
    message='Hello! I work in Makati and would like to move in next month. May I schedule a visit this weekend?',
    move_in_date=date.today() + timedelta(days=30),
    requested_at=timezone.now() - timedelta(days=1),
)

for room in all_rooms[:2]:
    SavedListing.objects.get_or_create(renter=renter, room=room)

# A pending verification document so the admin queue has real content.
id_file = copy_image('images/rooms/room-6.jpg', 'verification_documents/demo-ana-id.jpg')
VerificationDocument.objects.create(
    user=ana, document_type='GOVERNMENT_ID', file=id_file, status='PENDING',
)

print(f'Seeded: {Property.objects.count()} properties, {Room.objects.count()} rooms, '
      f'{Booking.objects.count()} bookings, {SavedListing.objects.count()} saves.')
print('Demo password for all demo accounts: ' + DEMO_PASSWORD)