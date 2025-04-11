# Generated by Django 4.2.4 on 2025-04-11 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ProjectManager', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='manzana_letra',
        ),
        migrations.RemoveField(
            model_name='project',
            name='manzana_num',
        ),
        migrations.RemoveField(
            model_name='project',
            name='parcela_letra',
        ),
        migrations.RemoveField(
            model_name='project',
            name='parcela_num',
        ),
        migrations.AlterField(
            model_name='project',
            name='chacra_letra',
            field=models.CharField(blank=True, max_length=10, verbose_name='Letra'),
        ),
        migrations.AlterField(
            model_name='project',
            name='chacra_num',
            field=models.CharField(blank=True, max_length=10, verbose_name='Numero'),
        ),
        migrations.AlterField(
            model_name='project',
            name='circuns',
            field=models.CharField(blank=True, max_length=30, verbose_name='Circunscripcion'),
        ),
        migrations.AlterField(
            model_name='project',
            name='fraccion_letra',
            field=models.CharField(blank=True, max_length=10, verbose_name='Letra'),
        ),
        migrations.AlterField(
            model_name='project',
            name='fraccion_num',
            field=models.CharField(blank=True, max_length=10, verbose_name='Numero'),
        ),
        migrations.AlterField(
            model_name='project',
            name='partida',
            field=models.CharField(blank=True, max_length=30, verbose_name='Partida'),
        ),
        migrations.AlterField(
            model_name='project',
            name='partido',
            field=models.CharField(blank=True, max_length=30, verbose_name='Partido'),
        ),
        migrations.AlterField(
            model_name='project',
            name='quinta_letra',
            field=models.CharField(blank=True, max_length=10, verbose_name='Letra'),
        ),
        migrations.AlterField(
            model_name='project',
            name='quinta_num',
            field=models.CharField(blank=True, max_length=10, verbose_name='Numero'),
        ),
        migrations.AlterField(
            model_name='project',
            name='seccion',
            field=models.CharField(blank=True, max_length=30, verbose_name='Seccion'),
        ),
    ]
