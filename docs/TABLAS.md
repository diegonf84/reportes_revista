# Tablas de la base de datos

Documento de referencia sobre las tablas que viven en `revista_tr_database.db` (SQLite, ruta definida por la variable de entorno `DATABASE`). Está pensado como guía de lectura: explica para qué existe cada tabla, de dónde sale, qué columnas son no-obvias y con quién se relaciona.

Convenciones generales:
- **Período `YYYYPP`**: año + trimestre fiscal (`01`=marzo, `02`=junio, `03`=septiembre, `04`=diciembre). Ver `GLOSARIO.md`.
- **`cod_cia`**: código de compañía aseguradora, texto de 4 dígitos con ceros a la izquierda (`'0002'`, `'0829'`).
- **`cod_subramo`** / **`cod_cuenta`**: códigos contables del plan de cuentas SSN, en formato texto con puntos (`'1.010.99'`).
- **Compañías especiales**: `'0829'`, `'0541'`, `'0686'` cierran en diciembre, no en junio. Aparecen como caso particular en todas las tablas `*_corregida_actual`.

---

## 1. Tablas fuente

Datos originales cargados desde archivos externos (MDB de SSN, CSVs). Son la verdad y no se reescriben mediante el pipeline de análisis.

### `datos_balance`
- **Propósito**: granularidad máxima del balance contable por compañía, período, subramo y cuenta. Es la fuente única de verdad sobre primas, siniestros, gastos y conceptos financieros.
- **Origen**: cargada por `modules/carga_base_principal.py` desde archivos `.mdb` en `mdb_files_to_load/`. Schema definido por `initial_scripts/create_principal_table.py`.
- **Columnas clave**:
  - `cod_cia` (TEXT) — compañía.
  - `periodo` (INTEGER) — formato `YYYYPP`.
  - `cod_cuenta` (TEXT) — código contable que se mapea a conceptos vía `parametros_reportes`.
  - `cod_subramo` (TEXT) — subramo asociado a la cuenta (puede no aplicar para conceptos patrimoniales).
  - `importe` (REAL) — valor en pesos. **Crudo, sin signo aplicado**: el signo lo decide el mapeo `parametros_reportes.signo`.
- **Relaciones**: alimenta a `base_balance_ultimos_periodos`. Vinculada por `cod_cia` con `datos_companias`, por `cod_subramo` con `datos_ramos_subramos`, por `cod_cuenta` con `parametros_reportes`.
- **Advertencias**:
  - No tiene mapeos de negocio aplicados. Para obtener "primas emitidas" hay que multiplicar `importe * signo` filtrando por `cod_cuenta` según el concepto.
  - Es la tabla más voluminosa; consultar siempre filtrando por `periodo` o pasando por `base_balance_ultimos_periodos`.

### `monthly_ipc_data`
- **Propósito**: índice IPC mensual para ajustes por inflación.
- **Origen**: `initial_scripts/create_ipc_table.py` lee `data_base_carga_ipc.csv` (separador `;`, decimal `,`).
- **Columnas**: `periodo` (INTEGER, **formato `YYYYMM`** — distinto al resto del proyecto), `indice_ipc` (REAL).
- **Advertencias**:
  - El `periodo` acá es **mensual** (`YYYYMM`), no `YYYYPP`. No se puede joinear directo contra otras tablas sin convertir.
  - Para análisis trimestral usar `quarter_ipc_data` (también creada por el mismo script).

---

## 2. Tablas de configuración

Catálogos / mapeos manuales que definen el comportamiento del pipeline. Se cargan una sola vez (o se actualizan rara vez) y son inputs del cálculo, no resultados.

### `conceptos_reportes`
- **Propósito**: define qué conceptos de negocio existen y a qué reporte / referencia pertenecen, y si el concepto se calcula a nivel de subramo o no.
- **Origen**: `initial_scripts/create_conceptos_reportes.py` (carga inicial de 5 conceptos de subramo) + `initial_scripts/insert_concepts.py` (extras como conceptos patrimoniales).
- **Columnas**:
  - `id` (INTEGER PK autoincremental).
  - `reporte` (TEXT) — agrupador legacy (`'anexo12-am'`, `'anexo13-b'`, `'resultados'`, `'pasivo'`, etc.). Coincide con la columna `reporte` en `parametros_reportes` para hacer JOIN.
  - `referencia` (TEXT) — sub-clave dentro del reporte (`'ref1'`, `'ref2'`, ...). Junto con `reporte` forma la clave de join contra `parametros_reportes`.
  - `concepto` (TEXT) — nombre lógico del concepto que termina siendo nombre de columna en `base_subramos` / `base_otros_conceptos` (ej: `primas_emitidas`, `resultado_tecnico`).
  - `es_subramo` (BOOLEAN) — **muy importante**: si es `1/TRUE`, el concepto se calcula en `base_subramos` y `base_ramos`; si es `0/FALSE`, se calcula en `base_otros_conceptos` (un solo período, agrupado solo por `cod_cia`).
- **Relaciones**: clave `(reporte, referencia)` joinea con `parametros_reportes`.
- **Advertencias**:
  - Si agregás un concepto nuevo que aparece en los reportes Excel pero olvidás insertarlo acá, no se va a calcular nunca.
  - El flag `es_subramo` decide qué pipeline lo procesa: cambiarlo dispara que el concepto deje de calcularse en una tabla y aparezca en otra.

### `parametros_reportes`
- **Propósito**: mapea cada cuenta contable (`cod_cuenta`) a un concepto (`reporte` + `referencia`), con un signo que indica si suma (+1) o resta (−1) al concepto.
- **Origen**: `initial_scripts/create_parametros_reportes.py` lee `PARAMETROSREPORTES.txt` (CSV con `;`). Filtra solo los reportes "que importan" (`anexo12-am`, `anexo13-b`, `resultados`, `pasivo`, `inversiones`, `ganaron-perdieron`, etc.).
- **Columnas**:
  - `reporte`, `referencia` — claves para joinear con `conceptos_reportes`.
  - `cod_cuenta` (TEXT) — código contable que se mapea contra `datos_balance.cod_cuenta`.
  - `signo` (INTEGER) — `+1` o `-1`. Multiplica al `importe` para que la suma de el resultado correcto (un siniestro pagado puede venir con cuentas que se suman y otras que se restan).
- **Relaciones**: hace JOIN con `conceptos_reportes` por `(reporte, referencia)`. Se aplica contra `datos_balance.cod_cuenta` durante el cálculo.
- **Advertencias**:
  - Una misma `cod_cuenta` puede mapear a más de un concepto (a través de distintos `(reporte, referencia)`). El cálculo construye `dict(zip(cod_cuenta, signo))` por concepto, así que si hay más de un signo para la misma cuenta dentro del mismo concepto sólo queda el último.

### `datos_companias`
- **Propósito**: catálogo de compañías con tipo de aseguradora y nombre legible.
- **Origen**: `initial_scripts/create_nombres_cias.py` lee `nombres_companias.csv`. También se administra desde el web UI (`app/routes/companies.py`).
- **Columnas**:
  - `cod_cia` (TEXT) — clave.
  - `nombre_corto` (TEXT) — nombre que aparece en los reportes Excel.
  - `tipo_cia` (TEXT) — uno de `Generales`, `Vida`, `Retiro`, `ART`, `M.T.P.P.`. Determina en qué reportes / rankings entra cada compañía.
  - `fecha` (DATE) — auditoría de carga.
- **Relaciones**: por `cod_cia` con todas las `base_*`.
- **Advertencias**: si una compañía aparece en `datos_balance` pero no acá, los reportes que joinean para mostrar el nombre la van a ocultar o dejar sin nombre.

### `datos_ramos_subramos`
- **Propósito**: tabla de mapeo subramo → ramo. Sin esto, la agregación a nivel ramo no se puede hacer.
- **Origen**: `initial_scripts/create_nombres_ramos.py` lee `nombres_ramos.csv`.
- **Columnas relevantes**:
  - `cod_subramo` — clave de join.
  - `ramo_denominacion` (TEXT) — denominación textual del ramo. Es el `GROUP BY` que usa `base_ramos` y `base_ramos_corregida_actual`.
- **Relaciones**: por `cod_subramo` con `datos_balance`, `base_subramos`, `base_balance_ultimos_periodos`.
- **Advertencias**:
  - Si un `cod_subramo` que aparece en `datos_balance` no está mapeado acá, queda con `ramo_denominacion=NULL` en `base_ramos` y se descarta (todos los grupos NULL se aglutinan en uno solo, distorsionando el resultado).
  - `crea_tabla_ramos.py` valida que el JOIN no devuelva todo NULL (línea 74), pero un mapeo parcial pasa silencioso.

### `quarter_ipc_data`
- **Propósito**: índice IPC sólo en cierres de trimestre, con `periodo` ya en formato del proyecto (`YYYYPP`).
- **Origen**: derivada en el mismo script de `monthly_ipc_data`. Toma sólo marzo/junio/septiembre/diciembre y mapea mes → cuatrimestre (`3→01`, `6→02`, `9→03`, `12→04`).
- **Columnas**: `periodo` (INTEGER, `YYYYPP`), `indice_ipc` (REAL).
- **Advertencias**: si el CSV de IPC no tiene un mes de cierre puntual, ese período faltará en esta tabla aunque exista en `monthly_ipc_data`.

---

## 3. Tablas intermedias

Producidas por el pipeline como paso previo. No se consumen directamente desde reportes; se las usa como input para las tablas de análisis.

### `base_balance_ultimos_periodos`
- **Propósito**: filtro de `datos_balance` a los últimos ~2 años para acelerar las agregaciones siguientes.
- **Origen**: `modules/crea_tabla_ultimos_periodos.py`. Hace `CREATE TABLE ... AS SELECT * FROM datos_balance WHERE periodo >= {año-2}00`.
- **Estructura**: copia exacta de `datos_balance` filtrada.
- **Relaciones**: input de `crea_tabla_subramos.py`, `crea_tabla_ramos.py`, `crea_tabla_otros_conceptos.py`.
- **Advertencias**:
  - **Se reemplaza con DROP/CREATE** — siempre contiene 2 años hacia atrás desde el año de referencia, no más.
  - El módulo necesita 2 años hacia atrás porque las correcciones de compañías especiales (T1, T2) requieren datos de "diciembre prev_prev" y "junio prev_prev". Si reducís el filtro a 1 año, las tablas `_corregida` rompen para esos trimestres.

---

## 4. Tablas de análisis

Las tablas que efectivamente consumen los generadores de reportes Excel.

### `base_subramos`
- **Propósito**: agregaciones financieras por compañía / período / subramo. Tabla principal para los reportes que cruzan compañía contra ramo/subramo.
- **Origen**: `modules/crea_tabla_subramos.py`. Aplica `parametros_reportes` sobre `base_balance_ultimos_periodos`, multiplicando `importe * signo` por concepto y agrupando por `(cod_cia, periodo, cod_subramo)`.
- **Granularidad**: una fila por `(cod_cia, periodo, cod_subramo)`.
- **Columnas no-obvias**:
  - `gastos_totales_devengados` — corresponde al concepto interno `gastos_devengados` en `conceptos_reportes`. El alias se cambia en el `agg`.
  - `gs_prod_*`, `gs_exp_*`, `gs_reaseg_*`, `gs_a_c_reaseguro` — apertura de gastos. Sumarlos da los gastos totales.
  - `primas_cedidas` — primas que la compañía cede al reasegurador. Va con signo positivo en este modelo.
- **Relaciones**: input de `base_ramos_corregida_actual`, `base_subramos_corregida_actual`, `base_cias_corregida_actual`, y consumida directamente por la mayoría de los `excel_generators/`.
- **Advertencias**:
  - Es **histórica** (cubre 2 años). Pero las tablas `*_corregida_actual` son de 1 período.
  - Sólo procesa conceptos con `es_subramo=1`. Conceptos patrimoniales no aparecen acá.

### `base_ramos`
- **Propósito**: misma idea que `base_subramos` pero agregada al nivel `ramo_denominacion` (un nivel arriba de subramo).
- **Origen**: `modules/crea_tabla_ramos.py`. Hace JOIN con `datos_ramos_subramos` para obtener `ramo_denominacion` antes de agregar.
- **Granularidad**: una fila por `(cod_cia, periodo, ramo_denominacion)`.
- **Relaciones**: input de `base_ramos_corregida_actual`.
- **Advertencias**:
  - Si `datos_ramos_subramos` no está poblada o no cubre todos los subramos, las filas con `ramo_denominacion=NULL` se agrupan todas juntas (ver advertencia en la sección de configuración).
  - Las columnas son las mismas que `base_subramos` excepto que `cod_subramo` se reemplaza por `ramo_denominacion`.

### `base_otros_conceptos`
- **Propósito**: conceptos patrimoniales / financieros que NO se calculan por subramo (resultado técnico, patrimonio neto, deudas, etc.). Sólo del último período.
- **Origen**: `modules/crea_tabla_otros_conceptos.py`. Filtra `conceptos_reportes` con `es_subramo=FALSE`. Toma sólo `MAX(periodo)` (o el período pasado por argumento).
- **Granularidad**: una fila por `(cod_cia, periodo)`. **Un solo período**, no histórica.
- **Columnas**: `resultado_tecnico`, `resultado_financiero`, `resultado_operaciones`, `impuesto_ganancias`, `deudas_con_asegurados`, `deudas_con_asegurados_ac_reaseguros`, `disponibilidades`, `inmuebles_inversion`, `inmuebles_uso_propio`, `inversiones`, `patrimonio_neto`.
- **Advertencias**:
  - **No tiene serie histórica**. Cada vez que corrés el módulo, sobreescribe con el último período disponible.
  - No aplica corrección por compañías especiales (cierre diferente). Los valores de `'0829'`, `'0541'`, `'0686'` representan acumulado enero-mes_actual, no 12 meses móviles.

### `base_subramos_corregida_actual`
- **Propósito**: primas emitidas del período actual y del período anterior comparable, **homogeneizadas a 12 meses móviles** para todas las compañías. Es la base para variaciones interanuales.
- **Origen**: `modules/crea_tabla_subramos_corregida.py`. Aplica fórmulas distintas por trimestre:
  - **T1 (marzo)**: especiales = `marzo - junio_anterior + diciembre_anterior` (12 meses móviles terminando en marzo).
  - **T2 (junio)**: especiales = `junio + diciembre_anterior - junio_anterior`.
  - **T3 (sept)**: especiales = `septiembre - junio` (julio-septiembre del año fiscal especial).
  - **T4 (dic)**: especiales = `diciembre - junio`.
  - Compañías comunes: directo, comparando mismo trimestre del año anterior.
- **Granularidad**: una fila por `(cod_cia, cod_subramo)` para el período corregido.
- **Columnas**: `cod_cia`, `cod_subramo`, `primas_emitidas` (período actual corregido), `primas_emitidas_anterior` (período anterior comparable corregido).
- **Relaciones**: la consumen los reportes de variación / ranking comparativo.
- **Advertencias**:
  - **Sólo del período actual** (parámetro de input). Cada corrida la sobreescribe.
  - Filtra `WHERE primas_emitidas <> 0`, así que filas que terminen en cero por neteo desaparecen.
  - Sólo trae `primas_emitidas`. Otras métricas (siniestros, gastos) no están corregidas.
  - Necesita históricos de 2 años para los trimestres 1 y 2 (junio y diciembre del año −1 y −2). Si `base_subramos` no los tiene, el JOIN falla silenciosamente y faltan filas de las compañías especiales.

### `base_ramos_corregida_actual`
- **Propósito**: idéntico a `base_subramos_corregida_actual` pero al nivel `ramo_denominacion`.
- **Origen**: `modules/crea_tabla_ramos_corregida.py`. Mismas fórmulas. Lee de `base_ramos`.
- **Granularidad**: una fila por `(cod_cia, ramo_denominacion)`.
- **Comportamiento de JOIN**: T1, T2 y T4 usan `FULL OUTER JOIN` para combinar período actual y anterior — incluye compañías que aparecen sólo en uno de los dos períodos. T3 usa `LEFT JOIN`.
- **Advertencias**: las mismas que la versión subramos.

### `base_cias_corregida_actual`
- **Propósito**: primas totales por compañía (sumando todos los subramos) para el período actual corregido. La usa `ranking_comparativo` para no romperse cuando un subramo aparece o desaparece entre períodos.
- **Origen**: `modules/crea_tabla_cias_corregida.py`. Lee de `base_subramos` (no de `base_ramos`) y aplica las mismas correcciones por trimestre, pero agregando todo a nivel `cod_cia`.
- **Granularidad**: una fila por `cod_cia`.
- **Columnas**: `cod_cia`, `primas_emitidas`, `primas_emitidas_anterior`.
- **Advertencias**: usar esta tabla, no la suma de `base_subramos_corregida_actual`, cuando se quieren totales por compañía consistentes (mantiene compañías que aparecieron sólo en uno de los dos períodos vía `FULL OUTER JOIN`).

---

## Resumen de relaciones

```
datos_balance (fuente)
    │
    ▼
base_balance_ultimos_periodos (filtro 2 años)
    │
    ├──► base_subramos ───► base_subramos_corregida_actual
    │         │                    │
    │         └────────────────────┴──► base_cias_corregida_actual
    │
    ├──► base_ramos ─────► base_ramos_corregida_actual
    │       (necesita datos_ramos_subramos)
    │
    └──► base_otros_conceptos (no histórica)

Mapeos (configuración) usados como JOIN durante el pipeline:
  conceptos_reportes ◄──(reporte, referencia)──► parametros_reportes
  parametros_reportes.cod_cuenta ◄──► datos_balance.cod_cuenta
  datos_companias.cod_cia ◄──► reportes finales
  datos_ramos_subramos.cod_subramo ◄──► base_balance_ultimos_periodos

IPC (independiente):
  monthly_ipc_data (YYYYMM)
  quarter_ipc_data (YYYYPP)
```

---

## Resumen rápido por categoría

| Categoría | Tablas | ¿Histórica? |
|---|---|---|
| Fuente | `datos_balance`, `monthly_ipc_data` | Sí |
| Configuración | `conceptos_reportes`, `parametros_reportes`, `datos_companias`, `datos_ramos_subramos`, `quarter_ipc_data` | Snapshot |
| Intermedia | `base_balance_ultimos_periodos` | Últimos 2 años |
| Análisis (histórica) | `base_subramos`, `base_ramos` | Últimos 2 años |
| Análisis (un período) | `base_otros_conceptos`, `base_subramos_corregida_actual`, `base_ramos_corregida_actual`, `base_cias_corregida_actual` | No — sólo período actual |
