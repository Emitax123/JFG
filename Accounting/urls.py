from django.urls import path
from . import views


urlpatterns = [
  path('', views.accounting_mov_display, name='accounting_display'),
  path('<int:pk>/', views.accounting_mov_display, name='accounting_display'),
  path('accall/', views.create_month_summary, name='summary_all'),
]