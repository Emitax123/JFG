from django.db import models

# Create your models here.
class Client(models.Model):
    name = models.CharField(max_length=40, verbose_name='Nombre y apellido')
    phone = models.CharField(max_length=40, default="", verbose_name='Telefono')
    flag = models.BooleanField(default=False, verbose_name='Fijo')
    not_listed = models.BooleanField(default=False, verbose_name='No listado')

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['name']
        
    def __str__(self):
        return self.name
    

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
    mens = models.CharField(null=True, blank=True, max_length=30, choices=MENS_CHOICES, verbose_name='Mensura')
    #CLiente
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True)
    
    #Deberia añadir files como un campo relacionado a un modelo de archivos
    
    #Titular, que puede o no puede ser el cliente
    titular_name = models.CharField(default="", max_length=30, blank=True, verbose_name='Nombre y apellido')
    titular_phone = models.CharField(default="", max_length=40, blank=True, verbose_name='Telefono')

    #Contacto, que puede o no puede ser el cliente
    contact_name = models.CharField(default="", max_length=30, blank=True, verbose_name='Nombre', null=True)
    contact_phone = models.CharField(default="", max_length=40, blank=True, verbose_name='Telefono', null=True)
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
    
    manzana_num= models.CharField(max_length=10, blank=True, verbose_name='Numero')
    manzana_letra= models.CharField(max_length=10, blank=True, verbose_name='Letra')

    parcela_num = models.CharField(max_length=10, blank=True, verbose_name='Numero')
    parcela_letra = models.CharField(max_length=10, blank=True, verbose_name='Letra')
    
    subparcela = models.CharField(max_length=10, blank=True, verbose_name='Subparcela')
   
    
    direction = models.CharField(max_length=100, blank=True, verbose_name='Calle')
    direction_number = models.CharField(max_length=10, blank=True, verbose_name='Altura')
    floor = models.CharField(max_length=10, blank=True, verbose_name='Piso')
    depto = models.CharField(max_length=10, blank=True, verbose_name='Depto')

    INSC_CHOICES = (
        ('Folio','Folio'),
        ('Matricula','Matricula'),
        )
    inscription_type = models.CharField(null=True, max_length=30, default='', choices=INSC_CHOICES, verbose_name='Inscripcion')
    #Costos
    price = models.DecimalField(default=0, decimal_places=2, max_digits=10, verbose_name='Presupuesto')
    adv = models.DecimalField(default=0, decimal_places=2, max_digits=10, verbose_name='Anticipo')
    gasto = models.DecimalField(default=0, decimal_places=2, max_digits=10, verbose_name='Gastos')
    #Datos finales
    procedure = models.IntegerField(null=True, blank=True, verbose_name='N° Tramite')
    #aprob = models.DateField(default=)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    closed = models.BooleanField(default=False, verbose_name='Cerrado')
    paused = models.BooleanField(default=False, verbose_name='Pausado')
    
    def formatted_price(self):
        return f"{self.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def formatted_adv(self):
        return f"{self.adv:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def formatted_gasto(self):
        return f"{self.gasto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def __str__(self):
        namepk = str(self.pk) + " - " + self.type
        return namepk
    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['-created']

class ProjectFiles (models.Model):
    project_pk= models.IntegerField(default=0)
    name = models.CharField(max_length=100, null=True, blank=True)
    url = models.URLField(null=True, blank=True)

class Event (models.Model):
    #Para modificaciones type=1
    #Para creaciones type = 2
    #Para deletes type = 3
    type = models.IntegerField(default=0)
    time = models.DateTimeField(auto_now_add=True)
    model_pk = models.IntegerField(default=0)
    msg = models.CharField(max_length=100, null=True)
    
    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ['-time']
    def __str__(self):
        return f"{self.time.strftime('%Y-%m-%d %H:%M:%S')} - {self.model_pk} - {self.msg}"
