# facturacion/management/commands/generar_codigos.py
from django.core.management.base import BaseCommand
from facturacion.models import Product

class Command(BaseCommand):
    help = 'Genera códigos de barras para productos sin código'

    def handle(self, *args, **kwargs):
        productos = Product.objects.filter(barcode__isnull=True)
        total = productos.count()
        
        if total == 0:
            self.stdout.write(
                self.style.SUCCESS('✓ Todos los productos ya tienen código de barras')
            )
            return
        
        self.stdout.write(f'Generando códigos para {total} productos...\n')
        
        for producto in productos:
            producto.save()
            self.stdout.write(
                self.style.SUCCESS(f'✓ {producto.name}: {producto.barcode}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n¡Completado! {total} códigos generados')
        )


# ddkdjkadjajdkla
from facturacion.models import Product

productos = Product.objects.filter(barcode__isnull=True)
print(f"Productos sin código: {productos.count()}")

for producto in productos:
    producto.save()
    print(f"✓ {producto.name}: {producto.barcode}")

print("¡Completado!")