from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ListingViewSet, BookingViewSet, ReviewViewSet, PaymentViewSet, ChapaWebhookView

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'listings', ListingViewSet, basename='listing')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'payments', PaymentViewSet, basename='payment')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('api/', include(router.urls)),
    
    # Payment webhook endpoint
    path('api/payments/webhook/chapa/', ChapaWebhookView.as_view(), name='chapa-webhook'),
]