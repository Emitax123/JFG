from django.urls import path
from django.urls import include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import static, staticfiles_urlpatterns
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
  path('', views.index, name = 'index'),
  path('projects/', views.projectlist_view, name = 'projects'),
  path('listprojects/<int:pk>', views.alt_projectlist_view, name = 'projectslist'),
  path('listprojectstype/<int:type>', views.projectlistfortype_view, name = 'listpaused'),
  path('listpaused/', views.list_paused, name = 'projectslistpaused'),
  path('create/', views.create_view, name = 'create'),
  path('delete/<int:pk>', views.delete_view, name = 'delete'),
  path('close/<int:pk>', views.close_view, name = 'close'),
  path('pause/<int:pk>', views.pause_view, name = 'pause'),
  path('balance/', views.balance, name= 'balance'),
  path('upload/<int:pk>', views.upload_files, name= 'upload'),
  path('download/<int:pk>/', views.download_file, name='download'),
  path('deletefile/<int:pk>', views.delete_file, name='deletefile'),
  path('filesview/<int:pk>', views.file_view, name = 'files'),
  path('project/<int:pk>',views.project_view, name= 'projectview'),
  path('project/mod/<int:pk>', views.mod_view, name= 'modification',),
  path('project/modify/<int:pk>', views.full_mod_view, name='fullmodification'),
  path('history', views.history_view, name='history'),
  path('chart-data/', views.chart_data, name='chartdata'),
  path('search/', views.search, name='search'),
  path('users/', include ('Users.urls')),
  
  path('clients/', views.clients_view, name='clients'),
  path('clients/create', views.create_client_view, name='clientcreate'),
  path('clients/projectcreate/<int:pk>', views.create_for_client, name='clientprojectcreate'),
  path('create/clientedislist/<int:pk>', views.clientedislist, name='clientedislist'),
  path('accounting/', include('Accounting.urls')),
  path('balance-info/', views.balance_info, name='balance_info'),
]
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.STATIC_URL,document_root=settings.STATICFILES_DIRS)
urlpatterns += (static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT))