# Generated by Django 4.2.4 on 2023-11-10 15:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ProjectManager', '0009_remove_project_files_alter_project_inscription_type_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='projectfiles',
            old_name='files',
            new_name='file',
        ),
    ]
