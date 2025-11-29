# Plan de Proyecto de Visualización - Integración con Superset

## Descripción General
Proyecto paralelo para crear dashboards interactivos usando Apache Superset para visualizar datos del mercado asegurador de los últimos 5 años.

## Estrategia de Datos

### Enfoque: Tablas con Datos Crudos
Mantenerlo simple - crear tablas con datos históricos crudos. Dejar que Superset maneje las agregaciones, cálculos y visualizaciones.

### Tablas Principales Necesarias

#### 1. Datos Operacionales (Primas/Siniestros)
- **Tabla de ramos** (nivel línea de negocio)
- **Tabla de subramos** (nivel sub-línea)
- **Tabla de compañías** (nivel compañía)

Todas conteniendo datos para los períodos históricos deseados (últimos 5 años recomendado).

#### 2. Datos Financieros/Patrimoniales
- **Tabla de conceptos patrimoniales** (expandida desde `base_otros_conceptos` actual)
  - Activos
  - Pasivos/Deudas
  - Capital/Patrimonio
  - Desglose de inversiones
  - Otros conceptos de balance

Todos los períodos incluidos.

#### 3. Dimensiones de Soporte (Opcional pero Recomendado)
- **Catálogo de períodos**: `periodo`, año, trimestre, etiquetas de fecha legibles
  - Facilita el filtrado por período en Superset
- **Catálogo de compañías**: `cia_id`, nombre, tipo/categoría
  - Útil si los nombres de compañías cambian con el tiempo

## Principios Clave

1. **Solo datos crudos** - Sin métricas pre-agregadas en las tablas
2. **Cobertura de períodos** - Incluir todos los períodos necesarios (5 años = ~20 trimestres)
3. **Consistencia** - Usar el mismo formato de período (YYYYPP) del sistema actual
4. **Simplicidad** - Dejar que Superset maneje cálculos, % de crecimiento, ratios, etc.

## Referencias a Lógica Existente

### Módulos Actuales de Creación de Tablas
Revisar estos archivos para patrones y lógica a replicar:

**Ramos/Subramos:**
- `modules/crea_tabla_ramos_corregida.py` - Lógica de agregación por ramos
- `modules/crea_tabla_subramos_corregida.py` - Lógica de agregación por subramos

**Nivel Compañía:**
- `modules/crea_tabla_cias_corregida.py` - Agregaciones a nivel compañía

**Patrimonial/Financiero:**
- `modules/crea_tabla_otros_conceptos.py` - Lógica actual de conceptos de balance
- Expandir conceptos basándose en datos disponibles en tabla `base_principal`

**Gestión de Períodos:**
- `modules/crea_tabla_ultimos_periodos.py` - Creación de tablas multi-período
- `modules/check_ultimos_periodos.py` - Listar períodos disponibles
- `modules/common.py` - Utilidades de formateo de períodos

### Esquema de Base de Datos
- **Tabla principal**: Revisar estructura en `initial_scripts/create_principal_table.py`
- **Mapeo de conceptos**: Ver `initial_scripts/create_conceptos_reportes.py`
- **Parámetros**: Revisar `initial_scripts/create_parametros_reportes.py`

### Carga de Datos
- `modules/carga_base_principal.py` - Cómo se procesan y cargan archivos MDB
- `utils/db_functions.py` - Funciones auxiliares de base de datos
- `utils/db_manager.py` - Gestión de conexiones

## Ideas de Dashboards (para Superset)

Una vez que las tablas de datos estén listas:

1. **Evolución de Participación de Mercado**
   - Top 10 compañías en 5 años
   - Gráficos de líneas mostrando tendencias de primas

2. **Solvencia y Salud Financiera**
   - Tendencias de ratios de solvencia con alertas de umbrales
   - Indicadores de adecuación de capital

3. **Rankings y Movimientos**
   - Quién subió/bajó en los rankings
   - Comparaciones período a período

4. **Performance por Ramo**
   - Qué ramos están creciendo/declinando
   - Cambios en composición del mercado

5. **Análisis Comparativo**
   - Compañía vs. promedios del mercado
   - Benchmarking de grupos de pares

## Pasos de Implementación (Futuro)

1. **Diseñar nuevo esquema de base de datos** para proyecto de visualización
2. **Crear proceso ETL** para poblar tablas históricas
   - Reutilizar lógica de los módulos listados arriba
   - Adaptar para carga batch de múltiples períodos
3. **Configurar Superset** y conectar a nueva base de datos
4. **Construir dashboards iniciales** (empezar con 2-3 métricas clave)
5. **Iterar y expandir** basándose en feedback

## Notas

- El sistema actual usa **formato YYYYPP** para períodos (ej: 202501, 202404)
- Los generadores CSV/Excel existentes en `ending_files/` y `excel_generators/` muestran qué métricas son importantes
- La Web UI en `app/` demuestra el workflow actual - podría inspirar procesos de actualización de datos

## Preguntas a Resolver Más Adelante

- ¿Qué "otros conceptos" específicos incluir más allá del conjunto actual?
- ¿Rango de tiempo: exactamente 5 años o configurable?
- ¿Frecuencia de actualización: actualizaciones batch trimestrales o incrementales?
- ¿Validación de datos: reutilizar lógica de comparación existente de `modules/compare_csv_reports.py`?
