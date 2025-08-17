# Guía de Uso - Módulos

Esta guía explica cómo usar cada módulo del sistema de reportes. Todos los módulos funcionan con **períodos** en formato `YYYYPP` donde:
- `YYYY` = Año (ej: 2025)
- `PP` = Trimestre (01, 02, 03, 04)

**Ejemplos de períodos válidos:**
- `202501` = Primer trimestre 2025 (Marzo)
- `202502` = Segundo trimestre 2025 (Junio)  
- `202503` = Tercer trimestre 2025 (Septiembre)
- `202504` = Cuarto trimestre 2025 (Diciembre)

## Configuración Inicial

### Variables de Entorno (.env)
Crear archivo `.env` con:
```bash
DATABASE=/ruta/a/tu/base_datos.db
```

### Preparación de Archivos
- Colocar archivos ZIP con datos MDB en `mdb_files_to_load/`
- Formato esperado: `YYYY-P.zip` (ej: `2025-1.zip`, `2025-3.zip`)

---

## Módulos Disponibles

### 1. **Verificación de Datos**

#### `check_ultimos_periodos.py`
**Propósito:** Lista todos los períodos disponibles en la base de datos

```bash
# Listar períodos disponibles
python modules/check_ultimos_periodos.py
```

**Salida esperada:**
```
Períodos disponibles en la base de datos:
- 202404 (Diciembre 2024)
- 202403 (Septiembre 2024)  
- 202402 (Junio 2024)
- 202401 (Marzo 2024)
```

#### `check_cantidad_cias.py`
**Propósito:** Verifica cuántas compañías tiene un archivo antes de cargarlo

```bash
# Verificar compañías en un período específico
python modules/check_cantidad_cias.py 202501

# Comparar con período anterior (recomendado)
python modules/check_cantidad_cias.py 202501 202404
```

**Salida esperada:**
```
El período 202501 tiene 89 compañías en la tabla Balance.

COMPARACIÓN DE COMPAÑÍAS
Archivo (período 202501): 89 compañías
Base de datos (período 202404): 87 compañías
===========================================
📋 COMPAÑÍAS NUEVAS EN ARCHIVO (2):
  - 0123: Nueva Seguros SA
  - 0456: Seguros del Futuro SA
```

### 2. **Carga de Datos**

#### `carga_base_principal.py`
**Propósito:** Carga datos de un período desde archivo MDB a la base de datos

```bash
# Cargar datos de un período específico
python modules/carga_base_principal.py 202501
```

**Qué hace:**
1. Busca archivo `2025-1.zip` en `mdb_files_to_load/`
2. Extrae tabla "Balance" del archivo MDB
3. Valida y transforma los datos
4. Inserta en tabla `datos_balance` de la base de datos

**Salida esperada:**
```
2025-01-15 10:30:45 - INFO - Archivo encontrado: /ruta/mdb_files_to_load/2025-1.zip
2025-01-15 10:30:45 - INFO - Iniciando carga del período 202501
2025-01-15 10:30:50 - INFO - Insertadas 125,847 filas del período 202501
```

### 3. **Procesamiento y Análisis**

#### `crea_tabla_ultimos_periodos.py`
**Propósito:** Crea tabla filtrada con datos de períodos recientes

```bash
# Usar últimos 2 años por defecto
python modules/crea_tabla_ultimos_periodos.py

# Especificar período inicial
python modules/crea_tabla_ultimos_periodos.py --periodo_inicial 202301
```

**Qué hace:**
- Crea tabla `base_balance_ultimos_periodos` 
- Filtra datos desde el período especificado
- Útil para análisis comparativos

#### `crea_tabla_otros_conceptos.py`
**Propósito:** Genera tabla con conceptos financieros agregados del último período

```bash
# Procesar conceptos del último período disponible
python modules/crea_tabla_otros_conceptos.py
```

**Qué hace:**
- Crea tabla `base_otros_conceptos`
- Agrega conceptos como: resultado técnico, financiero, patrimonio neto, etc.
- Usa el último período disponible en la base

#### `crea_tabla_subramos_corregida.py`
**Propósito:** Crea tabla de subramos con correcciones específicas por trimestre

```bash
# Procesar subramos para marzo (trimestre 1)
python modules/crea_tabla_subramos_corregida.py 202501

# Procesar subramos para junio (trimestre 2)
python modules/crea_tabla_subramos_corregida.py 202502

# Procesar subramos para septiembre (trimestre 3)
python modules/crea_tabla_subramos_corregida.py 202503

# Procesar subramos para diciembre (trimestre 4)  
python modules/crea_tabla_subramos_corregida.py 202504
```

**Qué hace:**
- Aplica lógica específica según el trimestre para normalizar períodos de 12 meses
- **Marzo:** marzo_actual - junio_anterior + diciembre_anterior
- **Junio:** junio_actual + diciembre_anterior - junio_anterior  
- **Septiembre:** comparación directa (sin corrección)
- **Diciembre:** diciembre_actual - junio_actual
- Maneja compañías especiales que cierran en diciembre (códigos 0829, 0541, 0686)

**Modo Testing (verificar cálculos antes de ejecutar):**
```bash
# Generar archivo CSV para verificar manualmente los cálculos
python modules/crea_tabla_subramos_corregida.py 202502 --test
```

**Salida del testing:**
- Crea archivo `modules/testing_data/202502_test_simple.csv`
- Muestra todas las columnas de períodos side-by-side
- Incluye cálculos paso a paso y fórmulas aplicadas
- Permite verificar manualmente antes de ejecutar en producción

---

## Generación de Reportes CSV

Después de procesar los datos con los módulos, el siguiente paso es generar los reportes en formato CSV.

### `generate_all_reports.py`
**Propósito:** Genera reportes CSV basados en las consultas definidas en `report_definitions.json`

```bash
# Generar todos los reportes CSV para un período
python ending_files/generate_all_reports.py --period 202501

# Generar un reporte específico
python ending_files/generate_all_reports.py --period 202501 --report cuadro_principal

# Especificar directorio de salida
python ending_files/generate_all_reports.py --period 202501 --output_dir ./reportes
```

**Reportes disponibles:**
- `cuadro_principal` - Cuadro principal por ramo y compañía
- `cuadro_nuevo` - Cuadro con datos patrimoniales
- `ganaron_perdieron` - Análisis de resultados técnicos y financieros
- `apertura_por_subramo` - Apertura detallada por subramo
- `primas_cedidas_reaseguro` - Análisis de cesión al reaseguro
- `ranking_comparativo` - Ranking comparativo de compañías
- `ranking_comparativo_por_ramo` - Ranking por ramo
- `sueldos_y_gastos` - Análisis de gastos operativos

**Archivos generados:**
- Se crean en `ending_files/{período}/`
- Formato: `{período}_{nombre_reporte}.csv`
- Ejemplo: `ending_files/202501/202501_cuadro_principal.csv`

**Dependencias de tablas:**
- `cuadro_principal`, `ganaron_perdieron`, `primas_cedidas_reaseguro`, `sueldos_y_gastos`: Requieren `base_subramos`
- `cuadro_nuevo`, `ganaron_perdieron`: Requieren `base_otros_conceptos`
- `apertura_por_subramo`, `ranking_comparativo`, `ranking_comparativo_por_ramo`: Requieren `base_subramos_corregida_actual`

---

## Generación de Reportes Excel

El paso final es convertir los archivos CSV en reportes Excel formateados.

### Generadores individuales por reporte
Cada tipo de reporte tiene su propio generador con formato específico:

```bash
# Generar Excel individual por tipo de reporte
python excel_generators/cuadro_principal.py 202501
python excel_generators/ranking_comparativo.py 202501
python excel_generators/ganaron_perdieron.py 202501
python excel_generators/apertura_por_subramos.py 202501
python excel_generators/primas_cedidas_reaseguro.py 202501
python excel_generators/ranking_comparativo_por_ramo.py 202501
python excel_generators/cuadro_nuevo.py 202501
python excel_generators/sueldos_y_gastos.py 202501
```

**Archivos generados:**
- Se crean en `excel_final_files/{período}/`
- Formato: `{período}_{nombre_reporte}.xlsx`
- Ejemplo: `excel_final_files/202501/202501_cuadro_principal.xlsx`

**Características de los Excel:**
- Formato profesional con estilos y bordes
- Fórmulas automáticas para totales y porcentajes
- Columnas auto-ajustadas
- Formateo numérico apropiado
- Headers formateados

**Dependencias:**
- Requieren los archivos CSV correspondientes en `ending_files/{período}/`
- Cada generador busca automáticamente su CSV de entrada

---

## Flujo de Trabajo Completo

### Proceso completo para nuevo período (3 fases):

#### **FASE 1: Procesamiento de Datos (modules)**
```bash
# 1. Verificar períodos existentes
python modules/check_ultimos_periodos.py

# 2. Verificar el archivo antes de cargar
python modules/check_cantidad_cias.py 202501 202404

# 3. Cargar los datos
python modules/carga_base_principal.py 202501

# 4. Crear tablas de análisis
python modules/crea_tabla_ultimos_periodos.py --periodo_inicial 202301
python modules/crea_tabla_otros_conceptos.py

# 5. TESTING: Verificar cálculos de subramos antes de ejecutar
python modules/crea_tabla_subramos_corregida.py 202501 --test

# 6. Si los cálculos son correctos, ejecutar en producción
python modules/crea_tabla_subramos_corregida.py 202501
```

#### **FASE 2: Generación de CSV**
```bash
# 7. Generar todos los reportes CSV
python ending_files/generate_all_reports.py --period 202501

# O generar reportes específicos:
python ending_files/generate_all_reports.py --period 202501 --report cuadro_principal
python ending_files/generate_all_reports.py --period 202501 --report ranking_comparativo
```

#### **FASE 3: Generación de Excel**
```bash
# 8. Generar todos los archivos Excel formateados
python excel_generators/cuadro_principal.py 202501
python excel_generators/cuadro_nuevo.py 202501
python excel_generators/ganaron_perdieron.py 202501
python excel_generators/apertura_por_subramos.py 202501
python excel_generators/primas_cedidas_reaseguro.py 202501
python excel_generators/ranking_comparativo.py 202501
python excel_generators/ranking_comparativo_por_ramo.py 202501
python excel_generators/sueldos_y_gastos.py 202501
```

### Para regenerar solo reportes (datos ya procesados):

#### **Solo CSV:**
```bash
# Regenerar todos los reportes CSV
python ending_files/generate_all_reports.py --period 202501

# Regenerar reporte específico
python ending_files/generate_all_reports.py --period 202501 --report ranking_comparativo
```

#### **Solo Excel:**
```bash
# Regenerar Excel específico (requiere CSV previo)
python excel_generators/ranking_comparativo.py 202501
```

### Para análisis de datos existentes:

```bash
# Verificar qué períodos tenemos
python modules/check_ultimos_periodos.py

# Regenerar tablas de análisis
python modules/crea_tabla_otros_conceptos.py
python modules/crea_tabla_subramos_corregida.py 202501

# Regenerar reportes completos
python ending_files/generate_all_reports.py --period 202501
```

---

## Solución de Problemas

### Error: "DATABASE environment variable not set"
```bash
# Crear archivo .env con la ruta a tu base de datos
echo "DATABASE=/ruta/a/tu/base_datos.db" > .env
```

### Error: "File 2025-1.zip not found"
- Verificar que el archivo esté en `mdb_files_to_load/`
- Verificar formato del nombre: `YYYY-P.zip`

### Error: "Period must be 6 digits (YYYYPP)"
- Usar formato correcto: 202501 (no 20251 ni 2025-1)

### Error: "El período 202501 ya existe en la base de datos"
- El período ya fue cargado anteriormente
- Para recargar, eliminar registros existentes primero

---

## Archivos Obsoletos

Los siguientes archivos están obsoletos y no deben usarse:
- `crea_tabla_subramos_corregida_actual_diciembre.py` ❌
- `crea_tabla_subramos_corregida_actual_marzo.py` ❌

Usar en su lugar: `crea_tabla_subramos_corregida.py` ✅