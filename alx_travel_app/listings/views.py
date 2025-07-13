from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json
import logging

from .models import Listing, Booking, Review, Payment
from .serializers import (
    ListingSerializer, BookingSerializer, ReviewSerializer, PaymentSerializer,
    BookingCreateResponseSerializer, PaymentStatusSerializer, 
    PaymentInitiateSerializer, PaymentVerifySerializer
)
from .services import ChapaPaymentService, create_payment_for_booking
from .tasks import (
    send_booking_confirmation_email, 
    send_booking_cancellation_email, 
    send_payment_confirmation_email,
    send_host_notification_email
)

logger = logging.getLogger(__name__)


class ListingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing travel listings.
    Provides CRUD operations for listings with additional filtering capabilities.
    """
    queryset = Listing.objects.all()
    serializer_class = ListingSerializer
    lookup_field = 'listing_id'

    def get_queryset(self):
        """
        Optionally restricts the returned listings by filtering against
        query parameters in the URL.
        """
        queryset = Listing.objects.all()
        
        # Filter by location
        location = self.request.query_params.get('location', None)
        if location is not None:
            queryset = queryset.filter(location__icontains=location)
        
        # Filter by property type
        property_type = self.request.query_params.get('property_type', None)
        if property_type is not None:
            queryset = queryset.filter(property_type=property_type)
        
        # Filter by availability
        available = self.request.query_params.get('available', None)
        if available is not None:
            available_bool = available.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(available=available_bool)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price', None)
        if min_price is not None:
            try:
                queryset = queryset.filter(price_per_night__gte=float(min_price))
            except ValueError:
                pass
        
        max_price = self.request.query_params.get('max_price', None)
        if max_price is not None:
            try:
                queryset = queryset.filter(price_per_night__lte=float(max_price))
            except ValueError:
                pass
        
        # Filter by number of guests
        guests = self.request.query_params.get('guests', None)
        if guests is not None:
            try:
                queryset = queryset.filter(max_guests__gte=int(guests))
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Set the host to the current user when creating a listing"""
        if self.request.user.is_authenticated:
            serializer.save(host=self.request.user)
        else:
            serializer.save()

    @swagger_auto_schema(
        method='get',
        manual_parameters=[
            openapi.Parameter('location', openapi.IN_QUERY, description="Filter by location", type=openapi.TYPE_STRING),
            openapi.Parameter('property_type', openapi.IN_QUERY, description="Filter by property type", type=openapi.TYPE_STRING),
            openapi.Parameter('available', openapi.IN_QUERY, description="Filter by availability", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('min_price', openapi.IN_QUERY, description="Minimum price per night", type=openapi.TYPE_NUMBER),
            openapi.Parameter('max_price', openapi.IN_QUERY, description="Maximum price per night", type=openapi.TYPE_NUMBER),
            openapi.Parameter('guests', openapi.IN_QUERY, description="Minimum number of guests", type=openapi.TYPE_INTEGER),
        ],
        responses={200: ListingSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Advanced search endpoint for listings with multiple filters
        """
        queryset = self.get_queryset()
        
        # Search in name and description
        search_query = request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(amenities__icontains=search_query)
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        responses={200: ReviewSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def reviews(self, request, listing_id=None):
        """
        Get all reviews for a specific listing
        """
        listing = self.get_object()
        reviews = listing.reviews.all().order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        responses={200: BookingSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def bookings(self, request, listing_id=None):
        """
        Get all bookings for a specific listing (for hosts)
        """
        listing = self.get_object()
        bookings = listing.bookings.all().order_by('-created_at')
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing bookings with integrated payment processing and email notifications.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    lookup_field = 'booking_id'

    def get_queryset(self):
        """
        Filter bookings based on query parameters
        """
        queryset = Booking.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter is not None:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by user (for guests to see their bookings)
        user_id = self.request.query_params.get('user_id', None)
        if user_id is not None:
            try:
                queryset = queryset.filter(user_id=int(user_id))
            except ValueError:
                pass
        
        # Filter by listing (for hosts to see bookings for their listings)
        listing_id = self.request.query_params.get('listing_id', None)
        if listing_id is not None:
            queryset = queryset.filter(listing__listing_id=listing_id)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Set the user to the current user when creating a booking"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    @swagger_auto_schema(
        request_body=BookingSerializer,
        responses={
            201: BookingCreateResponseSerializer,
            400: 'Bad Request'
        }
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new booking, initiate payment process, and send email notifications
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create booking
        booking = serializer.save()
        
        try:
            # Get payment and initiate with Chapa
            payment = booking.payment
            chapa_service = ChapaPaymentService()
            chapa_response = chapa_service.initiate_payment(payment)
            
            # Send email notifications asynchronously
            try:
                # Send booking confirmation email to customer
                send_booking_confirmation_email.delay(str(booking.booking_id))
                logger.info(f"Booking confirmation email task queued for booking {booking.booking_id}")
                
                # Send notification email to host
                send_host_notification_email.delay(str(booking.booking_id))
                logger.info(f"Host notification email task queued for booking {booking.booking_id}")
                
            except Exception as email_error:
                # Log email error but don't fail the booking creation
                logger.warning(f"Failed to queue email tasks for booking {booking.booking_id}: {str(email_error)}")
            
            # Prepare response
            response_data = {
                'booking': BookingSerializer(booking).data,
                'payment_url': payment.chapa_checkout_url,
                'payment_id': payment.payment_id,
                'message': 'Booking created successfully. Please complete payment to confirm your booking. Confirmation emails have been sent.'
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # If payment initiation fails, update booking status
            booking.status = 'payment_failed'
            booking.save()
            
            logger.error(f"Payment initiation failed for booking {booking.booking_id}: {str(e)}")
            
            return Response({
                'error': 'Booking created but payment initiation failed',
                'details': str(e),
                'booking_id': str(booking.booking_id)
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

    @swagger_auto_schema(
        method='patch',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['pending', 'confirmed', 'cancelled', 'completed'],
                    description='New booking status'
                )
            }
        ),
        responses={200: BookingSerializer}
    )
    @action(detail=True, methods=['patch'])
    def update_status(self, request, booking_id=None):
        """
        Update booking status with email notifications
        """
        booking = self.get_object()
        new_status = request.data.get('status')
        old_status = booking.status
        
        valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed', 'payment_pending', 'payment_failed']
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        booking.status = new_status
        booking.save()
        
        # Send email notifications for certain status changes
        try:
            if new_status == 'confirmed' and old_status != 'confirmed':
                send_booking_confirmation_email.delay(str(booking.booking_id))
                logger.info(f"Booking confirmation email task queued for status update: {booking.booking_id}")
            
            elif new_status == 'cancelled' and old_status != 'cancelled':
                send_booking_cancellation_email.delay(str(booking.booking_id))
                logger.info(f"Booking cancellation email task queued for status update: {booking.booking_id}")
                
        except Exception as email_error:
            logger.warning(f"Failed to queue email tasks for booking status update {booking.booking_id}: {str(email_error)}")
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @swagger_auto_schema(
        method='post',
        responses={200: BookingSerializer}
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, booking_id=None):
        """
        Cancel a booking with email notification
        """
        booking = self.get_object()
        
        if booking.status == 'completed':
            return Response(
                {'error': 'Cannot cancel a completed booking'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if booking.status == 'cancelled':
            return Response(
                {'error': 'Booking is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = booking.status
        booking.status = 'cancelled'
        booking.save()
        
        # Cancel payment if exists
        try:
            payment = booking.payment
            if payment.status in ['pending', 'processing']:
                payment.status = 'cancelled'
                payment.save()
        except Payment.DoesNotExist:
            pass
        
        # Send cancellation email
        try:
            send_booking_cancellation_email.delay(str(booking.booking_id))
            logger.info(f"Booking cancellation email task queued for cancellation: {booking.booking_id}")
        except Exception as email_error:
            logger.warning(f"Failed to queue cancellation email task for booking {booking.booking_id}: {str(email_error)}")
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)

    @swagger_auto_schema(
        responses={200: PaymentStatusSerializer}
    )
    @action(detail=True, methods=['get'])
    def payment_status(self, request, booking_id=None):
        """
        Get payment status for a booking
        """
        booking = self.get_object()
        
        try:
            payment = booking.payment
            chapa_service = ChapaPaymentService()
            payment_status = chapa_service.get_payment_status(str(payment.payment_id))
            return Response(payment_status)
            
        except Payment.DoesNotExist:
            return Response(
                {'error': 'No payment found for this booking'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing payments (read-only)
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    lookup_field = 'payment_id'

    def get_queryset(self):
        """Filter payments based on query parameters"""
        queryset = Payment.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by booking
        booking_id = self.request.query_params.get('booking_id', None)
        if booking_id:
            queryset = queryset.filter(booking__booking_id=booking_id)
        
        return queryset.order_by('-created_at')

    @swagger_auto_schema(
        request_body=PaymentInitiateSerializer,
        responses={200: 'Payment initiated successfully'}
    )
    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """
        Initiate payment for a booking
        """
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        booking_id = serializer.validated_data['booking_id']
        customer_phone = serializer.validated_data.get('customer_phone')
        
        try:
            booking = Booking.objects.get(booking_id=booking_id)
            
            # Check if payment already exists
            if hasattr(booking, 'payment'):
                payment = booking.payment
                if payment.status in ['completed']:
                    return Response(
                        {'error': 'Payment already completed for this booking'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Create payment if it doesn't exist
                payment = create_payment_for_booking(booking, customer_phone)
            
            # Initiate payment with Chapa
            chapa_service = ChapaPaymentService()
            chapa_response = chapa_service.initiate_payment(payment)
            
            return Response({
                'message': 'Payment initiated successfully',
                'payment_id': str(payment.payment_id),
                'checkout_url': payment.chapa_checkout_url,
                'tx_ref': payment.chapa_reference
            })
            
        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Payment initiation error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        request_body=PaymentVerifySerializer,
        responses={200: PaymentStatusSerializer}
    )
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """
        Verify payment with Chapa and send confirmation email
        """
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tx_ref = serializer.validated_data['tx_ref']
        
        try:
            # Find payment by reference
            payment = Payment.objects.get(chapa_reference=tx_ref)
            
            # Verify with Chapa
            chapa_service = ChapaPaymentService()
            verification_response = chapa_service.verify_payment(tx_ref)
            
            # Update payment status
            chapa_service.update_payment_status(payment, verification_response)
            
            # Send payment confirmation email if payment is successful
            if payment.is_successful:
                try:
                    send_payment_confirmation_email.delay(str(payment.payment_id))
                    logger.info(f"Payment confirmation email task queued for payment {payment.payment_id}")
                except Exception as email_error:
                    logger.warning(f"Failed to queue payment confirmation email for payment {payment.payment_id}: {str(email_error)}")
            
            # Return updated status
            payment_status = chapa_service.get_payment_status(str(payment.payment_id))
            return Response(payment_status)
            
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class ChapaWebhookView(APIView):
    """
    Handle webhook notifications from Chapa with email notifications
    """
    
    def post(self, request):
        """
        Process webhook notification from Chapa
        """
        try:
            # Parse webhook data
            webhook_data = request.data
            
            logger.info(f"Received Chapa webhook: {webhook_data}")
            
            # Handle webhook with Chapa service
            chapa_service = ChapaPaymentService()
            payment = chapa_service.handle_webhook(webhook_data)
            
            if payment:
                logger.info(f"Webhook processed successfully for payment {payment.payment_id}")
                
                # Send confirmation email if payment completed
                if payment.is_successful:
                    try:
                        send_payment_confirmation_email.delay(str(payment.payment_id))
                        logger.info(f"Payment confirmation email task queued from webhook for payment {payment.payment_id}")
                    except Exception as email_error:
                        logger.warning(f"Failed to queue payment confirmation email from webhook for payment {payment.payment_id}: {str(email_error)}")
                
                return Response({'status': 'success'})
            else:
                logger.warning("Webhook processing failed - payment not found or error occurred")
                return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return Response({'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing reviews.
    Provides CRUD operations for reviews.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    lookup_field = 'review_id'

    def get_queryset(self):
        """
        Filter reviews based on query parameters
        """
        queryset = Review.objects.all()
        
        # Filter by listing
        listing_id = self.request.query_params.get('listing_id', None)
        if listing_id is not None:
            queryset = queryset.filter(listing__listing_id=listing_id)
        
        # Filter by user
        user_id = self.request.query_params.get('user_id', None)
        if user_id is not None:
            try:
                queryset = queryset.filter(user_id=int(user_id))
            except ValueError:
                pass
        
        # Filter by rating
        min_rating = self.request.query_params.get('min_rating', None)
        if min_rating is not None:
            try:
                queryset = queryset.filter(rating__gte=int(min_rating))
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Set the user to the current user when creating a review"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()