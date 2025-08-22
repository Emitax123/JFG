from django.urls import path
from . import views


urlpatterns = [
  path('', views.accounting_mov_display, name='accounting_display'),
  path('<int:pk>/', views.accounting_mov_display, name='accounting_display'),
  path('createentry/<int:pk>/', views.create_manual_acc_entry, name='accounting_create')
]