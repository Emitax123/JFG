from django.urls import path
from . import views


urlpatterns = [
  path('', views.accounting_mov_display, name='accounting_display'),
  path('<int:pk>/', views.accounting_mov_display, name='accounting_display'),
  path('createentry/<int:pk>/', views.create_manual_acc_entry, name='accounting_create'),
  path('earnings/', views.get_earnings_per_client, name='earnings_per_client'),
  path('earnings/<int:count>/', views.display_earnings, name='earnings_per_client_count'),
  path('client-earnings/<int:client_id>/', views.client_detailed_earnings, name='client_detailed_earnings'),
]