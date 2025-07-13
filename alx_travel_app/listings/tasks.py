from celery import shared_task
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_booking_confirmation_email(self, booking_id):
    """
    Send booking confirmation email to the customer
    
    Args:
        booking_id (str): UUID of the booking
        
    Returns:
        dict: Status of email sending
    """
    try:
        from .models import Booking
        
        # Get booking details
        booking = Booking.objects.select_related('listing', 'user').get(booking_id=booking_id)
        
        # Email context
        context = {
            'booking': booking,
            'customer_name': f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username,
            'listing_name': booking.listing.name,
            'location': booking.listing.location,
            'check_in_date': booking.check_in_date,
            'check_out_date': booking.check_out_date,
            'number_of_guests': booking.number_of_guests,
            'total_price': booking.total_price,
            'booking_id': booking.booking_id,
            'duration_nights': booking.duration_nights,
            'current_year': timezone.now().year,
        }
        
        # Email subject
        subject = f'Booking Confirmation - {booking.listing.name}'
        
        # Email body (plain text)
        message = f"""
Dear {context['customer_name']},

Your booking has been confirmed! Here are the details:

Booking ID: {booking.booking_id}
Property: {booking.listing.name}
Location: {booking.listing.location}
Check-in: {booking.check_in_date.strftime('%B %d, %Y')}
Check-out: {booking.check_out_date.strftime('%B %d, %Y')}
Guests: {booking.number_of_guests}
Total Amount: ${booking.total_price}

Thank you for choosing ALX Travel App!

Best regards,
ALX Travel Team
        """
        
        # Try to render HTML template if it exists
        html_message = None
        try:
            html_message = render_to_string('emails/booking_confirmation.html', context)
        except Exception as e:
            logger.warning(f"HTML template not found, sending plain text email: {str(e)}")
        
        # Send email
        success = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if success:
            logger.info(f"Booking confirmation email sent successfully for booking {booking_id}")
            return {
                'status': 'success',
                'message': f'Confirmation email sent to {booking.user.email}',
                'booking_id': str(booking_id)
            }
        else:
            logger.error(f"Failed to send booking confirmation email for booking {booking_id}")
            return {
                'status': 'failed',
                'message': 'Email sending failed',
                'booking_id': str(booking_id)
            }
            
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found")
        return {
            'status': 'failed',
            'message': f'Booking {booking_id} not found',
            'booking_id': str(booking_id)
        }
    except Exception as e:
        logger.error(f"Error sending booking confirmation email for {booking_id}: {str(e)}")
        # Retry the task
        raise self.retry(exc=e)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_booking_cancellation_email(self, booking_id):
    """
    Send booking cancellation email to the customer
    
    Args:
        booking_id (str): UUID of the booking
        
    Returns:
        dict: Status of email sending
    """
    try:
        from .models import Booking
        
        # Get booking details
        booking = Booking.objects.select_related('listing', 'user').get(booking_id=booking_id)
        
        # Email context
        context = {
            'booking': booking,
            'customer_name': f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username,
            'listing_name': booking.listing.name,
            'location': booking.listing.location,
            'check_in_date': booking.check_in_date,
            'check_out_date': booking.check_out_date,
            'booking_id': booking.booking_id,
            'current_year': timezone.now().year,
        }
        
        # Email subject
        subject = f'Booking Cancellation - {booking.listing.name}'
        
        # Email body (plain text)
        message = f"""
Dear {context['customer_name']},

Your booking has been cancelled. Here are the details:

Booking ID: {booking.booking_id}
Property: {booking.listing.name}
Location: {booking.listing.location}
Check-in Date: {booking.check_in_date.strftime('%B %d, %Y')}
Check-out Date: {booking.check_out_date.strftime('%B %d, %Y')}

If you have any questions, please contact our support team.

Best regards,
ALX Travel Team
        """
        
        # Try to render HTML template if it exists
        html_message = None
        try:
            html_message = render_to_string('emails/booking_cancellation.html', context)
        except Exception as e:
            logger.warning(f"HTML template not found, sending plain text email: {str(e)}")
        
        # Send email
        success = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if success:
            logger.info(f"Booking cancellation email sent successfully for booking {booking_id}")
            return {
                'status': 'success',
                'message': f'Cancellation email sent to {booking.user.email}',
                'booking_id': str(booking_id)
            }
        else:
            logger.error(f"Failed to send booking cancellation email for booking {booking_id}")
            return {
                'status': 'failed',
                'message': 'Email sending failed',
                'booking_id': str(booking_id)
            }
            
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found")
        return {
            'status': 'failed',
            'message': f'Booking {booking_id} not found',
            'booking_id': str(booking_id)
        }
    except Exception as e:
        logger.error(f"Error sending booking cancellation email for {booking_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_payment_confirmation_email(self, payment_id):
    """
    Send payment confirmation email to the customer
    
    Args:
        payment_id (str): UUID of the payment
        
    Returns:
        dict: Status of email sending
    """
    try:
        from .models import Payment
        
        # Get payment details
        payment = Payment.objects.select_related('booking', 'booking__listing', 'booking__user').get(payment_id=payment_id)
        booking = payment.booking
        
        # Email context
        context = {
            'payment': payment,
            'booking': booking,
            'customer_name': f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username,
            'listing_name': booking.listing.name,
            'location': booking.listing.location,
            'payment_id': payment.payment_id,
            'booking_id': booking.booking_id,
            'amount': payment.amount,
            'currency': payment.currency,
            'payment_method': payment.get_payment_method_display(),
            'payment_date': payment.payment_date,
            'current_year': timezone.now().year,
        }
        
        # Email subject
        subject = f'Payment Confirmation - {booking.listing.name}'
        
        # Email body (plain text)
        message = f"""
Dear {context['customer_name']},

Your payment has been successfully processed! Here are the details:

Payment ID: {payment.payment_id}
Booking ID: {booking.booking_id}
Amount Paid: {payment.amount} {payment.currency}
Payment Method: {payment.get_payment_method_display() if hasattr(payment, 'get_payment_method_display') else payment.payment_method}
Payment Date: {payment.payment_date.strftime('%B %d, %Y at %I:%M %p') if payment.payment_date else 'N/A'}

Property: {booking.listing.name}
Location: {booking.listing.location}

Your booking is now confirmed!

Thank you for choosing ALX Travel App!

Best regards,
ALX Travel Team
        """
        
        # Try to render HTML template if it exists
        html_message = None
        try:
            html_message = render_to_string('emails/payment_confirmation.html', context)
        except Exception as e:
            logger.warning(f"HTML template not found, sending plain text email: {str(e)}")
        
        # Send email
        success = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if success:
            logger.info(f"Payment confirmation email sent successfully for payment {payment_id}")
            return {
                'status': 'success',
                'message': f'Payment confirmation email sent to {booking.user.email}',
                'payment_id': str(payment_id)
            }
        else:
            logger.error(f"Failed to send payment confirmation email for payment {payment_id}")
            return {
                'status': 'failed',
                'message': 'Email sending failed',
                'payment_id': str(payment_id)
            }
            
    except Payment.DoesNotExist:
        logger.error(f"Payment {payment_id} not found")
        return {
            'status': 'failed',
            'message': f'Payment {payment_id} not found',
            'payment_id': str(payment_id)
        }
    except Exception as e:
        logger.error(f"Error sending payment confirmation email for {payment_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_host_notification_email(self, booking_id):
    """
    Send new booking notification email to the host
    
    Args:
        booking_id (str): UUID of the booking
        
    Returns:
        dict: Status of email sending
    """
    try:
        from .models import Booking
        
        # Get booking details
        booking = Booking.objects.select_related('listing', 'listing__host', 'user').get(booking_id=booking_id)
        host = booking.listing.host
        
        # Email context
        context = {
            'booking': booking,
            'host_name': f"{host.first_name} {host.last_name}".strip() or host.username,
            'guest_name': f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username,
            'listing_name': booking.listing.name,
            'check_in_date': booking.check_in_date,
            'check_out_date': booking.check_out_date,
            'number_of_guests': booking.number_of_guests,
            'total_price': booking.total_price,
            'booking_id': booking.booking_id,
            'duration_nights': booking.duration_nights,
            'current_year': timezone.now().year,
        }
        
        # Email subject
        subject = f'New Booking Received - {booking.listing.name}'
        
        # Email body (plain text)
        message = f"""
Dear {context['host_name']},

You have received a new booking for your property! Here are the details:

Booking ID: {booking.booking_id}
Property: {booking.listing.name}
Guest: {context['guest_name']}
Check-in: {booking.check_in_date.strftime('%B %d, %Y')}
Check-out: {booking.check_out_date.strftime('%B %d, %Y')}
Guests: {booking.number_of_guests}
Total Amount: ${booking.total_price}

Please ensure your property is ready for the guest's arrival.

Best regards,
ALX Travel Team
        """
        
        # Try to render HTML template if it exists
        html_message = None
        try:
            html_message = render_to_string('emails/host_notification.html', context)
        except Exception as e:
            logger.warning(f"HTML template not found, sending plain text email: {str(e)}")
        
        # Send email
        success = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[host.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if success:
            logger.info(f"Host notification email sent successfully for booking {booking_id}")
            return {
                'status': 'success',
                'message': f'Host notification email sent to {host.email}',
                'booking_id': str(booking_id)
            }
        else:
            logger.error(f"Failed to send host notification email for booking {booking_id}")
            return {
                'status': 'failed',
                'message': 'Email sending failed',
                'booking_id': str(booking_id)
            }
            
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found")
        return {
            'status': 'failed',
            'message': f'Booking {booking_id} not found',
            'booking_id': str(booking_id)
        }
    except Exception as e:
        logger.error(f"Error sending host notification email for {booking_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task
def cleanup_expired_bookings():
    """
    Periodic task to cleanup expired pending bookings
    This can be used with Celery Beat for scheduled execution
    """
    try:
        from .models import Booking
        from datetime import timedelta
        
        # Find bookings that are pending for more than 24 hours
        cutoff_time = timezone.now() - timedelta(hours=24)
        expired_bookings = Booking.objects.filter(
            status='payment_pending',
            created_at__lt=cutoff_time
        )
        
        count = expired_bookings.count()
        expired_bookings.update(status='cancelled')
        
        logger.info(f"Cleaned up {count} expired bookings")
        return {
            'status': 'success',
            'message': f'Cleaned up {count} expired bookings'
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up expired bookings: {str(e)}")
        return {
            'status': 'failed',
            'message': str(e)
        }


@shared_task
def send_reminder_emails():
    """
    Periodic task to send reminder emails for upcoming check-ins
    This can be used with Celery Beat for scheduled execution
    """
    try:
        from .models import Booking
        from datetime import timedelta
        
        # Find bookings with check-in tomorrow
        tomorrow = timezone.now().date() + timedelta(days=1)
        upcoming_bookings = Booking.objects.filter(
            status='confirmed',
            check_in_date=tomorrow
        ).select_related('listing', 'user')
        
        count = 0
        for booking in upcoming_bookings:
            # Send reminder email (you can create a separate task for this)
            send_booking_reminder_email.delay(str(booking.booking_id))
            count += 1
        
        logger.info(f"Sent {count} reminder emails")
        return {
            'status': 'success',
            'message': f'Sent {count} reminder emails'
        }
        
    except Exception as e:
        logger.error(f"Error sending reminder emails: {str(e)}")
        return {
            'status': 'failed',
            'message': str(e)
        }


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_booking_reminder_email(self, booking_id):
    """
    Send booking reminder email to the customer (day before check-in)
    
    Args:
        booking_id (str): UUID of the booking
        
    Returns:
        dict: Status of email sending
    """
    try:
        from .models import Booking
        
        # Get booking details
        booking = Booking.objects.select_related('listing', 'user').get(booking_id=booking_id)
        
        # Email context
        context = {
            'booking': booking,
            'customer_name': f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username,
            'listing_name': booking.listing.name,
            'location': booking.listing.location,
            'check_in_date': booking.check_in_date,
            'check_out_date': booking.check_out_date,
            'booking_id': booking.booking_id,
            'current_year': timezone.now().year,
        }
        
        # Email subject
        subject = f'Check-in Reminder - {booking.listing.name}'
        
        # Email body (plain text)
        message = f"""
Dear {context['customer_name']},

This is a friendly reminder that your check-in is tomorrow!

Booking Details:
Booking ID: {booking.booking_id}
Property: {booking.listing.name}
Location: {booking.listing.location}
Check-in: {booking.check_in_date.strftime('%B %d, %Y')}
Check-out: {booking.check_out_date.strftime('%B %d, %Y')}

Have a wonderful stay!

Best regards,
ALX Travel Team
        """
        
        # Try to render HTML template if it exists
        html_message = None
        try:
            html_message = render_to_string('emails/booking_reminder.html', context)
        except Exception as e:
            logger.warning(f"HTML template not found, sending plain text email: {str(e)}")
        
        # Send email
        success = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if success:
            logger.info(f"Booking reminder email sent successfully for booking {booking_id}")
            return {
                'status': 'success',
                'message': f'Reminder email sent to {booking.user.email}',
                'booking_id': str(booking_id)
            }
        else:
            logger.error(f"Failed to send booking reminder email for booking {booking_id}")
            return {
                'status': 'failed',
                'message': 'Email sending failed',
                'booking_id': str(booking_id)
            }
            
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found")
        return {
            'status': 'failed',
            'message': f'Booking {booking_id} not found',
            'booking_id': str(booking_id)
        }
    except Exception as e:
        logger.error(f"Error sending booking reminder email for {booking_id}: {str(e)}")
        raise self.retry(exc=e)