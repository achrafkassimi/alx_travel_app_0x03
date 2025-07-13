from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random
from listings.models import Listing, Booking, Review


class Command(BaseCommand):
    help = 'Seed the database with sample travel listings, bookings, and reviews'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create'
        )
        parser.add_argument(
            '--listings',
            type=int,
            default=20,
            help='Number of listings to create'
        )
        parser.add_argument(
            '--bookings',
            type=int,
            default=30,
            help='Number of bookings to create'
        )
        parser.add_argument(
            '--reviews',
            type=int,
            default=25,
            help='Number of reviews to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            Review.objects.all().delete()
            Booking.objects.all().delete()
            Listing.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('✓ Existing data cleared'))

        # Create users
        users = self.create_users(options['users'])
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(users)} users'))

        # Create listings
        listings = self.create_listings(users, options['listings'])
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(listings)} listings'))

        # Create bookings
        bookings = self.create_bookings(users, listings, options['bookings'])
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(bookings)} bookings'))

        # Create reviews
        reviews = self.create_reviews(users, listings, bookings, options['reviews'])
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(reviews)} reviews'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Successfully seeded database with:\n'
                f'   - {len(users)} users\n'
                f'   - {len(listings)} listings\n'
                f'   - {len(bookings)} bookings\n'
                f'   - {len(reviews)} reviews'
            )
        )

    def create_users(self, count):
        """Create sample users"""
        users = []
        
        # Sample user data
        first_names = [
            'John', 'Jane', 'Michael', 'Sarah', 'David', 'Emily', 'Robert', 'Lisa',
            'James', 'Maria', 'William', 'Jennifer', 'Richard', 'Linda', 'Charles'
        ]
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
            'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez'
        ]
        
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}{last_name.lower()}{i+1}"
            email = f"{username}@example.com"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'is_active': True
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                users.append(user)
        
        return users

    def create_listings(self, users, count):
        """Create sample listings"""
        listings = []
        
        # Sample listing data
        property_types = ['hotel', 'apartment', 'house', 'villa', 'resort', 'hostel']
        
        locations = [
            'Paris, France', 'Tokyo, Japan', 'New York, USA', 'London, UK',
            'Sydney, Australia', 'Rome, Italy', 'Barcelona, Spain', 'Amsterdam, Netherlands',
            'Bangkok, Thailand', 'Dubai, UAE', 'Singapore', 'Los Angeles, USA',
            'Berlin, Germany', 'Prague, Czech Republic', 'Istanbul, Turkey'
        ]
        
        names = [
            'Luxury Downtown Apartment', 'Cozy Beachfront Villa', 'Modern City Loft',
            'Historic Boutique Hotel', 'Spacious Family House', 'Charming Garden Cottage',
            'Penthouse with City Views', 'Rustic Mountain Cabin', 'Elegant Studio',
            'Seaside Resort Suite', 'Urban Design Hotel', 'Traditional Townhouse',
            'Contemporary Flat', 'Romantic Getaway', 'Business Travel Suite'
        ]
        
        amenities_list = [
            'WiFi, Air Conditioning, Kitchen',
            'Pool, Gym, Spa, Concierge',
            'Parking, Balcony, Washing Machine',
            'Ocean View, Private Beach, Restaurant',
            'City Center, Metro Access, Rooftop Terrace',
            'Garden, BBQ, Pet Friendly',
            'Business Center, Meeting Room, Airport Shuttle'
        ]
        
        descriptions = [
            'A beautiful and comfortable place to stay with all modern amenities.',
            'Perfect for families and groups looking for a relaxing vacation.',
            'Ideal location for business travelers and tourists alike.',
            'Stunning views and luxury accommodations in the heart of the city.',
            'Cozy and welcoming space with traditional charm and modern comfort.',
            'Experience the best of local culture in this authentic accommodation.'
        ]
        
        for i in range(count):
            listing = Listing.objects.create(
                host=random.choice(users),
                name=f"{random.choice(names)} {i+1}",
                description=random.choice(descriptions),
                location=random.choice(locations),
                price_per_night=Decimal(str(random.randint(50, 500))),
                property_type=random.choice(property_types),
                max_guests=random.randint(1, 8),
                bedrooms=random.randint(1, 4),
                bathrooms=random.randint(1, 3),
                amenities=random.choice(amenities_list),
                available=random.choice([True, True, True, False])  # 75% available
            )
            listings.append(listing)
        
        return listings

    def create_bookings(self, users, listings, count):
        """Create sample bookings"""
        bookings = []
        
        # Get only available listings
        available_listings = [l for l in listings if l.available]
        
        if not available_listings:
            self.stdout.write(self.style.WARNING('No available listings found, skipping bookings'))
            return []
        
        statuses = ['pending', 'confirmed', 'completed', 'cancelled']
        status_weights = [0.1, 0.4, 0.4, 0.1]  # Most bookings are confirmed or completed
        
        for i in range(count):
            listing = random.choice(available_listings)
            user = random.choice([u for u in users if u != listing.host])  # Guest can't be the host
            
            # Generate random dates
            start_date = date.today() + timedelta(days=random.randint(-90, 90))
            duration = random.randint(1, 14)  # 1-14 nights
            end_date = start_date + timedelta(days=duration)
            
            # Ensure dates are valid
            if start_date >= end_date:
                continue
            
            try:
                booking = Booking.objects.create(
                    listing=listing,
                    user=user,
                    check_in_date=start_date,
                    check_out_date=end_date,
                    number_of_guests=random.randint(1, min(listing.max_guests, 6)),
                    total_price=listing.price_per_night * duration,
                    status=random.choices(statuses, weights=status_weights)[0],
                    special_requests=random.choice([
                        '', '', '',  # Most bookings have no special requests
                        'Early check-in please',
                        'Late check-out if possible',
                        'Extra towels needed',
                        'Quiet room preferred'
                    ])
                )
                bookings.append(booking)
            except Exception as e:
                # Skip if there's a conflict
                continue
        
        return bookings

    def create_reviews(self, users, listings, bookings, count):
        """Create sample reviews"""
        reviews = []
        
        # Get completed bookings for realistic reviews
        completed_bookings = [b for b in bookings if b.status == 'completed']
        
        if not completed_bookings:
            self.stdout.write(self.style.WARNING('No completed bookings found, creating reviews without bookings'))
            completed_bookings = bookings[:count] if bookings else []
        
        comments = [
            "Amazing place! Highly recommended for anyone visiting the area.",
            "Great location and very clean. The host was very responsive.",
            "Perfect for our family vacation. Kids loved it!",
            "Exactly as described. Would definitely book again.",
            "Beautiful apartment with stunning views.",
            "Very comfortable and well-equipped. Great value for money.",
            "The location was perfect for exploring the city.",
            "Host was very welcoming and gave great local recommendations.",
            "Clean, comfortable, and exactly what we needed.",
            "Excellent communication from the host. Smooth check-in process.",
            "Good place but could use some improvements.",
            "Outstanding service and beautiful property.",
            "Convenient location with easy access to public transport.",
            "Cozy and comfortable. Felt like home away from home.",
            "Great amenities and very well maintained.",
            "Peaceful and quiet neighborhood. Perfect for relaxation.",
            "Modern and stylish interior. Very Instagram-worthy!",
            "Host went above and beyond to make our stay comfortable.",
            "Good value for the price. Would recommend to friends.",
            "Nice place overall, minor issues but nothing major."
        ]
        
        # Create reviews for completed bookings first
        for booking in completed_bookings[:count]:
            try:
                review = Review.objects.create(
                    listing=booking.listing,
                    user=booking.user,
                    booking=booking,
                    rating=random.choices(
                        [1, 2, 3, 4, 5],
                        weights=[0.05, 0.05, 0.15, 0.35, 0.4]  # Mostly positive reviews
                    )[0],
                    comment=random.choice(comments)
                )
                reviews.append(review)
            except Exception as e:
                # Skip if review already exists
                continue
        
        # Create additional reviews without specific bookings if needed
        remaining_count = count - len(reviews)
        if remaining_count > 0 and listings:
            for i in range(remaining_count):
                listing = random.choice(listings)
                # Make sure user is not the host
                available_users = [u for u in users if u != listing.host]
                if not available_users:
                    continue
                
                user = random.choice(available_users)
                
                try:
                    review = Review.objects.create(
                        listing=listing,
                        user=user,
                        rating=random.choices(
                            [1, 2, 3, 4, 5],
                            weights=[0.05, 0.05, 0.15, 0.35, 0.4]
                        )[0],
                        comment=random.choice(comments)
                    )
                    reviews.append(review)
                except Exception as e:
                    # Skip if review already exists (unique constraint)
                    continue
        
        return reviews