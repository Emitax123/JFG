from django.contrib import admin


from .models import Account, AccountMovement
admin.site.register(Account)
admin.site.register(AccountMovement)