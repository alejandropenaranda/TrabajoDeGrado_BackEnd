# Generated by Django 4.2.6 on 2024-07-20 14:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_promediocalificaciones_codigo_materia'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='promediocalificaciones',
            name='codigo_materia',
        ),
        migrations.AddField(
            model_name='promediocalificaciones',
            name='materia',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, to='core.materia'),
            preserve_default=False,
        ),
    ]
