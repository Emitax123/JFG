from django.contrib import admin


from .models import Account, AccountMovement, MonthlyFinancialSummary
admin.site.register(MonthlyFinancialSummary)
admin.site.register(Account)
admin.site.register(AccountMovement)
