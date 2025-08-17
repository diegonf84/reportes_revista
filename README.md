# Reportes del Mercado Asegurador

Sistema automatizado para la generación de reportes del sector asegurador.

## Instalación

Para ejecutar este proyecto, asegúrate de tener Python 3.11 instalado en tu sistema. Puedes descargarlo desde [python.org](https://www.python.org/downloads/).

Este proyecto utiliza [Conda](https://docs.conda.io/en/latest/) como sistema de gestión de paquetes y entornos. Asegúrate de tener Conda instalado en tu sistema para seguir estas instrucciones. Puedes instalar Conda a través de [Miniconda](https://docs.conda.io/en/latest/miniconda.html) o [Anaconda](https://www.anaconda.com/products/distribution).

Una vez instalado Python, sigue estos pasos para configurar tu entorno de desarrollo:

1. Clonar repositorio:
```bash
git clone https://github.com/diegonf84/reportes_revista
```

2. Crear y activar entorno Conda:
```bash
conda env create -f environment.yml
conda activate nombre_entorno
```

3. Instalar módulos locales:
```bash
pip install -e .
```

## Estructura del Proyecto
```
├── docs/                          # Documentación
│   └── MODULES.md                 # Documentación técnica detallada
│
├── ending_files/                  # FASE 2: Archivos CSV finales por período
│   ├── 202404/
│   ├── 202501/
│   ├── generate_all_reports.py    # Generador principal de CSV
│   └── report_definitions.json    # Definiciones de reportes
│
├── excel_final_files/            # FASE 3: Archivos Excel finales por período
│   ├── 202404/
│   └── 202501/
│
├── excel_generators/             # FASE 3: Generadores de reportes Excel
│   ├── apertura_por_subramos.py
│   ├── cuadro_principal.py
│   ├── ranking_comparativo.py
│   └── ... (8 generadores totales)
│
├── initial_scripts/              # Scripts de configuración inicial
│   ├── create_conceptos_reportes.py
│   ├── create_parametros_reportes.py
│   └── create_principal_table.py
│
├── mdb_files_to_load/           # Archivos MDB a procesar (formato YYYY-P.zip)
│   ├── 2024-4.mdb
│   ├── 2025-1.mdb
│   └── ...
│
├── modules/                      # FASE 1: Módulos principales (trabajan con períodos YYYYPP)
│   ├── common.py                 # Utilidades compartidas
│   ├── carga_base_principal.py   # Carga datos desde MDB
│   ├── check_cantidad_cias.py    # Verificación de compañías
│   ├── check_ultimos_periodos.py # Lista períodos disponibles
│   ├── crea_tabla_ultimos_periodos.py    # Tabla de períodos recientes
│   ├── crea_tabla_otros_conceptos.py     # Conceptos financieros
│   └── crea_tabla_subramos_corregida.py  # Tabla subramos corregida
│
├── utils/                       # Utilidades del sistema
│   ├── db_functions.py          # Funciones de base de datos
│   ├── db_manager.py            # Gestor de conexiones DB
│   ├── other_functions.py       # Funciones auxiliares
│   └── report_generator.py      # Generador de reportes
│
├── .env                         # Variables de entorno (DATABASE=...)
├── environment.yml              # Configuración entorno Conda
├── USAGE.md                     # Guía de uso práctica
└── setup.py                     # Configuración del paquete
```

## Uso Rápido

### Configuración Inicial
```bash
# 1. Configurar variables de entorno
echo "DATABASE=/ruta/a/tu/base_datos.db" > .env

# 2. Colocar archivos en mdb_files_to_load/
# Formato: YYYY-P.zip (ej: 2025-1.zip)
```

### Workflow Completo (3 Fases)

#### **Fase 1: Procesamiento de Datos**
```bash
# 1. Verificar períodos existentes
python modules/check_ultimos_periodos.py

# 2. Validar archivo antes de cargar
python modules/check_cantidad_cias.py 202501 202404

# 3. Cargar nuevo período
python modules/carga_base_principal.py 202501

# 4. Generar tablas de análisis
python modules/crea_tabla_ultimos_periodos.py --periodo_inicial 202301
python modules/crea_tabla_otros_conceptos.py
python modules/crea_tabla_subramos_corregida.py 202501
```

#### **Fase 2: Generación de CSV**
```bash
# 5. Generar reportes CSV
python ending_files/generate_all_reports.py --period 202501
```

#### **Fase 3: Generación de Excel**
```bash
# 6. Generar reportes Excel formateados
python excel_generators/cuadro_principal.py 202501
python excel_generators/ranking_comparativo.py 202501
# ... (otros generadores según necesidad)
```

### Documentación

- **[USAGE.md](USAGE.md)** - Guía práctica paso a paso con ejemplos
- **[docs/MODULES.md](docs/MODULES.md)** - Documentación técnica detallada

### Formato de Períodos

Todos los módulos usan períodos en formato **YYYYPP**:
- `202501` = Marzo 2025 (1er trimestre)
- `202502` = Junio 2025 (2do trimestre)
- `202503` = Septiembre 2025 (3er trimestre)
- `202504` = Diciembre 2025 (4to trimestre)

## Estado del Proyecto

### ✅ Completado
- **Fase 1:** Sistema de carga y procesamiento de datos desde archivos MDB
- **Fase 2:** Generación automática de reportes CSV configurables 
- **Fase 3:** Generadores de reportes Excel formateados y profesionales
- Validación y verificación de compañías con comparaciones
- Pipeline completo desde datos raw hasta reportes finales
- Documentación completa de las 3 fases
- Manejo consistente de períodos (YYYYPP)
- Testing de cálculos antes de producción

### 🔄 En Desarrollo
- Dashboard de visualización de datos
- API REST para acceso a reportes
- Automatización completa del pipeline

### 📋 Pendiente
- Incluir nombres completos de ramos, subramos y compañías
- Ampliar conceptos de reportes (primas cedidas, etc.)
- Implementar tests automatizados