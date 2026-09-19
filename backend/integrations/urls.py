from django.urls import path

from . import views

app_name = 'integrations'

urlpatterns = [
    path('daraja/b2c/callback/', views.daraja_b2c_callback, name='daraja-b2c-callback'),
    path('daraja/b2c/timeout/', views.daraja_b2c_timeout, name='daraja-b2c-timeout'),
    path(
        'daraja/transaction-status/callback/',
        views.daraja_transaction_status_callback,
        name='daraja-transaction-status-callback',
    ),
]