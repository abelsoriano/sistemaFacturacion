from docx import Document
import os

# Nombre del archivo
filename = "archivo_prueba.docx"
doc = Document()

# Crear un texto muy largo repetido
texto = ("Este es un texto de prueba para llenar el documento. " * 1000)

# Insertar ese texto varias veces
for i in range(2000):  # Ajusta este número si necesitas más tamaño
    doc.add_paragraph(texto)

# Guardar
doc.save(filename)

# Verificar tamaño
size_mb = os.path.getsize(filename) / (1024*1024)
print(f"Tamaño del archivo: {size_mb:.2f} MB")
