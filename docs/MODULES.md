# Documentación Detallada de Módulos

Esta documentación proporciona información técnica detallada sobre cada módulo del sistema.

## Arquitectura del Sistema

**🚀 Sistema Dual:**
- **Console v1.0**: Módulos Python para procesamiento masivo de datos
- **Web UI v2.0**: Interfaz Flask para gestión de master data

## Índice

1. [Web UI v2.0 - Aplicación Flask](#web-ui-v20---aplicación-flask)
2. [Console v1.0 - Módulos de Verificación](#console-v10---módulos-de-verificación)
3. [Console v1.0 - Módulos de Carga](#console-v10---módulos-de-carga)
4. [Console v1.0 - Módulos de Procesamiento](#console-v10---módulos-de-procesamiento)
5. [Utilidades Compartidas](#utilidades-compartidas)

---

## Web UI v2.0 - Aplicación Flask

### Arquitectura

**Patrón MVC con Blueprints:**
```
app/
├── app.py                    # Aplicación principal Flask
├── routes/                   # Controladores (Blueprints)
├── templates/                # Vistas (HTML + Jinja2)
├── static/                   # Assets (CSS, JS)
└── forms/                    # Modelos de formularios (WTForms)
```

### `app/app.py`

**Descripción:** Aplicación Flask principal que inicializa el servidor web.

**Características:**
- Configuración automática desde variables de entorno
- Registro de blueprints para modularidad
- Manejo de errores 404/500
- Integración con logging del sistema existente

**Variables de entorno requeridas:**
```bash
FLASK_SECRET_KEY=clave-secreta
FLASK_PORT=5000
FLASK_DEBUG=True
DATABASE=/ruta/a/base_datos.db
```

**Inicio:**
```bash
python app/app.py
```

### `app/routes/companies.py`

**Descripción:** Blueprint para gestión CRUD de compañías.

**Rutas implementadas:**
- `GET /companies/` - Lista todas las compañías
- `GET /companies/add` - Formulario nueva compañía
- `POST /companies/add` - Procesar nueva compañía
- `GET /companies/edit/<cod_cia>` - Formulario editar compañía
- `POST /companies/edit/<cod_cia>` - Procesar edición
- `POST /companies/delete/<cod_cia>` - Eliminar compañía

**Validaciones implementadas:**
- Código único de compañía
- Campos obligatorios
- Tipos de compañía válidos (Generales, Vida, Retiro, ART, M.T.P.P.)
- Rangos numéricos (1-9999)

**Integración con base de datos:**
- Uso directo de SQLite sin ORM
- Transacciones seguras con context managers
- Manejo de errores de base de datos

### `app/forms/company_forms.py`

**Descripción:** Formularios Flask-WTF para validación client/server-side.

**Formularios definidos:**
- `CompanyForm`: Agregar/editar compañías
  - `cod_cia`: IntegerField con validación de rango
  - `nombre_corto`: StringField con validación de longitud
  - `tipo_cia`: SelectField con opciones predefinidas

**Validadores aplicados:**
- `DataRequired`: Campos obligatorios
- `NumberRange`: Código entre 1-9999
- `Length`: Límites de caracteres

### `app/templates/`

**Estructura de plantillas:**
- `base.html`: Plantilla base con Bootstrap 5
- `dashboard.html`: Dashboard principal con estadísticas
- `companies/list.html`: Lista de compañías con búsqueda
- `companies/add.html`: Formulario nueva compañía
- `companies/edit.html`: Formulario editar compañía

**Características de UI:**
- Responsive design con Bootstrap 5
- Búsqueda en tiempo real con JavaScript
- Validación visual de formularios
- Badges de colores por tipo de compañía
- Confirmaciones de eliminación

### `app/static/`

**Assets estáticos:**
- `css/custom.css`: Estilos personalizados
- `js/main.js`: JavaScript para interactividad

**Funcionalidades JavaScript:**
- Búsqueda de tabla en tiempo real
- Validación de formularios
- Confirmaciones de eliminación
- Tooltips y elementos interactivos

---

## Console v1.0 - Módulos de Verificación

### `check_ultimos_periodos.py`

**Descripción:** Lista todos los períodos disponibles en la base de datos con información estadística.

**Parámetros:** Ninguno

**Tablas consultadas:**
- `datos_balance`

**Salida:** Imprime lista de períodos ordenados del más reciente al más antiguo

**Ejemplo de uso:**
```bash
python modules/check_ultimos_periodos.py
```

**Código de ejemplo:**
```python
from modules.check_ultimos_periodos import list_available_periods

# Obtener períodos programáticamente
periods = list_available_periods()
print(f"Último período: {periods[0]}")
```

---

### `check_cantidad_cias.py`

**Descripción:** Verifica la cantidad de compañías en un archivo MDB y opcionalmente compara con un período anterior.

**Parámetros:**
- `periodo_archivo` (requerido): Período del archivo a verificar
- `periodo_anterior` (opcional): Período para comparación

**Archivos requeridos:**
- `mdb_files_to_load/YYYY-P.zip` donde P corresponde al trimestre

**Tablas consultadas:**
- `datos_balance` (si se especifica período anterior)
- `datos_companias` (para nombres de compañías)

**Validaciones realizadas:**
- Formato de período (YYYYPP)
- Existencia del archivo ZIP
- Acceso a tabla Balance en el MDB

**Ejemplo de uso:**
```bash
# Solo verificar archivo
python modules/check_cantidad_cias.py 202501

# Comparar con período anterior
python modules/check_cantidad_cias.py 202501 202404
```

**Casos de uso típicos:**
- Validación antes de carga masiva
- Detección de compañías nuevas o faltantes
- Control de calidad de archivos

---

## Console v1.0 - Módulos de Carga

### `carga_base_principal.py`

**Descripción:** Carga datos desde archivos MDB hacia la tabla principal de la base de datos.

**Parámetros:**
- `periodo` (requerido): Período a cargar en formato YYYYPP

**Archivos requeridos:**
- `mdb_files_to_load/YYYY-P.zip`

**Tablas de destino:**
- `datos_balance`

**Proceso de transformación:**
1. **Extracción:** Lee tabla "Balance" del archivo MDB
2. **Limpieza:** Elimina columnas innecesarias
3. **Transformación:**
   - Convierte período de formato "YYYY-P" a YYYYPP
   - Normaliza códigos de compañía con ceros a la izquierda
   - Elimina registros con importe = 0
   - Limpia valores nulos en cod_subramo
4. **Validación:** Verifica tipos de datos esperados
5. **Carga:** Inserta en tabla datos_balance

**Validaciones:**
- Período no existe previamente en la base
- Tipos de datos correctos
- Archivo ZIP existe y es accesible

**Ejemplo de uso:**
```bash
python modules/carga_base_principal.py 202501
```

**Estructura de datos esperada:**
```python
tipos_esperados = {
    'cod_cia': 'object',      # Código de compañía (ej: "0123")
    'periodo': 'int64',       # Período (ej: 202501)
    'cod_subramo': 'object',  # Código de subramo
    'importe': 'int64',       # Importe en pesos
    'cod_cuenta': 'object'    # Código de cuenta contable
}
```

---

## Console v1.0 - Módulos de Procesamiento

### `crea_tabla_ultimos_periodos.py`

**Descripción:** Crea tabla filtrada con datos de períodos recientes para análisis comparativos.

**Parámetros:**
- `--periodo_inicial` (opcional): Período desde el cual filtrar. Por defecto: últimos 2 años

**Tablas de origen:**
- `datos_balance`

**Tablas de destino:**
- `base_balance_ultimos_periodos`

**Lógica de filtrado:**
- Si no se especifica período inicial: usa año actual - 2 años
- Incluye todos los períodos >= período inicial

**Ejemplo de uso:**
```bash
# Últimos 2 años (por defecto)
python modules/crea_tabla_ultimos_periodos.py

# Desde período específico
python modules/crea_tabla_ultimos_periodos.py --periodo_inicial 202301
```

**Casos de uso:**
- Preparar datos para reportes comparativos
- Reducir tamaño de consultas en análisis
- Crear snapshots temporales

---

### `crea_tabla_otros_conceptos.py`

**Descripción:** Genera tabla agregada con conceptos financieros del último período disponible.

**Parámetros:** Ninguno (usa último período automáticamente)

**Tablas de origen:**
- `base_balance_ultimos_periodos`
- `conceptos_reportes`
- `parametros_reportes`

**Tablas de destino:**
- `base_otros_conceptos`

**Conceptos calculados:**
- `resultado_tecnico`
- `resultado_financiero`
- `resultado_operaciones`
- `impuesto_ganancias`
- `deudas_con_asegurados`
- `deudas_con_asegurados_ac_reaseguros`
- `disponibilidades`
- `inmuebles_inversion`
- `inmuebles_uso_propio`
- `inversiones`
- `patrimonio_neto`

**Proceso de cálculo:**
1. Obtiene último período de base_balance_ultimos_periodos
2. Filtra conceptos que NO son por subramo
3. Aplica mapeos de códigos de cuenta y signos
4. Agrupa por compañía y período
5. Suma importes según configuración

**Ejemplo de uso:**
```bash
python modules/crea_tabla_otros_conceptos.py
```

---

### `crea_tabla_subramos_corregida.py`

**Descripción:** Crea tabla de subramos con correcciones específicas según el trimestre.

**Parámetros:**
- `periodo` (requerido): Período a procesar

**Tablas de origen:**
- `base_subramos`

**Tablas de destino:**
- `base_subramos_corregida_actual`

**Lógica por trimestre:**

#### Trimestre 1 (Marzo)
- **Compañías especiales** (0829, 0541, 0686):
  - Primas = Marzo_actual - Junio_anterior + Diciembre_anterior
  - Compara con: Marzo_anterior - Junio_anterior + Diciembre_anterior
- **Resto de compañías**: Comparación directa marzo vs marzo anterior

#### Trimestre 4 (Diciembre)
- **Compañías especiales**:
  - Primas = Diciembre_actual - Junio_actual  
  - Compara con: Diciembre_anterior - Junio_anterior
- **Resto de compañías**: Comparación directa diciembre vs diciembre anterior

#### Trimestres 2 y 3
- Comparación directa para todas las compañías

**Ejemplo de uso:**
```bash
# Procesar marzo 2025
python modules/crea_tabla_subramos_corregida.py 202501

# Procesar junio 2025
python modules/crea_tabla_subramos_corregida.py 202502

# Procesar diciembre 2025
python modules/crea_tabla_subramos_corregida.py 202504

# MODO TESTING: Verificar cálculos antes de ejecutar
python modules/crea_tabla_subramos_corregida.py 202502 --test
```

**Columnas de salida:**
- `cod_cia`: Código de compañía
- `cod_subramo`: Código de subramo
- `primas_emitidas`: Primas del período actual (corregidas)
- `primas_emitidas_anterior`: Primas del período anterior (corregidas)

**Modo Testing:**
El parámetro `--test` genera un archivo CSV (`modules/testing_data/{periodo}_test_simple.csv`) con:
- Todas las columnas de períodos involucrados side-by-side
- Cálculos paso a paso para compañías especiales
- Fórmulas aplicadas para verificación manual
- Permite validar la lógica antes de ejecutar en producción

**Estructura del archivo de testing:**
```csv
cod_cia,cod_subramo,periodo_procesado,trimestre,actual_T2,diciembre_anterior,junio_anterior,calculo_actual,formula
0829,01,202502,2,1000,2000,750,2250,"actual_T2 + diciembre_anterior - junio_anterior"
```

---

## Utilidades Compartidas

### `common.py`

**Funciones principales:**

#### `validate_period(periodo: int)`
Valida formato YYYYPP con rangos razonables (2020-2030, trimestres 1-4).

#### `periodo_to_filename(periodo: int) -> str`
Convierte período interno (202501) a nombre de archivo (2025-1.zip).

#### `find_file_in_directory(directorio: Path, filename: str) -> Path`
Busca archivo con mensajes de error útiles listando archivos disponibles.

#### `get_mdb_files_directory() -> Path`
Retorna ruta estándar al directorio mdb_files_to_load.

#### `setup_logging(level: int = logging.INFO)`
Configura logging consistente para todos los módulos.

#### `format_number(num: int) -> str`
Formatea números con separadores de miles para mejor legibilidad.

---

## Flujos de Datos

### Flujo de Procesamiento Completo (Sistema Dual)

#### **Opción A: Web UI v2.0 + Console v1.0 (Híbrido)**
```
WEB UI: Gestión de Master Data
app/routes/companies.py → datos_companias (CRUD completo)
                        ↓
CONSOLE: Procesamiento de Datos (3 Fases)
FASE 1: Archivo MDB → carga_base_principal.py → datos_balance
                   ↓
       datos_balance → crea_tabla_ultimos_periodos.py → base_balance_ultimos_periodos
                   ↓
       base_balance_ultimos_periodos → crea_tabla_otros_conceptos.py → base_otros_conceptos
                   ↓
       base_subramos → crea_tabla_subramos_corregida.py → base_subramos_corregida_actual
                   ↓
FASE 2: generate_all_reports.py → CSV Reports (ending_files/{period}/)
                   ↓
FASE 3: excel_generators/*.py → Excel Reports (excel_final_files/{period}/)
```

#### **Opción B: Solo Console v1.0 (Tradicional)**
```
FASE 1: PROCESAMIENTO DE DATOS (modules/)
Archivo MDB → carga_base_principal.py → datos_balance
                                     ↓
datos_balance → crea_tabla_ultimos_periodos.py → base_balance_ultimos_periodos
                                               ↓
base_balance_ultimos_periodos → crea_tabla_otros_conceptos.py → base_otros_conceptos
                             ↓
base_subramos → crea_tabla_subramos_corregida.py → base_subramos_corregida_actual
                                                 ↓
FASE 2: GENERACIÓN CSV (ending_files/)
base_subramos + base_otros_conceptos + base_subramos_corregida_actual
                ↓
generate_all_reports.py → CSV Reports (ending_files/{period}/)
                ↓
FASE 3: GENERACIÓN EXCEL (excel_generators/)
CSV Reports → excel_generators/*.py → Excel Reports (excel_final_files/{period}/)
```

### Flujo de Verificación
```
Archivo MDB → check_cantidad_cias.py → Validación
datos_balance → check_ultimos_periodos.py → Lista de períodos
```

---

## Pipeline de Generación de Reportes

### Fase 2: Generación de CSV

#### `generate_all_reports.py`
**Ubicación:** `ending_files/generate_all_reports.py`

**Propósito:** Ejecuta consultas SQL definidas en JSON para generar reportes CSV.

**Parámetros:**
- `--period`: Período en formato YYYYPP
- `--report`: Reporte específico (opcional)
- `--output_dir`: Directorio de salida (por defecto: `./`)
- `--definitions`: Archivo JSON de definiciones (por defecto: `report_definitions.json`)

**Archivo de definiciones (`report_definitions.json`):**
Contiene la configuración de cada reporte:
```json
{
  "nombre_reporte": {
    "query": ["SELECT...", "FROM...", "WHERE periodo = '{period}'"],
    "int_columns": ["columna1", "columna2"],
    "separator": ";",
    "decimal": ","
  }
}
```

**Reportes disponibles:**
- `cuadro_principal`: Análisis por ramo con métricas de siniestralidad
- `cuadro_nuevo`: Datos patrimoniales y financieros
- `ganaron_perdieron`: Resultados técnicos y financieros
- `apertura_por_subramo`: Concentración por subramo con porcentajes
- `primas_cedidas_reaseguro`: Análisis de cesión y retención
- `ranking_comparativo`: Ranking de compañías con variación anual
- `ranking_comparativo_por_ramo`: Ranking por ramo con variación
- `sueldos_y_gastos`: Análisis de estructura de gastos

**Dependencias de tablas:**
```
cuadro_principal     → base_subramos, datos_companias, datos_ramos_subramos
cuadro_nuevo         → base_otros_conceptos, datos_companias
ganaron_perdieron    → base_subramos, base_otros_conceptos, datos_companias
apertura_por_subramo → base_subramos_corregida_actual, datos_companias, datos_ramos_subramos
primas_cedidas_reaseguro → base_subramos, datos_companias
ranking_comparativo  → base_subramos_corregida_actual, datos_companias
ranking_comparativo_por_ramo → base_subramos_corregida_actual, datos_companias, datos_ramos_subramos
sueldos_y_gastos     → base_subramos, datos_companias
```

### Fase 3: Generación de Excel

#### Generadores individuales
**Ubicación:** `excel_generators/`

Cada reporte tiene su generador específico que:
1. Lee el archivo CSV correspondiente de `ending_files/{period}/`
2. Aplica formato profesional (estilos, bordes, alineación)
3. Calcula totales y subtotales automáticamente
4. Genera archivo Excel en `excel_final_files/{period}/`

**Generadores disponibles:**
- `cuadro_principal.py`: Genera Excel con formato por ramos
- `cuadro_nuevo.py`: Excel con datos patrimoniales
- `ganaron_perdieron.py`: Excel de análisis de resultados
- `apertura_por_subramos.py`: Excel con concentración por subramo
- `primas_cedidas_reaseguro.py`: Excel de análisis de cesión
- `ranking_comparativo.py`: Excel de ranking con totales por tipo
- `ranking_comparativo_por_ramo.py`: Excel de ranking por ramo
- `sueldos_y_gastos.py`: Excel de estructura de gastos

**Características comunes:**
- Headers formateados con estilos profesionales
- Formateo numérico apropiado (miles, decimales, porcentajes)
- Bordes y alineación consistente
- Totales y subtotales automáticos
- Columnas auto-ajustadas
- Mapeo de nombres para presentación

**Ejemplo de uso:**
```bash
# Generar Excel específico
python excel_generators/ranking_comparativo.py 202501

# El generador busca automáticamente:
# - Input: ending_files/202501/202501_ranking_comparativo.csv
# - Output: excel_final_files/202501/202501_ranking_comparativo.xlsx
```

**Manejo de errores comunes:**
- `FileNotFoundError`: CSV no encontrado - verificar que se ejecutó la fase 2
- Formatos de datos incorrectos - verificar separadores y decimales en CSV
- Problemas de encoding - archivos deben estar en UTF-8

---

## Manejo de Errores

### Errores Comunes y Soluciones

**`ValueError: Period must be 6 digits (YYYYPP)`**
- Causa: Formato de período incorrecto
- Solución: Usar formato YYYYPP (ej: 202501, no 20251)

**`FileNotFoundError: File 2025-1.zip not found`**
- Causa: Archivo no existe en mdb_files_to_load/
- Solución: Verificar nombre y ubicación del archivo

**`sqlite3.Error: UNIQUE constraint failed`**
- Causa: Período ya existe en la base de datos
- Solución: Eliminar datos existentes o usar período diferente

**`ValueError: Error en los tipos de datos luego de transformar`**
- Causa: Datos del archivo no cumplen tipos esperados
- Solución: Verificar integridad del archivo MDB

---

## Configuración de Base de Datos

### Tablas Principales

#### `datos_balance`
```sql
CREATE TABLE datos_balance (
    cod_cia TEXT,
    periodo INTEGER,
    cod_subramo TEXT,
    importe INTEGER,
    cod_cuenta TEXT
);
```

#### `base_balance_ultimos_periodos`
Misma estructura que `datos_balance`, pero filtrada por períodos recientes.

#### `base_otros_conceptos`
```sql
CREATE TABLE base_otros_conceptos (
    cod_cia TEXT,
    periodo INTEGER,
    resultado_tecnico INTEGER,
    resultado_financiero INTEGER,
    resultado_operaciones INTEGER,
    impuesto_ganancias INTEGER,
    deudas_con_asegurados INTEGER,
    deudas_con_asegurados_ac_reaseguros INTEGER,
    disponibilidades INTEGER,
    inmuebles_inversion INTEGER,
    inmuebles_uso_propio INTEGER,
    inversiones INTEGER,
    patrimonio_neto INTEGER
);
```

#### `base_subramos_corregida_actual`
```sql
CREATE TABLE base_subramos_corregida_actual (
    cod_cia TEXT,
    cod_subramo TEXT,
    primas_emitidas INTEGER,
    primas_emitidas_anterior INTEGER
);
```