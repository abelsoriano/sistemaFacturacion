# Generated by Django 4.2.19 on 2025-05-07 21:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='labour',
            name='factura',
        ),
    ]
