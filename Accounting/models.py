from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User

from ProjectManager.models import Project

class Account(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    estimated = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Presupuesto")
    expenses = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    advance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    netWorth = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    created = models.DateTimeField(auto_now=True, verbose_name="Fecha de Creación")
    def __str__(self):
        return str(self.project.pk) + self.created.strftime(" - %Y-%m-%d")

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
        verbose_name = "Movimiento de Cuenta"
        verbose_name_plural = "Movimientos de Cuenta"
        ordering = ['-created_at']  # Default ordering for better query performance
        indexes = [
            models.Index(fields=['account', 'created_at']),  # For queries filtering by account and sorting by date
            models.Index(fields=['movement_type']),          # For queries filtering by movement type
            models.Index(fields=['project', 'created_at']),  # For project-specific queries with date sorting
            models.Index(fields=['-created_at', 'movement_type']),  # For main listing page with type exclusion
            models.Index(fields=['created_at']),  # For date-based filtering
        ]
    
    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.amount} - {self.created_at.strftime('%d/%m/%Y')}"
    
class MonthlyFinancialSummary(models.Model):
    """
    Model that aggregates financial data by month.
    New instances are created automatically when data is recorded in a new month.
    """
    year = models.IntegerField(verbose_name="Año")
    month = models.IntegerField(verbose_name="Mes")
    total_advance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Cobros Total")
    total_expenses = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Gastos Total")
    total_networth = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta")

    total_net_mensura = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Mensura")
    total_net_est_parc = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Est Parcelario")
    total_net_leg = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Legajos")
    total_net_amoj = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Amojonamiento")
    total_net_relev = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="Ganancia Neta Relevamiento")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monthly_summaries',
        verbose_name='Creado por'
    )

    class Meta:
        verbose_name = "Resumen Mensual"
        verbose_name_plural = "Resumenes Mensuales"
        unique_together = ['year', 'month']  # Ensure only one record per month
        ordering = ['-year', '-month']  # Default ordering, newest first
        indexes = [
            models.Index(fields=['year', 'month']),  # For efficient lookups by year/month
        ]

    def __str__(self):
        month_names = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        return f"{month_names.get(self.month, self.month)} - {self.year}"
    
    def net_worth(self):
        """
        Calculate the net worth of the monthly summary.
        """
        return self.total_advance - self.total_expenses

    @classmethod
    def initialize(cls, year, month):
        """
        Create a new monthly summary record with default values for the specified year and month.
        If record already exists, it will be returned without modifications.
        """
        
        summary, created = cls.objects.get_or_create(
            year=year,
            month=month,
            defaults={
                'total_advance': 0.00,
                'total_expenses': 0.00,
                'total_networth': 0.00,
            }
        )
        return summary

