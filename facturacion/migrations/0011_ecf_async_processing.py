# Generated manually for Celery based e-CF processing.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0010_electronicfiscaldocument_dgii_request_xml_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='electronicfiscaldocument',
            name='async_task_id',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True, verbose_name='Task Celery Actual'),
        ),
        migrations.AddField(
            model_name='electronicfiscaldocument',
            name='idempotency_key',
            field=models.CharField(blank=True, db_index=True, max_length=120, null=True, verbose_name='Clave Idempotencia'),
        ),
        migrations.AddField(
            model_name='electronicfiscaldocument',
            name='submission_attempts',
            field=models.PositiveIntegerField(default=0, verbose_name='Intentos de Envío'),
        ),
        migrations.AddField(
            model_name='electronicfiscaldocument',
            name='status_check_attempts',
            field=models.PositiveIntegerField(default=0, verbose_name='Intentos Consulta Estado'),
        ),
        migrations.AddField(
            model_name='electronicfiscaldocument',
            name='next_retry_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Próximo Reintento'),
        ),
        migrations.AddField(
            model_name='electronicfiscaldocument',
            name='last_error',
            field=models.TextField(blank=True, null=True, verbose_name='Último Error'),
        ),
    ]
