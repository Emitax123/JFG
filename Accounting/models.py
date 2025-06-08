from django.utils import timezone
from django.db import models

from ProjectManager.models import Project

class Account(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    estimated = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Presupuesto")
    expenses = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    advance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    netWorth = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    created = models.DateTimeField(auto_now=True, verbose_name="Fecha de Creación")
    def __str__(self):
        return str(self.project.pk) + self.project.created.strftime(" - %Y-%m-%d")

    class Meta:
        verbose_name = "Cobranza"
        verbose_name_plural = "Cobranzas"
        
class AccountMovement(models.Model):
    MOVEMENT_TYPES = (
        ('ADV', 'Anticipo'),
        ('EXP', 'Gasto'),
        ('EST', 'Presupuesto'),
    )
    
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='movements')
    project = models.ForeignKey('ProjectManager.Project', on_delete=models.CASCADE, verbose_name="Proyecto")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES, verbose_name="Tipo de Movimiento")
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [
            models.Index(fields=['account', 'created_at']),  # For queries filtering by account and sorting by date
            models.Index(fields=['movement_type']),          # For queries filtering by movement type
        ]
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.amount} - {self.created_at.strftime('%d/%m/%Y')}"