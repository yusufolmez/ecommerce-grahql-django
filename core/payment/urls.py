from django.urls import path
from . import views

urlpatterns = [
    path('payment/<int:order_id>/', views.payment_page, name='payment_page'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
]