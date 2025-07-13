from django.contrib import admin
from .models import Listing, Booking, Review


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'property_type', 'price_per_night', 'available', 'created_at']
    list_filter = ['property_type', 'available', 'location']
    search_fields = ['name', 'location', 'description']
    readonly_fields = ['listing_id', 'created_at', 'updated_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['booking_id', 'listing', 'user', 'check_in_date', 'check_out_date', 'status']
    list_filter = ['status', 'check_in_date', 'check_out_date']
    search_fields = ['listing__name', 'user__username']
    readonly_fields = ['booking_id', 'created_at', 'updated_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['review_id', 'listing', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['listing__name', 'user__username', 'comment']
    readonly_fields = ['review_id', 'created_at', 'updated_at']