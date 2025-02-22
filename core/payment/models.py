from django.db import models
from django.conf import settings
from ecommerce.models import Order,OrderItem

class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    class PaymentProvider(models.TextChoices):
        IYZICO = "IYZICO", "Iyzico"
        STRIPE = "STRIPE", "Stripe"
        PAYPAL = "PAYPAL", "PayPal"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE,related_name='payment_items',null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='TRY')
    provider = models.CharField(
        max_length=10,
        choices=PaymentProvider.choices,
        default=PaymentProvider.IYZICO
    )
    status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    provider_token = models.CharField(max_length=100, blank=True, null=True)
    provider_transaction_id = models.CharField(max_length=255, null=True, blank=True)
    provider_payment_id = models.CharField(max_length=255, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.id} - {self.status}"
