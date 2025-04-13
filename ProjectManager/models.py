from django.db import models
from os.path import basename
# Create your models here.
class Client(models.Model):
    name = models.CharField(max_length=30, verbose_name='Nombre y apellido')
    dni = models.CharField(verbose_name='DNI')
    phone = models.CharField(verbose_name='Tel')

class Project (models.Model):
    TYPE_CHOICES = (
        ('Estado Parcelario', 'Estado Parcelario'),
        ('Mensura', 'Mensura'),
        ('Amojonamiento', 'Amojonamiento'),
        ('Relevamiento', 'Relevamiento'),
        ('Legajo Parcelario', 'Legajo Parcelario'),
        #Agregar una opcion de carga manual
        )
    MENS_CHOICES = (
        ('PH', 'PH'),
        ('Usucapion', 'Usucapion'),
        ('Division', 'Division'),
        ('Anexion/Division', 'Anexion/Division'),
        ('Unificacion', 'Unificacion'),
        )
    
    type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name='Proyecto')
    mens = models.CharField(max_length=30, choices=MENS_CHOICES, verbose_name='Mensura')
    #CLiente
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True)
    
    #Titular, que puede o no puede ser el cliente
    titular_name = models.CharField(max_length=30, verbose_name='Nombre y apellido')
    titular_dni = models.IntegerField(verbose_name='DNI')
    titular_phone = models.IntegerField(verbose_name='Telefono')
    #Nomenclatura
    partido= models.CharField(max_length=30, blank=True, verbose_name='Partido')
    partida= models.CharField(max_length=30, blank=True, verbose_name='Partida')
    circuns= models.CharField(max_length=30, blank=True, verbose_name='Circunscripcion')
    seccion= models.CharField(max_length=30, blank=True, verbose_name='Seccion')
    #Partida
    #Si hay chacra no hay quinta y vice
    chacra_num = models.CharField(max_length=10, blank=True, verbose_name='Numero')
    chacra_letra= models.CharField(max_length=10, blank=True, verbose_name='Letra')

    quinta_num= models.CharField(max_length=10, blank=True, verbose_name='Numero')
    quinta_letra= models.CharField(max_length=10, blank=True, verbose_name='Letra')
    
    fraccion_num = models.CharField(max_length=10, blank=True, verbose_name='Numero')
    fraccion_letra = models.CharField(max_length=10, blank=True, verbose_name='Letra')
    
    INSC_CHOICES = (
        ('Folio','Folio'),
        ('Matricula','Matricula'),
        )
    inscription_type = models.CharField(null=True, max_length=30, default='', choices=INSC_CHOICES, verbose_name='Parcela')
    #Costos
    price = models.DecimalField(default=0, decimal_places=2, max_digits=8, verbose_name='Presupuesto')
    adv = models.DecimalField(default=0, decimal_places=2, max_digits=8, verbose_name='Anticipo')
    gasto = models.DecimalField(default=0, decimal_places=2, max_digits=8, verbose_name='Gastos')
    #Datos finales
    procedure = models.IntegerField(null=True, verbose_name='N° Tramite')
    #aprob = models.DateField(default=)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

class ProjectFiles (models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    files = models.FileField(null=True, upload_to='media/files')
    def filename(self):
        return basename(self.files.name)

class Event (models.Model):
    #Para modificaciones type=1
    #Para creaciones type = 2
    type = models.IntegerField(default=0)
    time = models.DateTimeField(auto_now_add=True)
    model_pk = models.IntegerField(default=0)
    msg = models.CharField(max_length=50, null=True)
