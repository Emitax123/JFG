# Generated by Django 4.2.4 on 2023-08-02 22:57

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, verbose_name='Nombre y apellido')),
                ('dni', models.IntegerField(default=0, verbose_name='DNI')),
                ('phone', models.IntegerField(default=0, verbose_name='Telefono')),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('1', 'Estado Parcelario'), ('2', 'Mensura'), ('3', 'Amojonamiento'), ('4', 'Relevamiento'), ('5', 'Legajo Parcelario')], max_length=30, verbose_name='Proyecto')),
                ('mens', models.CharField(choices=[('1', 'PH'), ('2', 'Usucapion'), ('3', 'Division'), ('4', 'Anexion'), ('5', 'Unificacion')], max_length=30, verbose_name='Mensura')),
                ('client_name', models.CharField(max_length=30, verbose_name='Nombre y apellido')),
                ('client_dni', models.IntegerField(default=0, verbose_name='DNI')),
                ('client_phone', models.IntegerField(default=0, verbose_name='Telefono')),
                ('noment_seccion', models.CharField(max_length=30, verbose_name='Seccion')),
                ('noment_partido', models.CharField(max_length=30, verbose_name='Partido')),
                ('noment_circuns', models.CharField(max_length=30, verbose_name='Circunscripcion')),
                ('partida_quinta', models.CharField(max_length=30, verbose_name='Quinta')),
                ('partida_manzana', models.CharField(max_length=30, verbose_name='Manzana')),
                ('partida_parcela', models.CharField(max_length=30, verbose_name='Parcela')),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Presupuesto')),
                ('adv', models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Anticipo')),
                ('gasto', models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name='Gastos')),
                ('procedure', models.IntegerField(default=0, verbose_name='N° Tramite')),
                ('aprob', models.DateField()),
                ('files', models.FileField(upload_to='media/files')),
            ],
        ),
    ]
