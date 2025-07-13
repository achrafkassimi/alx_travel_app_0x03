# Generated migration for adding Payment model and updating Booking model

import django.core.validators
import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('listings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'), 
                    ('confirmed', 'Confirmed'), 
                    ('cancelled', 'Cancelled'), 
                    ('completed', 'Completed'), 
                    ('payment_pending', 'Payment Pending'), 
                    ('payment_failed', 'Payment Failed')
                ], 
                default='payment_pending', 
                help_text='Current status of the booking', 
                max_length=20
            ),
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('payment_id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique identifier for the payment', primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Payment amount in ETB (Ethiopian Birr)', max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('currency', models.CharField(default='ETB', help_text='Payment currency', max_length=3)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded')], default='pending', help_text='Current payment status', max_length=20)),
                ('payment_method', models.CharField(blank=True, choices=[('mobile', 'Mobile Money'), ('card', 'Credit/Debit Card'), ('bank', 'Bank Transfer')], help_text='Payment method used', max_length=20, null=True)),
                ('chapa_transaction_id', models.CharField(blank=True, help_text='Transaction ID from Chapa', max_length=100, null=True)),
                ('chapa_checkout_url', models.URLField(blank=True, help_text='Chapa checkout URL for payment', null=True)),
                ('chapa_reference', models.CharField(help_text='Unique reference for Chapa transaction', max_length=100, unique=True)),
                ('customer_email', models.EmailField(help_text='Customer email address')),
                ('customer_phone', models.CharField(blank=True, help_text='Customer phone number', max_length=20, null=True)),
                ('customer_name', models.CharField(help_text='Customer full name', max_length=100)),
                ('payment_date', models.DateTimeField(blank=True, help_text='When the payment was completed', null=True)),
                ('failure_reason', models.TextField(blank=True, help_text='Reason for payment failure', null=True)),
                ('webhook_data', models.JSONField(blank=True, help_text='Raw webhook data from Chapa', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When the payment record was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When the payment record was last updated')),
                ('booking', models.OneToOneField(help_text='The booking this payment is for', on_delete=django.db.models.deletion.CASCADE, related_name='payment', to='listings.booking')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['status'], name='listings_pa_status_8c3d12_idx'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['chapa_transaction_id'], name='listings_pa_chapa_t_4f2a85_idx'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['chapa_reference'], name='listings_pa_chapa_r_7b8c94_idx'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['created_at'], name='listings_pa_created_9e1f73_idx'),
        ),
    ]