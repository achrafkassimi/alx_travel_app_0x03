from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta
from .models import Listing, Booking, Review


class ListingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testhost',
            email='host@test.com',
            password='testpass123'
        )
        
    def test_listing_creation(self):
        listing = Listing.objects.create(
            host=self.user,
            name='Test Apartment',
            description='A nice test apartment',
            location='Test City',
            price_per_night=Decimal('100.00'),
            property_type='apartment',
            max_guests=4,
            bedrooms=2,
            bathrooms=1
        )
        self.assertEqual(listing.name, 'Test Apartment')
        self.assertEqual(listing.host, self.user)
        self.assertTrue(listing.available)


class BookingModelTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username='testhost',
            email='host@test.com',
            password='testpass123'
        )
        self.guest = User.objects.create_user(
            username='testguest',
            email='guest@test.com',
            password='testpass123'
        )
        self.listing = Listing.objects.create(
            host=self.host,
            name='Test Apartment',
            description='A nice test apartment',
            location='Test City',
            price_per_night=Decimal('100.00'),
            max_guests=4
        )
        
    def test_booking_creation(self):
        booking = Booking.objects.create(
            listing=self.listing,
            user=self.guest,
            check_in_date=date.today() + timedelta(days=1),
            check_out_date=date.today() + timedelta(days=3),
            number_of_guests=2,
            total_price=Decimal('200.00')
        )
        self.assertEqual(booking.listing, self.listing)
        self.assertEqual(booking.user, self.guest)
        self.assertEqual(booking.duration_nights, 2)


class ReviewModelTest(TestCase):
    def setUp(self):
        self.host = User.objects.create_user(
            username='testhost',
            email='host@test.com',
            password='testpass123'
        )
        self.guest = User.objects.create_user(
            username='testguest',
            email='guest@test.com',
            password='testpass123'
        )
        self.listing = Listing.objects.create(
            host=self.host,
            name='Test Apartment',
            description='A nice test apartment',
            location='Test City',
            price_per_night=Decimal('100.00'),
            max_guests=4
        )
        
    def test_review_creation(self):
        review = Review.objects.create(
            listing=self.listing,
            user=self.guest,
            rating=5,
            comment='Great place to stay!'
        )
        self.assertEqual(review.listing, self.listing)
        self.assertEqual(review.user, self.guest)
        self.assertEqual(review.rating, 5)