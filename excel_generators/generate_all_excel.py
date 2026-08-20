import logging
import argparse
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from modules.report_generation import validate_excel_outputs

# Import all Excel generator functions
from apertura_por_subramos import generate_apertura_subramo_excel
from apertura_por_subramos_comparativo import generate_apertura_subramo_comparativo_excel
from cuadro_nuevo import generate_cuadro_nuevo_excel
from cuadro_principal import generate_cuadro_principal_excel
from detalle_gastos import generate_detalle_gastos_excel
from detalle_inmuebles import generate_detalle_inmuebles_excel
from distribucion_inversiones import generate_distribucion_inversiones_excel
from ganaron_perdieron import generate_ganaron_perdieron_excel
from indicadores_solvencia import generate_indicadores_solvencia_excel
from primas_cedidas_reaseguro import generate_primas_cedidas_excel
from ranking_comparativo import generate_ranking_comparativo_excel
from ranking_comparativo_por_ramo import generate_ranking_ramo_excel
from ranking_generales import generate_ranking_produccion_excel
from sueldos_y_gastos import generate_sueldos_gastos_excel


GENERATORS = [
    ("Apertura por Subramos", generate_apertura_subramo_excel),
    ("Apertura por Subramos Comparativo", generate_apertura_subramo_comparativo_excel),
    ("Cuadro Nuevo", generate_cuadro_nuevo_excel),
    ("Cuadro Principal", generate_cuadro_principal_excel),
    ("Detalle Gastos", generate_detalle_gastos_excel),
    ("Detalle Inmuebles", generate_detalle_inmuebles_excel),
    ("Distribución Inversiones", generate_distribucion_inversiones_excel),
    ("Ganaron Perdieron", generate_ganaron_perdieron_excel),
    ("Indicadores Solvencia", generate_indicadores_solvencia_excel),
    ("Primas Cedidas Reaseguro", generate_primas_cedidas_excel),
    ("Ranking Comparativo", generate_ranking_comparativo_excel),
    ("Ranking Comparativo por Ramo", generate_ranking_ramo_excel),
    ("Ranking Generales (Producción)", generate_ranking_produccion_excel),
    ("Sueldos y Gastos", generate_sueldos_gastos_excel),
]


def generate_all_excel_reports(
    period: str,
    csv_dir: str = None,
    output_dir: str = None,
) -> dict:
    """
    Genera todos los archivos Excel para un período específico.
    
    Args:
        period: Período en formato YYYYPP (ej: "202502")
    """
    
    print(f"🚀 Iniciando generación de {len(GENERATORS)} archivos Excel para período {period}")
    print("=" * 70)
    
    successful = []
    failed = []
    generated_paths = []
    start_time = time.time()
    
    for i, (name, generator_func) in enumerate(GENERATORS, 1):
        try:
            print(f"[{i:2d}/{len(GENERATORS)}] Generando {name}...")
            
            # Ejecutar el generador
            excel_path = generator_func(period, csv_dir=csv_dir, output_dir=output_dir)
            
            print(f"✅ {name} completado")
            successful.append(name)
            generated_paths.append(Path(excel_path))
            
        except FileNotFoundError as e:
            error_msg = f"CSV no encontrado - {str(e)}"
            print(f"❌ {name} falló: {error_msg}")
            failed.append((name, error_msg))
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ {name} falló: {error_msg}")
            failed.append((name, error_msg))
    
    if not failed:
        validation_directory = (
            Path(output_dir)
            if output_dir
            else project_root / "excel_final_files" / period
        )
        try:
            validate_excel_outputs(validation_directory, period)
        except Exception as e:
            failed.append(("Validación Excel", str(e)))

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
        print(f"      Ejecuta: python ending_files/generate_all_reports.py {period}")
    
    # Directorio de salida
    destination = Path(output_dir) if output_dir else project_root / "excel_final_files" / period
    print(f"\n📁 Archivos Excel guardados en: {destination}")

    if failed:
        print(f"\n⚠️  Proceso completado con {len(failed)} errores")
    else:
        print(f"\n🎉 Todos los archivos Excel generados exitosamente!")

    return {
        "successful": successful,
        "failed": failed,
        "status": "success" if not failed else "partial" if successful else "failed",
        "output_directory": str(destination),
        "generated_paths": [str(path) for path in generated_paths],
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Genera todos los archivos Excel para un período')
    parser.add_argument('period', help='Período del reporte (ej: 202502)')
    parser.add_argument('--csv-dir', default=None, help='Directorio de CSV del período')
    parser.add_argument('--output-dir', default=None, help='Directorio temporal o final de Excel')
    
    args = parser.parse_args()
    
    # Configurar logging para suprimir mensajes individuales de cada generador
    logging.basicConfig(level=logging.WARNING)
    
    try:
        result = generate_all_excel_reports(
            args.period,
            csv_dir=args.csv_dir,
            output_dir=args.output_dir,
        )
        sys.exit(0 if not result['failed'] else 1)
    except KeyboardInterrupt:
        print(f"\n🛑 Proceso interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)
