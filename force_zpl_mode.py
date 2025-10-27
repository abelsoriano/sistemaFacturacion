"""
Script para cambiar la impresora Zebra a modo ZPL permanentemente
Ejecutar: python force_zpl_mode.py
"""

import win32print

def force_zpl_mode():
    """
    Envía comando ZPL para cambiar permanentemente el modo de la impresora
    """
    # Comando ZPL para cambiar a modo ZPL
    # ^SZD = Set ZPL Mode, Data saved to DRAM
    zpl_mode_command = b"^XA^SZD^XZ"
    
    # Nombre de tu impresora
    printer_name = "ZDesigner LP 2824 Plus (ZPL)"
    
    print(f"Cambiando {printer_name} a modo ZPL...")
    
    try:
        # Abrir impresora
        hPrinter = win32print.OpenPrinter(printer_name)
        
        try:
            # Enviar comando en modo RAW
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("Cambiar a ZPL", None, "RAW"))
            
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, zpl_mode_command)
                win32print.EndPagePrinter(hPrinter)
                
                print("✓ Comando enviado correctamente")
                print("✓ La impresora ahora está en modo ZPL")
                print("\nPuedes verificar imprimiendo una etiqueta de prueba:")
                print("Comandos ZPL ahora serán interpretados correctamente.")
                
            finally:
                win32print.EndDocPrinter(hPrinter)
                
        finally:
            win32print.ClosePrinter(hPrinter)
            
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        print("\nSoluciones alternativas:")
        print("1. Verifica que el nombre de la impresora sea correcto")
        print("2. Ejecuta este script como Administrador")
        print("3. O crea un archivo 'zpl_mode.zpl' con contenido: ^XA^SZD^XZ")
        print("   Y ejecuta: copy /b zpl_mode.zpl USB001")
        return False


def print_test_label():
    """
    Imprime una etiqueta de prueba con código de barras
    """
    printer_name = "ZDesigner LP 2824 Plus (ZPL)"
    
    # Etiqueta de prueba ZPL
    test_zpl = b"""^XA
^SZD
^FO50,20^A0N,40,40^FDPRUEBA ZPL^FS
^FO50,70^BY3^BCN,80,Y,N,N^FD123456789^FS
^FO50,160^A0N,30,30^FD$99.99^FS
^XZ"""
    
    print(f"\nImprimiendo etiqueta de prueba...")
    
    try:
        hPrinter = win32print.OpenPrinter(printer_name)
        
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("Test ZPL", None, "RAW"))
            
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, test_zpl)
                win32print.EndPagePrinter(hPrinter)
                
                print("✓ Etiqueta de prueba enviada")
                print("\nSi ves un código de barras = Modo ZPL OK ✓")
                print("Si ves comandos como texto = Modo EPL (necesita cambio)")
                
            finally:
                win32print.EndDocPrinter(hPrinter)
                
        finally:
            win32print.ClosePrinter(hPrinter)
            
        return True
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("SCRIPT PARA FORZAR MODO ZPL EN ZEBRA TLP 2824 PLUS")
    print("="*60)
    print()
    
    # Paso 1: Cambiar a modo ZPL
    if force_zpl_mode():
        print()
        print("-"*60)
        
        # Paso 2: Imprimir prueba
        response = input("\n¿Quieres imprimir una etiqueta de prueba? (s/n): ")
        if response.lower() in ['s', 'si', 'y', 'yes']:
            print_test_label()
    
    print()
    print("="*60)
    print("PROCESO COMPLETADO")
    print("="*60)