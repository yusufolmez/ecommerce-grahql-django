from django.shortcuts import render
from .models import Order
from .payment_service import IyzicoPaymentService
from django.http import JsonResponse    
from django.views.decorators.csrf import csrf_exempt
from .models import Payment

def payment_page(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        payment_service = IyzicoPaymentService()
        result = payment_service.create_payment_form(order.payment, request.user, callback_url="http://localhost:8000/payment/callback/")
        
        payment_token = result['token']
        price = order.total_price
        
        return render(request, 'payment_template.html', {
            'payment_token': payment_token,
            'payment_form_content': result['checkoutFormContent'],
            'price': price
        })
    except Order.DoesNotExist:
        return render(request, 'payment_template.html', {
            'error_message': 'Sipariş bulunamadı.'
        })
@csrf_exempt
def payment_callback(request):
    try:
        token = request.POST.get('token')
        if not token:
            print("No token found in request")
            return render(request, 'payment_failed.html', {'error': 'No payment token provided'})

        payment_service = IyzicoPaymentService()
        result = payment_service.verify_payment(token)
        
        if result['status'] == 'success':
            try:
                order = Order.objects.get(id=result.get('order_id'))
                payment = order.payment
                
                payment.status = Payment.PaymentStatus.COMPLETED
                payment.provider_payment_id = result['payment_id']
                payment.provider_transaction_id = result['transaction_id']
                payment.save()
                
                order.status = Order.OrderStatus.PROCESSING
                order.save()
                
                return render(request, 'payment_success.html', {'order': order})
                
            except Order.DoesNotExist:
                print(f"Order not found for order ID: {result.get('order_id')}")
                return render(request, 'payment_failed.html', {'error': 'Order not found'})
        else:
            return render(request, 'payment_failed.html', 
                        {'error': result.get('error_message', 'Payment verification failed')})
                        
    except Exception as e:
        print(f"Callback error: {str(e)}")
        return render(request, 'payment_failed.html', {'error': str(e)})