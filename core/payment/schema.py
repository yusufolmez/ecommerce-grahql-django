
import graphene
from graphene_django import DjangoObjectType
from .models import Payment
from .payment_service import IyzicoPaymentService
from django.conf import settings
from ecommerce.models import Order

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
                provider=Payment.PaymentProvider.IYZICO
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
                payment = Payment.objects.get(provider_payment_id=result['payment_id'])
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

class Mutation(graphene.ObjectType):
    initiate_payment = InitiatePaymentMutation.Field()
    verify_payment = VerifyPaymentMutation.Field()