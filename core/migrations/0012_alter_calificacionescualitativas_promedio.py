# Generated by Django 5.1.1 on 2024-09-15 15:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_fortalezasdebilidadesescula'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calificacionescualitativas',
            name='promedio',
            field=models.FloatField(null=True),
        ),
    ]
