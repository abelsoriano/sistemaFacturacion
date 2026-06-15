from django.db import migrations, models
import django.db.models.deletion


LOW_RISK_MODELS = (
    "Client",
    "Category",
    "Product",
    "Almacen",
    "AssetCategory",
    "Asset",
    "ServicioManoObra",
    "AbonoServicio",
)


def validate_no_null_company(apps, schema_editor):
    null_counts = []
    for model_name in LOW_RISK_MODELS:
        model = apps.get_model("facturacion", model_name)
        count = model.objects.filter(company__isnull=True).count()
        if count:
            null_counts.append(f"{model_name}={count}")

    if null_counts:
        raise RuntimeError(
            "No se puede aplicar company NOT NULL en dominios low-risk. "
            "Existen registros sin empresa: " + ", ".join(null_counts)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("facturacion", "0026_electronicfiscaldocument_company"),
    ]

    operations = [
        migrations.RunPython(validate_no_null_company, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="abonoservicio",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="abonos_servicio",
                to="facturacion.company",
            ),
        ),
        migrations.AlterField(
            model_name="almacen",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="almacenes",
                to="facturacion.company",
            ),
        ),
        migrations.AlterField(
            model_name="asset",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="assets",
                to="facturacion.company",
            ),
        ),
        migrations.AlterField(
            model_name="assetcategory",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="asset_categories",
                to="facturacion.company",
            ),
        ),
        migrations.AlterField(
            model_name="category",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="categories",
                to="facturacion.company",
            ),
        ),
        migrations.AlterField(
            model_name="client",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="clients",
                to="facturacion.company",
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="products",
                to="facturacion.company",
            ),
        ),
        migrations.AlterField(
            model_name="serviciomanoobra",
            name="company",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="servicios_mano_obra",
                to="facturacion.company",
            ),
        ),
    ]
