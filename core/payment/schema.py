
import graphene
import logging
from graphene_django import DjangoObjectType
from .models import Payment
from .payment_service import IyzicoPaymentService
from django.conf import settings
from ecommerce.models import Order
from django.utils import timezone
import iyzipay
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

class PaymentType(DjangoObjectType):
    class Meta:
        model = Payment
        fields = '__all__'

class InitiatePaymentMutation(graphene.Mutation):
    class Arguments:
        order_id = graphene.ID(required=True)

    success = graphene.Boolean()
    payment_form_content = graphene.String()
    error_message = graphene.String()

    def mutate(self, info, order_id):
        user = info.context.user
        if user.is_anonymous:
            raise Exception('Please login to proceed with payment')

        try:
            order = Order.objects.get(id=order_id, user=user)
            
            payment = Payment.objects.create(
                order=order,
                amount=order.total_price,
                currency='TRY',
                provider=Payment.PaymentProvider.IYZICO,
                provider_payment_id="",
                provider_transaction_id=" ",
            )

            payment_service = IyzicoPaymentService()
            callback_url = f"{settings.SITE_URL}/payment/callback/"
            
            result = payment_service.create_payment_form(payment, user, callback_url)
            
            if result['status'] == 'success':
                return InitiatePaymentMutation(
                    success=True,
                    payment_form_content=result['checkoutFormContent']
                )
            else:
                payment.status = Payment.PaymentStatus.FAILED
                payment.error_message = result['error_message']
                payment.save()
                return InitiatePaymentMutation(
                    success=False,
                    error_message=result['error_message']
                )

        except Order.DoesNotExist:
            return InitiatePaymentMutation(
                success=False,
                error_message="Order not found"
            )
        except Exception as e:
            return InitiatePaymentMutation(
                success=False,
                error_message=str(e)
            )

class VerifyPaymentMutation(graphene.Mutation):
    class Arguments:
        token = graphene.String(required=True)

    success = graphene.Boolean()
    error_message = graphene.String()

    def mutate(self, info, token):
        try:
            payment_service = IyzicoPaymentService()
            result = payment_service.verify_payment(token)

            if result['status'] == 'success':
                order = Order.objects.get(id=result['order_id'])
                payment = order.payment
                if payment.status == Payment.PaymentStatus.COMPLETED:
                    return VerifyPaymentMutation(
                        success=False,
                        error_message = result['error_message']
                    )
                payment.status = Payment.PaymentStatus.COMPLETED
                payment.provider_transaction_id = result['transaction_id']
                payment.save()
                
                payment.order.status = 'PROCESSING'
                payment.order.save()
                
                return VerifyPaymentMutation(success=True)
            else:
                return VerifyPaymentMutation(
                    success=False,
                    error_message=result['error_message']
                )

        except Exception as e:
            return VerifyPaymentMutation(
                success=False,
                error_message=str(e)
            )

class CancelOrderMutation(graphene.Mutation):
    class Arguments:
        payment_id = graphene.ID(required=True)

    success = graphene.Boolean()
    error_message = graphene.String()

    def mutate(self, info, payment_id):
        user = info.context.user
        if user.is_anonymous:
            return CancelOrderMutation(success=False, error_message="Lütfen giriş yapınız.")

        try:
            try:
                payment_obj = Payment.objects.get(id=int(payment_id))
                ip_address = info.context.META.get('REMOTE_ADDR', '')
            except (ValueError, Payment.DoesNotExist):
                return CancelOrderMutation(
                    success=False,
                    error_message="Geçersiz ödeme ID'si veya ödeme kaydı bulunamadı."
                )

            order = payment_obj.order
            if not order:
                return CancelOrderMutation(
                    success=False,
                    error_message="Ödeme ile ilişkili bir sipariş bulunamadı."
                )

            if (timezone.now() - order.created_at).total_seconds() > 86400:
                return CancelOrderMutation(
                    success=False,
                    error_message="İptal süresi dolmuştur. Sipariş oluşturulma süresinden 24 saat geçti."
                )

            if not payment_obj.provider_transaction_id:
                return CancelOrderMutation(
                    success=False,
                    error_message="Bu ödeme için işlem numarası (transaction ID) bulunamadı."
                )

            payment_service = IyzicoPaymentService()
            result = payment_service.refund_payment(payment_obj, user, ip_address)

            if result['status'] == 'success':
                return CancelOrderMutation(success=True)
            else:
                return CancelOrderMutation(success=False, error_message=result['error_message'])

        except Payment.DoesNotExist:
            return CancelOrderMutation(success=False, error_message="Geçersiz ödeme ID'si.")
        except PermissionDenied as e:
            return CancelOrderMutation(success=False, error_message=str(e))
        except Exception as e:
            logger.error(f"Sistem hatası: {str(e)}")
            return CancelOrderMutation(success=False, error_message="Teknik bir sorun oluştu.")

class Mutation(graphene.ObjectType):
    initiate_payment = InitiatePaymentMutation.Field()
    verify_payment = VerifyPaymentMutation.Field()
    cancel_order_refund = CancelOrderMutation.Field()