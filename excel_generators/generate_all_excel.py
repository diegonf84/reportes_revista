import logging
import argparse
import sys
import time

# Import all Excel generator functions
from apertura_por_subramos import generate_apertura_subramo_excel
from cuadro_nuevo import generate_cuadro_nuevo_excel
from cuadro_principal import generate_cuadro_principal_excel
from detalle_inmuebles import generate_detalle_inmuebles_excel
from ganaron_perdieron import generate_ganaron_perdieron_excel
from primas_cedidas_reaseguro import generate_primas_cedidas_excel
from ranking_comparativo import generate_ranking_comparativo_excel
from ranking_comparativo_por_ramo import generate_ranking_ramo_excel
from ranking_generales import generate_ranking_produccion_excel
from sueldos_y_gastos import generate_sueldos_gastos_excel

def generate_all_excel_reports(period: str) -> None:
    """
    Genera todos los archivos Excel para un período específico.
    
    Args:
        period: Período en formato YYYYPP (ej: "202502")
    """
    
    # Lista de generadores con nombres descriptivos
    generators = [
        ("Apertura por Subramos", generate_apertura_subramo_excel),
        ("Cuadro Nuevo", generate_cuadro_nuevo_excel),
        ("Cuadro Principal", generate_cuadro_principal_excel),
        ("Detalle Inmuebles", generate_detalle_inmuebles_excel),
        ("Ganaron Perdieron", generate_ganaron_perdieron_excel),
        ("Primas Cedidas Reaseguro", generate_primas_cedidas_excel),
        ("Ranking Comparativo", generate_ranking_comparativo_excel),
        ("Ranking Comparativo por Ramo", generate_ranking_ramo_excel),
        ("Ranking Generales (Producción)", generate_ranking_produccion_excel),
        ("Sueldos y Gastos", generate_sueldos_gastos_excel)
    ]
    
    print(f"🚀 Iniciando generación de {len(generators)} archivos Excel para período {period}")
    print("=" * 70)
    
    successful = []
    failed = []
    start_time = time.time()
    
    for i, (name, generator_func) in enumerate(generators, 1):
        try:
            print(f"[{i:2d}/{len(generators)}] Generando {name}...")
            
            # Ejecutar el generador
            excel_path = generator_func(period)
            
            print(f"✅ {name} completado")
            successful.append(name)
            
        except FileNotFoundError as e:
            error_msg = f"CSV no encontrado - {str(e)}"
            print(f"❌ {name} falló: {error_msg}")
            failed.append((name, error_msg))
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ {name} falló: {error_msg}")
            failed.append((name, error_msg))
    
    # Resumen final
    elapsed_time = time.time() - start_time
    print("=" * 70)
    print(f"🎯 Resumen de generación para período {period}")
    print(f"⏱️  Tiempo total: {elapsed_time:.1f} segundos")
    print(f"✅ Exitosos: {len(successful)}")
    print(f"❌ Fallidos: {len(failed)}")
    
    if successful:
        print(f"\n📄 Archivos Excel generados exitosamente ({len(successful)}):")
        for name in successful:
            print(f"   ✅ {name}")
    
    if failed:
        print(f"\n⚠️  Archivos que fallaron ({len(failed)}):")
        for name, error in failed:
            print(f"   ❌ {name}: {error}")
        print(f"\n💡 Tip: Asegúrate de que todos los archivos CSV estén generados primero")
        print(f"      Ejecuta: python ending_files/generate_all_reports.py --period {period}")
    
    # Directorio de salida
    print(f"\n📁 Archivos Excel guardados en: excel_final_files/{period}/")
    
    # Exit code
    if failed:
        print(f"\n⚠️  Proceso completado con {len(failed)} errores")
        sys.exit(1)
    else:
        print(f"\n🎉 Todos los archivos Excel generados exitosamente!")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Genera todos los archivos Excel para un período')
    parser.add_argument('period', help='Período del reporte (ej: 202502)')
    
    args = parser.parse_args()
    
    # Configurar logging para suprimir mensajes individuales de cada generador
    logging.basicConfig(level=logging.WARNING)
    
    try:
        generate_all_excel_reports(args.period)
    except KeyboardInterrupt:
        print(f"\n🛑 Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)