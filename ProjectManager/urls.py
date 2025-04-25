from django.urls import path
from django.urls import include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
  path('', views.projectlist_view, name = 'projects'),
  path('create/', views.create_view, name = 'create'),
  path('delete/<int:pk>', views.delete_view, name = 'delete'),
  path('balance/', views.balance, name= 'balance'),
  path('upload/<int:pk>', views.upload_files, name= 'upload'),
  path('filesview/<int:pk>', views.file_view, name = 'files'),
  path('project/<int:pk>',views.project_view, name= 'projectview'),
  path('project/mod/<int:pk>', views.mod_view, name= 'modification',),
  path('history', views.history_view, name='history'),
  path('chart-data/', views.chart_data, name='chartdata'),
  path('search/', views.search, name='search'),
  path('users/', include ('Users.urls')),
  
]
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.STATIC_URL,document_root=settings.STATICFILES_DIRS)
urlpatterns += (static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT))