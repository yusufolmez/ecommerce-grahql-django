import iyzipay
import logging
from django.conf import settings
from django.core.exceptions import PermissionDenied
import json
from django.db import transaction
from ecommerce.models import Order
from .models import Payment

logger = logging.getLogger(__name__)

class IyzicoPaymentService:
    def __init__(self):
        self.options = {
            'api_key': settings.IYZICO_API_KEY,
            'secret_key': settings.IYZICO_SECRET_KEY,
            'base_url': settings.IYZICO_BASE_URL
        }

    def create_payment_form(self, payment, user, callback_url):
        if payment.status == 'COMPLETED':
            return {    
            'status': 'error',
            'error_message': 'Payment has already been completed for this order.'
            }
        buyer = {
            'id': str(user.id),
            'name': user.first_name,
            'surname': user.last_name,
            'email': user.email,
            'identityNumber': '11111111111',
            'registrationAddress': payment.order.shipping_address.street,
            'city': payment.order.shipping_address.city,
            'country': "Turkey",
            'ip': "85.34.78.112"
        }

        address = {
            'contactName': f"{user.first_name} {user.last_name}",
            'city': payment.order.shipping_address.city,
            'country': "Turkey",
            'address': payment.order.shipping_address.street
        }
        basket_items = []
        for order_item in payment.order.items.all():
            basket_items.append({
                'id': str(order_item.id),
                'name': f"{order_item.product_variant.product.product_name} - {order_item.product_variant.variants}",  
                'category1': order_item.product_variant.product.product_category.category_name,  
                'category2': order_item.product_variant.product.product_category.parent_category.category_name if order_item.product_variant.product.product_category.parent_category else '',  # Alt kategori
                'itemType': 'PHYSICAL', 
                'price': str(order_item.unit_price * order_item.quantity)  
            })
        metadata = {
            'order_id': payment.order.id,
            'payment_id': payment.id,
        }

        request = {
            'locale': 'tr',
            'conversationId': str(payment.order.id),
            'price': str(payment.amount),
            'paidPrice': str(payment.amount),
            'currency': payment.currency,
            'basketId': str(payment.order.id),
            'paymentGroup': 'PRODUCT',
            "callbackUrl": callback_url,
            "enabledInstallments": ['2', '3', '6', '9'],
            'buyer': buyer,
            'shippingAddress': address,
            'billingAddress': address,
            'basketItems': basket_items,
            'metadata':metadata,
        }

        checkout_form_initialize = iyzipay.CheckoutFormInitialize().create(request, self.options)
        response_data = checkout_form_initialize.read().decode("utf-8")
        result = json.loads(response_data)


        if result.get('status') == 'success':

            payment.provider_token = result.get('token')
            payment.save()

            return {
                'status': 'success',
                'token': result.get('token'),
                'checkoutFormContent': result.get('checkoutFormContent'),
                'tokenExpireTime': 1800
            }
        else:
            return {
                'status': 'error',
                'error_message': result.get('errorMessage', 'Payment failed.')
            }




    def verify_payment(self, token):
        request = {
            'locale': 'tr',
            'token': token,
        }

        checkout_form_result = iyzipay.CheckoutForm().retrieve(request, self.options)
        result = json.loads(checkout_form_result.read().decode("utf-8"))

        order_id = result.get('basketId')
        if not order_id:
            return {
                'status': 'error',
                'error_message': 'Order ID not found in response'
            }

        try:
            order = Order.objects.get(id=order_id)
            payment = order.payment
            print(json.dumps(result, indent=4))
            payment.provider_transaction_id = result.get('itemTransactions', [{}])[0].get('paymentTransactionId', None)
            print(payment.provider_transaction_id)
            payment_id = result.get('paymentId')
        except Order.DoesNotExist:
            return {
                'status': 'error',
                'error_message': 'Order not found'
            }

        return {
            'status': 'success',
            'payment_id': payment_id,
            'transaction_id': payment.provider_transaction_id,
            'order_id': order_id
        }

    def refund_payment(self, payment, user, ip_address):
        try:
            if payment.order.user != user:
                raise PermissionDenied("Bu işlem için yetkiniz yok.")

            request = {
                'locale': 'tr',
                'conversationId': str(payment.order.id),
                'paymentTransactionId':  payment.provider_transaction_id,
                'price': str(payment.amount),
                'currency': payment.currency,
                'ip': ip_address
            }

            refund = iyzipay.Refund().create(request, self.options)
            response_data = refund.read().decode("utf-8")
            result = json.loads(response_data)


            if result.get('status') == 'success':
                with transaction.atomic():
                    payment.status = Payment.PaymentStatus.REFUNDED
                    payment.save()

                    payment.order.status = 'CANCELED'
                    payment.order.save()

                return {
                    'status': 'success'
                }
            else:
                error_message = result.get('errorMessage') or "İade işlemi başarısız."
                logger.error(f"İyzipay iade hatası: {error_message}")
                return {'status': 'error', 'error_message': error_message}
        except Exception as e:
            logger.error(f"İade sırasında beklenmeyen hata: {str(e)}", exc_info=True)
            return {'status': 'error', 'error_message': str(e)}