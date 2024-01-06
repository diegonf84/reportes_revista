from carga_archivo import procesar_archivo
import os


def procesar_archivos_en_carpeta(ruta_carpeta, extension_archivo='.txt'):
    for archivo in os.listdir(ruta_carpeta):
        if archivo.endswith(extension_archivo):
            ruta_completa = os.path.join(ruta_carpeta, archivo)
            print(f"Procesando archivo: {archivo}")
            procesar_archivo(ruta_completa)


if __name__ == "__main__":
    ruta_carpeta = 'files_import'  # Asegúrate de que esta ruta sea correcta
    procesar_archivos_en_carpeta(ruta_carpeta)
