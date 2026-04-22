# Reportes del Mercado Asegurador

Sistema automatizado para la generación de reportes del sector asegurador.

**🆕 Ahora disponible en dos versiones:**
- **Console v1.0**: Herramientas completas de línea de comandos (existente)
- **Web UI v2.0**: Interfaz web moderna para gestión de compañías (nuevo)

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
conda activate revista_tr_cuadros
```

3. Instalar módulos locales:
```bash
pip install -e .
```

## Estructura del Proyecto
```
├── app/                          # 🆕 WEB UI v2.0: Interfaz web Flask
│   ├── __init__.py
│   ├── app.py                    # Aplicación Flask principal
│   ├── routes/                   # Rutas web
│   │   ├── companies.py          # Gestión de compañías  
│   │   └── data_processing.py    # Procesamiento de datos (verificación, carga, tablas, reportes)
│   ├── templates/                # Plantillas HTML
│   │   ├── base.html             # Plantilla base con Bootstrap
│   │   ├── dashboard.html        # Dashboard principal
│   │   ├── companies/            # Gestión de compañías
│   │   └── data_processing/      # Procesamiento de datos (verificación, carga, tablas, reportes)
│   ├── static/                   # CSS, JS, archivos estáticos
│   │   ├── css/custom.css
│   │   └── js/main.js
│   └── forms/                    # Formularios Flask-WTF
│       ├── company_forms.py      # Formularios de compañías
│       └── processing_forms.py   # Formularios de procesamiento de datos y reportes
│
├── docs/                          # Documentación
│   ├── MODULES.md                 # Documentación técnica detallada
│   └── WEB_UI_PLAN.md             # Plan y estado del Web UI
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
│   └── ... (13 generadores totales)
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
├── .env                         # Variables de entorno (DATABASE=... + WEB UI config)
├── environment.yml              # Configuración entorno Conda (incluye Flask)
├── USAGE.md                     # Guía de uso práctica (Console + Web UI)
└── setup.py                     # Configuración del paquete
```

## Uso Rápido

### Configuración Inicial
```bash
# 1. Configurar variables de entorno
echo "DATABASE=../revista_tr_database.db" > .env
echo "FLASK_SECRET_KEY=tu-clave-secreta" >> .env
echo "FLASK_PORT=5000" >> .env
echo "FLASK_DEBUG=True" >> .env

# 2. Colocar archivos en mdb_files_to_load/
# Formato: YYYY-P.zip (ej: 2025-1.zip)
```

## 🚀 Opciones de Uso

### **Opción A: Web UI v2.0 (Recomendado para gestión de compañías)**
```bash
# Iniciar interfaz web
python app/app.py

# Abrir navegador en:
http://127.0.0.1:5000
```

**Funcionalidades disponibles:**
- ✅ **Dashboard del sistema** con estadísticas generales
- ✅ **Gestión completa de compañías** (CRUD)
  - Agregar nuevas compañías
  - Editar compañías existentes  
  - Eliminar compañías
  - Búsqueda y filtrado
- ✅ **Procesamiento completo de datos** (3 módulos principales)
  - **Verificación de Datos**: Validar archivos MDB y comparar compañías
  - **Carga de Datos**: Procesar archivos MDB hacia base de datos
  - **Procesamiento de Tablas**: Crear tablas de análisis (períodos, conceptos, subramos)
- ✅ **Validación de datos** en tiempo real
- ✅ **Interfaz moderna** con Bootstrap
- ✅ **Manejo de errores** inteligente y mensajes informativos
- ✅ **Generación completa de reportes** (CSV + Excel) en un solo proceso

### **Opción B: Console v1.0 (Workflow completo de procesamiento)**

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

#### **Fase 4: Export a Parquet + Upload a S3 (visualización)**
```bash
# 7. Generar los 3 parquet históricos (5 años) y subirlos a S3 en un solo paso
python export_parquet/run_all_and_upload.py --max_period 202503
```

Este orquestador ejecuta en orden:
- `export_subramos_to_parquet`
- `export_ramos_to_parquet`
- `export_otros_conceptos_to_parquet`
- `upload_parquet_files` (lee `S3_BUCKET`, `S3_PREFIX`, `AWS_*` desde `.env`)

Los scripts individuales (`export_subramos_parquet.py`, `export_ramos_parquet.py`,
`export_otros_conceptos_parquet.py`, `upload_to_s3.py`) siguen funcionando standalone
si se necesitan por separado.

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
- **Console v1.0 (Sistema completo)**
  - **Fase 1:** Sistema de carga y procesamiento de datos desde archivos MDB
  - **Fase 2:** Generación automática de reportes CSV configurables 
  - **Fase 3:** Generadores de reportes Excel formateados y profesionales
  - Validación y verificación de compañías con comparaciones
  - Pipeline completo desde datos raw hasta reportes finales
  - Manejo consistente de períodos (YYYYPP)
  - Testing de cálculos antes de producción

- **Web UI v2.0 (Interfaz moderna)**
  - ✅ **Dashboard del sistema** con estadísticas en tiempo real
  - ✅ **Gestión completa de compañías** (CRUD con validación)
  - ✅ **Procesamiento completo de datos** (3 módulos principales)
    - **Verificación de Datos**: Upload MDB, validar compañías, comparar períodos
    - **Carga de Datos**: Procesar archivos MDB, manejo inteligente de errores
    - **Procesamiento de Tablas**: Crear tablas de análisis con workflow guiado
  - ✅ **Generación unificada de reportes** (CSV + Excel)
    - **Un solo paso**: Ingreso de período y generación automática de todos los reportes
    - **Progreso en tiempo real**: Seguimiento visual del proceso de generación
    - **12 tipos de reportes CSV**: Cuadro principal, ranking, apertura por subramo, etc.
    - **Archivos organizados**: CSV en ending_files/, Excel en excel_final_files/
  - ✅ **Interfaz responsive** con Bootstrap 5
  - ✅ **Búsqueda y filtrado** de compañías
  - ✅ **Integración completa** con base de datos existente
  - ✅ **Compatibilidad total** con sistema console v1.0

### 🔄 En Desarrollo (Web UI v2.0 - Próximas fases)
- **Dashboard avanzado** con visualizaciones y gráficos
- **API REST** para acceso programático a reportes
- **Gestión de archivos** con explorador web integrado
- **Gestión de períodos** desde interfaz web

### 📋 Pendiente
- Implementación de nombres históricos de compañías (snapshots por período)
- Ampliar conceptos de reportes (primas cedidas, etc.)
- Implementar tests automatizados
- Incluir nombres completos de ramos, subramos y compañías