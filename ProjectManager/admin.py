from django.contrib import admin
from .models import Project, Client, Event, ProjectFiles
# Register your models here.

admin.site.register(Project)
admin.site.register(Client)
admin.site.register(Event)
admin.site.register(ProjectFiles)