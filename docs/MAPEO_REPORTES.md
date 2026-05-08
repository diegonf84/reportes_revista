# Mapeo de reportes

Documento de referencia que mapea cada reporte de salida a las tablas y columnas que lo alimentan, con sus dependencias y restricciones. Se complementa con `TABLAS.md` (definición de cada tabla).

---

## Cómo se generan los reportes

El pipeline de salida tiene dos etapas:

1. **CSVs intermedios** — `ending_files/generate_all_reports.py` lee `ending_files/report_definitions.json` (12 reportes con queries SQL) y por cada uno genera un CSV en `ending_files/{period}/{period}_<nombre>.csv`. Las queries usan `{period}` como placeholder reemplazado en runtime.
2. **Excels finales** — `excel_generators/generate_all_excel.py` orquesta 13 generadores que leen los CSVs y escriben `excel_final_files/{period}/{period}_<nombre>.xlsx`. Cada generador aplica formato, hojas múltiples y cálculos adicionales.

> Hay **12 definiciones de CSV** pero **13 Excels**: `ranking_generales` no tiene su propio CSV — reutiliza `{period}_ranking_comparativo.csv` para producir un Excel distinto (`ranking_produccion.xlsx`).

### Orden de ejecución típico
```
1. python ending_files/generate_all_reports.py {period}      # genera 12 CSVs
2. python excel_generators/generate_all_excel.py {period}    # genera 13 Excels
```

---

## Cuadro general de dependencias

| Reporte (Excel) | CSV fuente | Tablas que consulta | Período |
|---|---|---|---|
| `cuadro_nuevo` | `{p}_cuadro_nuevo.csv` | `base_subramos` + `base_otros_conceptos` + `datos_companias` | `{period}` |
| `cuadro_principal` | `{p}_cuadro_principal.csv` | `base_subramos` + `datos_companias` + `datos_ramos_subramos` | `{period}` |
| `ganaron_perdieron` | `{p}_ganaron_perdieron.csv` | `base_subramos` + `base_otros_conceptos` + `datos_companias` | `{period}` |
| `apertura_por_subramo` | `{p}_apertura_por_subramo.csv` | `base_subramos_corregida_actual` + `datos_companias` + `datos_ramos_subramos` | Implícito (corregida) |
| `primas_cedidas_reaseguro` | `{p}_primas_cedidas_reaseguro.csv` | `base_subramos` + `datos_companias` | `{period}` |
| `ranking_comparativo` | `{p}_ranking_comparativo.csv` | `base_cias_corregida_actual` + `datos_companias` | Implícito (corregida) |
| `ranking_comparativo_por_ramo` | `{p}_ranking_comparativo_por_ramo.csv` | `base_ramos_corregida_actual` + `datos_companias` | Implícito (corregida) |
| `ranking_generales` (`ranking_produccion.xlsx`) | **reusa `{p}_ranking_comparativo.csv`** | (idem ranking_comparativo) | Implícito (corregida) |
| `sueldos_y_gastos` | `{p}_sueldos_y_gastos.csv` | `base_subramos` + `datos_companias` | `{period}` |
| `detalle_inmuebles` | `{p}_detalle_inmuebles.csv` | `base_otros_conceptos` + `datos_companias` | `{period}` |
| `detalle_gastos` | `{p}_detalle_gastos.csv` | `base_subramos` + `datos_companias` | `{period}` |
| `distribucion_inversiones` | `{p}_distribucion_inversiones.csv` | `base_otros_conceptos` + `datos_companias` | `{period}` |
| `indicadores_solvencia` | `{p}_indicadores_solvencia.csv` | `base_otros_conceptos` + `datos_companias` | `{period}` |

---

## Detalle por reporte

Cada entrada describe: el SQL que produce el CSV, qué columnas terminan en el Excel, dependencias y restricciones específicas.

### 1. `cuadro_nuevo`
- **Tablas usadas**: `base_subramos` (suma `primas_emitidas` por compañía), `base_otros_conceptos` (datos patrimoniales), `datos_companias`.
- **Columnas leídas**:
  - De `base_subramos`: `primas_emitidas`.
  - De `base_otros_conceptos`: `disponibilidades`, `inversiones`, `inmuebles_inversion`, `inmuebles_uso_propio`, `deudas_con_asegurados`, `deudas_con_asegurados_ac_reaseguros`, `patrimonio_neto`.
  - De `datos_companias`: `tipo_cia`, `nombre_corto`.
- **Columnas calculadas en SQL**: `inmuebles = inmuebles_inversion + inmuebles_uso_propio`; `deudas_total_aseg = deudas_con_asegurados - deudas_con_asegurados_ac_reaseguros`; `deudas_neto = deudas_con_asegurados`.
- **Generador Excel**: una sola hoja, agrupando por `tipo_cia` con totales por grupo.
- **Restricciones**: no excluye ninguna compañía; depende de que `base_otros_conceptos` esté para el período actual.

### 2. `cuadro_principal`
- **Tablas usadas**: `base_subramos` (métricas operativas), `datos_companias`, `datos_ramos_subramos` (para `ramo_denominacion`).
- **Columnas leídas**: `primas_devengadas`, `primas_emitidas`, `siniestros_devengados`, `gastos_totales_devengados` (alias `gastos`), `cod_subramo`, más nombres y ramo.
- **Columnas calculadas en SQL**: `pct_stros = siniestros / primas_devengadas * 100`, `pct_gastos`, `resultado = primas_devengadas - siniestros - gastos`, `pct_result`.
- **Generador Excel**: tres hojas — `Generales`, `Vida`, `ART`. Cada hoja contiene cuadros individuales por ramo + cuadro resumen y total del mercado. El generador tiene **mapeos hardcodeados de nombres de ramos** (ej: `'Automotores' → 'AUTOMOTORES'`); los ramos que no estén en `mapa_ramos_generales`, `mapa_ramos_vida` o `'Riesgos del Trabajo'` no aparecen.
- **Restricción importante**: el SQL **excluye** los subramos `'2.070.01'`, `'2.070.02'`, `'3.000.99'` (no entran al cálculo de cuadro principal — habitualmente conceptos no asignables a un ramo específico). Si en el futuro se quieren incluir, hay que tocar el JSON.
- **Restricción**: filas con `primas_emitidas <> 0` después de agrupar.

### 3. `ganaron_perdieron`
- **Tablas usadas**: `base_subramos` (suma `primas_devengadas` por compañía), `base_otros_conceptos` (resultados financieros), `datos_companias`.
- **Columnas leídas**: `primas_devengadas`, `resultado_tecnico`, `resultado_financiero`, `resultado_operaciones`, `impuesto_ganancias`.
- **Columnas calculadas en SQL**: `pct_rt`, `pct_rf`, `resultado = rt + rf + ro - imp_ganancias` (impuesto cambiado de signo), `pct_result`.
- **Generador Excel**: una hoja por `tipo_cia`. Cada hoja parte las compañías en "LAS QUE GANARON" (`resultado > 0`) y "LAS QUE PERDIERON" (`resultado < 0`).
- **Restricciones**: las compañías con `resultado = 0` no aparecen en ningún cuadro pero sí en el total.

### 4. `apertura_por_subramo`
- **Tablas usadas**: `base_subramos_corregida_actual` (primas corregidas), `datos_companias`, `datos_ramos_subramos` (necesita `subramo_denominacion`, no sólo `cod_subramo`/`ramo_denominacion`).
- **Período**: implícito en `base_subramos_corregida_actual` (el SQL **no filtra por `periodo`**); está atado al período de la última corrida de `crea_tabla_subramos_corregida.py`.
- **Columnas calculadas en SQL**: `porcentaje = primas / total_subramo * 100`; `porcentaje_acumulado` con window function por subramo.
- **Generador Excel**: una hoja por ramo. **Filtra subramos vía un diccionario hardcodeado** `SUBRAMOS_INCLUIDOS` en `excel_generators/apertura_por_subramos.py:9`. Sólo aparecen los 26 subramos listados (Combinado Familiar, Automotores, RC, Otros Riesgos, Motos, Accidentes Personales, Salud, Vida, Sepelio, Retiro). Si querés agregar/sacar subramos hay que editar ese diccionario.
- **Advertencias**:
  - Si `crea_tabla_subramos_corregida.py` no se corrió para el período objetivo, este reporte queda con datos del período anterior **sin que el sistema lo avise**.
  - Si `datos_ramos_subramos` no tiene `subramo_denominacion` para algún `cod_subramo` que aparece en `base_subramos_corregida_actual`, esa fila se pierde.

### 5. `primas_cedidas_reaseguro`
- **Tablas usadas**: `base_subramos` (suma `primas_emitidas` y `primas_cedidas` por compañía), `datos_companias`.
- **Columnas calculadas en SQL**: `pct_cesion = primas_ced / primas_emit * 100`; `primas_retenidas = primas_emit - primas_ced`; `pct_ret = primas_retenidas / primas_emit * 100`. Usa `iif(primas_emit = 0, 0, ...)` para evitar división por cero.
- **Generador Excel**: una hoja por `tipo_cia`. **Excluye `tipo_cia = 'Retiro'`** (lista hardcodeada `tipos_incluir = ['ART', 'Generales', 'M.T.P.P.', 'Vida']` en línea 28). Renombra hoja `M.T.P.P. → MTTP`.
- **Restricciones**: SQL excluye compañías con `primas_emit = 0` (`WHERE b.primas_emit <> 0`).

### 6. `ranking_comparativo`
- **Tablas usadas**: `base_cias_corregida_actual` (primas actual y anterior), `datos_companias`.
- **Período**: implícito (sin filtro `WHERE periodo`); depende de la última corrida de `crea_tabla_cias_corregida.py`.
- **Columnas calculadas en SQL**: `variacion = ((primas / primas_anterior) - 1) * 100`; protegido con `iif(primas_anterior = 0, 0, ...)`.
- **Generador Excel**: tres hojas — `Ranking` (cuadros por tipo), `Ranking Total Comparativo` (todas las compañías ordenadas por primas descendente), `base_detalle` (detalle plano con todas las columnas).

### 7. `ranking_comparativo_por_ramo`
- **Tablas usadas**: `base_ramos_corregida_actual`, `datos_companias`.
- **Período**: implícito (idem que ranking_comparativo, pero por ramo).
- **Columnas calculadas en SQL**: `variacion` con misma lógica anti-zero-div.
- **Generador Excel**: dos hojas — `Ranking` (un cuadro por ramo, ordenado alfabéticamente por entidad) y `base_detalle`.

### 8. `ranking_generales` → produce `ranking_produccion.xlsx`
- **Reuso de CSV**: lee `{period}_ranking_comparativo.csv` (el mismo que el reporte 6). **No tiene query propia en el JSON**.
- **Tablas usadas**: indirectamente las mismas que `ranking_comparativo`.
- **Generador Excel** (`excel_generators/ranking_generales.py`): tres hojas:
  - `Ranking Generales` — sólo compañías con `tipo_cia = 'Generales'`, ordenadas por primas emitidas descendente. Título fijo: `"RANKING DE PRODUCCION DE COMPAÑIAS DE SEGUROS PATRIMONIALES Y MIXTAS"`.
  - `Varios` — un cuadro por tipo (incluye Retiro, a diferencia de `primas_cedidas`) + cuadro resumen por tipos en columna H.
  - `Ranking` — todas las compañías de los tipos `['ART', 'Generales', 'M.T.P.P.', 'Retiro', 'Vida']` ordenadas por primas emitidas descendente.
- **Advertencia**: si `ranking_comparativo` falla, este también; el script lo levanta como excepción de `FileNotFoundError`.

### 9. `sueldos_y_gastos`
- **Tablas usadas**: `base_subramos` (apertura de gastos por compañía), `datos_companias`.
- **Columnas leídas**: `primas_devengadas`, `gs_prod_comisiones`, `gs_prod_otros`, `gs_a_c_reaseguro`, `gs_exp_sueldos`, `gastos_totales_devengados`.
- **Columnas calculadas en SQL** (CTE): `gastos_produccion = gs_prod_comisiones + gs_prod_otros - gs_a_c_reaseguro`; `gastos_sueldos = gs_exp_sueldos`; `gastos_reaseguro = gs_a_c_reaseguro`; `gastos_totales = gastos_totales_devengados`.
- **Columnas calculadas en Excel** (no en CSV): `pct_sueldos = total_sueldos / total_primas_devengadas * 100`, idem `pct_gs_prod`, `pct_total_gs`. **El generador agrega los porcentajes al vuelo**, no vienen del CSV. Si el CSV se mira directo (sin Excel) faltan los porcentajes.
- **Generador Excel**: una hoja por `tipo_cia` + `base_detalle`.

### 10. `detalle_inmuebles`
- **Tablas usadas**: `base_otros_conceptos`, `datos_companias`.
- **Columnas leídas**: `inmuebles_inversion`, `inmuebles_uso_propio`.
- **Columnas calculadas en SQL**: `inmuebles_total = inmuebles_inversion + inmuebles_uso_propio`.
- **Generador Excel**: una sola hoja, agrupando por `tipo_cia`. **Filtra filas donde los tres valores son cero** (en el generador, no en SQL) — compañías sin inmuebles no aparecen.
- **Filtro WHERE**: `b.periodo = '{period}'` directo.

### 11. `detalle_gastos`
- **Tablas usadas**: `base_subramos` (apertura completa de gastos), `datos_companias`.
- **Columnas leídas**: `primas_emitidas`, `primas_devengadas`, `gs_prod_comisiones`, `gs_prod_otros`, `gs_a_c_reaseguro`, `gs_exp_sueldos`, `gs_exp_ret_sindicos`, `gs_exp_honorarios`, `gs_exp_impuestos`, `gs_exp_publicidad`, `gs_exp_otros`, `gs_reaseg_act_prod`, `gastos_totales_devengados`.
- **Columnas calculadas en SQL** (CTE):
  - `gastos_produccion = gs_prod_comisiones + gs_prod_otros - gs_a_c_reaseguro`
  - `gastos_explotacion = gs_exp_sueldos + gs_exp_ret_sindicos + gs_exp_honorarios + gs_exp_impuestos + gs_exp_publicidad + gs_exp_otros + gs_reaseg_act_prod`
  - `gastos_totales = gastos_totales_devengados`
  - `pct_gastos_produccion`, `pct_gastos_explotacion`, `pct_gastos_totales` (sobre `total_primas_devengadas`).
- **Generador Excel**: dos hojas — `Detalle Gastos` (sólo porcentajes, agrupado por tipo) y `base_detalle`. Los totales de porcentaje en el Excel son **promedios ponderados** recalculados con los totales de la suma, no promedio simple de los porcentajes individuales.

### 12. `distribucion_inversiones`
- **Tablas usadas**: `base_otros_conceptos`, `datos_companias`.
- **Columnas leídas**: `inmuebles_inversion`, `inversiones`.
- **Columnas calculadas en SQL**:
  - `total_inv = inmuebles_inversion + inversiones`
  - `total_inv_inm = inmuebles_inversion`
  - `total_inv_liq = inversiones`
  - `pct_inmuebles_inversion`, `pct_inversiones_liquidas` (sobre `total_inv`, con `iif(... = 0, 0, ...)`).
- **Generador Excel**: dos hojas — `Distribucion Inversiones` y `base_detalle`. Totales por tipo recalculan porcentajes como promedio ponderado.

### 13. `indicadores_solvencia`
- **Tablas usadas**: `base_otros_conceptos`, `datos_companias`.
- **Columnas leídas**: `inmuebles_inversion`, `inversiones`, `disponibilidades`, `deudas_con_asegurados`.
- **Cálculos de ratios**: **no se hacen en SQL**, se hacen en el generador Excel:
  - Ratio 1: `(disponibilidades + inversiones) / deudas_con_asegurados * 100`.
  - Ratio 2: `(disponibilidades + inversiones + inmuebles_inversion) / deudas_con_asegurados * 100`.
- **Caso especial — `deudas_con_asegurados = 0`**: el generador escribe `(*)` en lugar del ratio y agrega un footnote `"(*) No registra deudas con asegurados"`. Esto aparece típicamente en compañías de Retiro.
- **Generador Excel**: dos hojas — `Indicadores Solvencia` (sólo los dos ratios) y `base_detalle` (montos + ratios). Agrupado por tipo, ordenado alfabéticamente.

---

## Orden requerido de existencia de tablas

Para que los 13 Excels se generen sin errores, las tablas deben existir en este orden. El web UI (`app/routes/data_processing.py`) lo encadena automáticamente; si corrés módulos a mano, este es el orden correcto:

```
1. SOURCE / CONFIG (carga inicial — se hacen una sola vez o cuando llega data nueva):
   - datos_balance              ← carga_base_principal.py (de archivos .mdb)
   - datos_companias            ← create_nombres_cias.py
   - datos_ramos_subramos       ← create_nombres_ramos.py
   - conceptos_reportes         ← create_conceptos_reportes.py + insert_concepts.py
   - parametros_reportes        ← create_parametros_reportes.py

2. PIPELINE (cada vez que llega un período nuevo o se corrige uno existente):
   - base_balance_ultimos_periodos    ← crea_tabla_ultimos_periodos.py
       │
       ├──► base_subramos              ← crea_tabla_subramos.py
       ├──► base_ramos                 ← crea_tabla_ramos.py
       └──► base_otros_conceptos       ← crea_tabla_otros_conceptos.py

3. CORRECCIONES (sólo para el período objetivo del reporte):
   - base_subramos_corregida_actual  ← crea_tabla_subramos_corregida.py {period}
   - base_ramos_corregida_actual     ← crea_tabla_ramos_corregida.py {period}
   - base_cias_corregida_actual      ← crea_tabla_cias_corregida.py {period}

4. SALIDA:
   - python ending_files/generate_all_reports.py {period}     # 12 CSVs
   - python excel_generators/generate_all_excel.py {period}   # 13 Excels
```

### Tablas requeridas por reporte (resumen)

| Reporte | Necesita |
|---|---|
| `cuadro_nuevo` | `base_subramos`, `base_otros_conceptos`, `datos_companias` |
| `cuadro_principal` | `base_subramos`, `datos_companias`, `datos_ramos_subramos` |
| `ganaron_perdieron` | `base_subramos`, `base_otros_conceptos`, `datos_companias` |
| `apertura_por_subramo` | `base_subramos_corregida_actual`, `datos_companias`, `datos_ramos_subramos` |
| `primas_cedidas_reaseguro` | `base_subramos`, `datos_companias` |
| `ranking_comparativo` | `base_cias_corregida_actual`, `datos_companias` |
| `ranking_comparativo_por_ramo` | `base_ramos_corregida_actual`, `datos_companias` |
| `ranking_generales` | (idem ranking_comparativo) |
| `sueldos_y_gastos` | `base_subramos`, `datos_companias` |
| `detalle_inmuebles` | `base_otros_conceptos`, `datos_companias` |
| `detalle_gastos` | `base_subramos`, `datos_companias` |
| `distribucion_inversiones` | `base_otros_conceptos`, `datos_companias` |
| `indicadores_solvencia` | `base_otros_conceptos`, `datos_companias` |

---

## Restricciones / casos especiales transversales

Cosas a tener en cuenta que aplican a varios reportes:

- **Tablas `*_corregida_actual` no filtran por período** en sus queries. Están "atadas" al período de la última ejecución de los módulos de corrección (`crea_tabla_*_corregida.py {period}`). Si pedís reportes para 202503 pero las tablas corregidas tienen 202502, los reportes 4, 6, 7 y 8 saldrán **silenciosamente con datos del período viejo**.
- **`base_otros_conceptos` se sobreescribe en cada corrida** y no es histórica. Reportes 1, 3, 10, 12, 13 dependen de ella; correr `crea_tabla_otros_conceptos.py` con un período distinto invalida todos esos reportes hasta que se vuelva a correr para el período correcto.
- **Filtros de tipo de compañía hardcodeados** en los generadores Excel:
  - `primas_cedidas_reaseguro`: excluye `'Retiro'`.
  - `ranking_comparativo`, `ranking_generales`: incluyen `['ART', 'Generales', 'M.T.P.P.', 'Vida', 'Retiro']`.
  - `cuadro_principal`: clasifica ramos en `Generales`/`Vida`/`ART` con diccionarios hardcodeados — ramos no mapeados desaparecen.
  - `apertura_por_subramo`: limita a 26 subramos hardcodeados en `SUBRAMOS_INCLUIDOS`.
- **División por cero**: las queries de `primas_cedidas_reaseguro`, `ranking_comparativo`, `ranking_comparativo_por_ramo`, `distribucion_inversiones`, `detalle_gastos` la manejan con `iif(... = 0, 0, ...)`. `indicadores_solvencia` la maneja en Python escribiendo `(*)`. En `cuadro_principal`, `ganaron_perdieron` y `sueldos_y_gastos` los porcentajes no tienen protección explícita — si `primas_devengadas = 0` para alguna compañía, el SQL devuelve `NULL`.
- **Strings de período**: la query usa `WHERE periodo = '{period}'` con comillas — la columna `periodo` es INTEGER pero SQLite hace coerción tolerante.
