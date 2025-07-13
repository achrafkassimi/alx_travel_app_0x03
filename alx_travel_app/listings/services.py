import requests
import json
import logging
from django.conf import settings
from django.core.exceptions import ValidationError
from typing import Dict, Any, Optional
from .models import Payment, Booking

logger = logging.getLogger(__name__)


class ChapaPaymentService:
    """
    Service class for handling Chapa payment integration
    """
    
    def __init__(self):
        self.secret_key = getattr(settings, 'CHAPA_SECRET_KEY', None)
        self.base_url = getattr(settings, 'CHAPA_BASE_URL', 'https://api.chapa.co/v1')
        self.webhook_url = getattr(settings, 'CHAPA_WEBHOOK_URL', None)
        
        if not self.secret_key:
            raise ValidationError("CHAPA_SECRET_KEY not found in settings")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Chapa API requests"""
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to Chapa API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request payload
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If request fails
        """
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Chapa API request failed: {str(e)}")
            raise Exception(f"Payment service error: {str(e)}")
    
    def initiate_payment(self, payment: Payment) -> Dict[str, Any]:
        """
        Initiate payment with Chapa
        
        Args:
            payment: Payment model instance
            
        Returns:
            Response data from Chapa API
        """
        booking = payment.booking
        
        # Prepare payment data
        payment_data = {
            'amount': str(payment.amount),
            'currency': payment.currency,
            'email': payment.customer_email,
            'first_name': payment.customer_name.split(' ')[0] if payment.customer_name else 'Guest',
            'last_name': ' '.join(payment.customer_name.split(' ')[1:]) if len(payment.customer_name.split(' ')) > 1 else '',
            'phone_number': payment.customer_phone or '',
            'tx_ref': payment.chapa_reference,
            'callback_url': f"{settings.FRONTEND_URL}/payment/callback/{payment.payment_id}/",
            'return_url': f"{settings.FRONTEND_URL}/booking/{booking.booking_id}/",
            'description': f"Payment for booking {booking.booking_id} - {booking.listing.name}",
            'meta': {
                'booking_id': str(booking.booking_id),
                'payment_id': str(payment.payment_id),
                'listing_name': booking.listing.name,
                'customer_id': str(booking.user.id),
            }
        }
        
        # Add webhook URL if configured
        if self.webhook_url:
            payment_data['webhook'] = self.webhook_url
        
        try:
            response = self._make_request('POST', 'transaction/initialize', payment_data)
            
            # Update payment with Chapa response
            if response.get('status') == 'success':
                payment.chapa_checkout_url = response['data']['checkout_url']
                payment.status = 'processing'
                payment.save()
                
                logger.info(f"Payment initiated successfully for booking {booking.booking_id}")
                return response
            else:
                payment.status = 'failed'
                payment.failure_reason = response.get('message', 'Unknown error')
                payment.save()
                
                logger.error(f"Payment initiation failed for booking {booking.booking_id}: {response}")
                raise Exception(f"Payment initiation failed: {response.get('message', 'Unknown error')}")
                
        except Exception as e:
            payment.status = 'failed'
            payment.failure_reason = str(e)
            payment.save()
            raise
    
    def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        """
        Verify payment status with Chapa
        
        Args:
            tx_ref: Transaction reference
            
        Returns:
            Payment verification response
        """
        try:
            response = self._make_request('GET', f'transaction/verify/{tx_ref}')
            
            if response.get('status') == 'success':
                logger.info(f"Payment verification successful for tx_ref: {tx_ref}")
                return response
            else:
                logger.error(f"Payment verification failed for tx_ref: {tx_ref}")
                return response
                
        except Exception as e:
            logger.error(f"Payment verification error for tx_ref {tx_ref}: {str(e)}")
            raise
    
    def update_payment_status(self, payment: Payment, verification_data: Dict[str, Any]) -> None:
        """
        Update payment status based on verification response
        
        Args:
            payment: Payment model instance
            verification_data: Response from payment verification
        """
        try:
            data = verification_data.get('data', {})
            status = data.get('status', '').lower()
            
            # Map Chapa status to our payment status
            status_mapping = {
                'success': 'completed',
                'failed': 'failed',
                'pending': 'processing',
                'cancelled': 'cancelled',
            }
            
            payment.status = status_mapping.get(status, 'failed')
            payment.chapa_transaction_id = data.get('id')
            payment.payment_method = self._get_payment_method(data.get('method'))
            payment.webhook_data = verification_data
            
            if payment.status == 'completed':
                payment.payment_date = data.get('created_at')
                # Update booking status
                booking = payment.booking
                booking.status = 'confirmed'
                booking.save()
                
                logger.info(f"Payment completed for booking {booking.booking_id}")
                
            elif payment.status == 'failed':
                payment.failure_reason = data.get('failure_reason', 'Payment failed')
                # Update booking status
                booking = payment.booking
                booking.status = 'payment_failed'
                booking.save()
                
                logger.warning(f"Payment failed for booking {booking.booking_id}")
            
            payment.save()
            
        except Exception as e:
            logger.error(f"Error updating payment status: {str(e)}")
            raise
    
    def _get_payment_method(self, chapa_method: str) -> str:
        """
        Map Chapa payment method to our payment method choices
        
        Args:
            chapa_method: Payment method from Chapa
            
        Returns:
            Mapped payment method
        """
        method_mapping = {
            'telebirr': 'mobile',
            'cbebirr': 'mobile',
            'ebirr': 'mobile',
            'mpesa': 'mobile',
            'visa': 'card',
            'mastercard': 'card',
            'amex': 'card',
            'bank': 'bank',
        }
        
        if chapa_method:
            return method_mapping.get(chapa_method.lower(), 'mobile')
        return 'mobile'
    
    def handle_webhook(self, webhook_data: Dict[str, Any]) -> Optional[Payment]:
        """
        Handle webhook notification from Chapa
        
        Args:
            webhook_data: Webhook payload from Chapa
            
        Returns:
            Updated Payment instance or None
        """
        try:
            tx_ref = webhook_data.get('tx_ref')
            if not tx_ref:
                logger.error("No tx_ref in webhook data")
                return None
            
            # Find payment by reference
            try:
                payment = Payment.objects.get(chapa_reference=tx_ref)
            except Payment.DoesNotExist:
                logger.error(f"Payment not found for tx_ref: {tx_ref}")
                return None
            
            # Verify payment with Chapa API
            verification_response = self.verify_payment(tx_ref)
            
            # Update payment status
            self.update_payment_status(payment, verification_response)
            
            return payment
            
        except Exception as e:
            logger.error(f"Webhook handling error: {str(e)}")
            return None
    
    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Get current payment status
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Payment status information
        """
        try:
            payment = Payment.objects.get(payment_id=payment_id)
            
            # If payment is still processing, check with Chapa
            if payment.status in ['pending', 'processing']:
                verification_response = self.verify_payment(payment.chapa_reference)
                self.update_payment_status(payment, verification_response)
                payment.refresh_from_db()
            
            return {
                'payment_id': str(payment.payment_id),
                'status': payment.status,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'checkout_url': payment.chapa_checkout_url,
                'booking_id': str(payment.booking.booking_id),
                'created_at': payment.created_at.isoformat(),
                'updated_at': payment.updated_at.isoformat(),
            }
            
        except Payment.DoesNotExist:
            raise Exception(f"Payment not found: {payment_id}")
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            raise


# Utility function to create payment for booking
def create_payment_for_booking(booking: Booking, customer_phone: Optional[str] = None) -> Payment:
    """
    Create payment record for a booking
    
    Args:
        booking: Booking instance
        customer_phone: Optional customer phone number
        
    Returns:
        Created Payment instance
    """
    payment = Payment.objects.create(
        booking=booking,
        amount=booking.total_price,
        currency='MAD',  # Default to Ethiopian Birr
        customer_email=booking.user.email,
        customer_phone=customer_phone,
        customer_name=f"{booking.user.first_name} {booking.user.last_name}".strip() or booking.user.username,
    )
    
    return payment