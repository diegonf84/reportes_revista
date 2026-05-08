# Métricas calculadas

Inventario de todas las métricas que aparecen en los reportes pero **no son columnas directas** de las tablas de la base de datos. Para cada una se documenta: fórmula exacta, dónde aparece, base del denominador y casos especiales (división por cero, etc.).

Un patrón a tener en cuenta antes de leer: muchas métricas se calculan **dos veces** — una en SQL para el detalle por compañía (CSV intermedio), y otra en Python para los totales por grupo en el Excel. **Los totales casi nunca son promedio simple de los porcentajes individuales**: son promedios ponderados que recalculan la métrica desde los totales sumados de numerador y denominador. Esa diferencia es importante: si tomás los porcentajes del CSV y los promediás, **no vas a obtener el total que muestra el Excel**.

Todos los porcentajes se expresan en escala 0–100 (no 0–1).

---

## Por reporte

### `cuadro_principal` (resultados técnicos)

Cuatro métricas por compañía/ramo. Calculadas en SQL en `ending_files/report_definitions.json` ("cuadro_principal").

| Métrica | Fórmula | Denominador | Aparece en |
|---|---|---|---|
| `pct_stros` | `siniestros / primas_devengadas * 100` | `primas_devengadas` por compañía/ramo | Columna "Siniestr. (%)" |
| `pct_gastos` | `gastos / primas_devengadas * 100` | `primas_devengadas` por compañía/ramo | Columna "Gs. prod. y explot. (%)" |
| `resultado` | `primas_devengadas - siniestros - gastos` | (no aplica, es absoluto) | Columna "Resultados técnicos $" |
| `pct_result` | `resultado / primas_devengadas * 100` | `primas_devengadas` por compañía/ramo | Columna "Resultados técnicos %" |

**Donde `gastos`** es el alias del SQL para `gastos_totales_devengados` (la suma de toda la apertura `gs_*` ya hecha al construir `base_subramos`).

**Totales por ramo y total del mercado (en `excel_generators/cuadro_principal.py`)**: el generador suma `siniestros`, `gastos`, `primas_devengadas` y `resultado` por separado, y luego recalcula los porcentajes sobre esos totales, redondeando a 1 decimal. Es promedio ponderado por `primas_devengadas`, no promedio aritmético.

**Casos especiales / división por cero**: el SQL **no protege** contra `primas_devengadas = 0`. Si una compañía tiene devengadas en cero, el SQL devuelve `NULL` para los porcentajes y se exporta como vacío. El generador Excel también divide directo (`crear_cuadro_resumen` línea 169) — si el total de un ramo o del mercado fuera 0 (caso muy improbable) tira `ZeroDivisionError`. En la práctica esto no ocurre porque los totales suman cientos de compañías.

---

### `ganaron_perdieron` (resultado del ejercicio)

Cinco métricas por compañía. SQL en `ending_files/report_definitions.json` ("ganaron_perdieron").

| Métrica | Fórmula | Denominador | Aparece en |
|---|---|---|---|
| `pct_rt` | `resultado_tecnico / primas_devengadas * 100` | `primas_devengadas` por compañía | "% s/primas devengadas" (columna de RT) |
| `pct_rf` | `resultado_financiero / primas_devengadas * 100` | `primas_devengadas` por compañía | "% s/primas devengadas" (columna de RF) |
| `impuesto_ganancias` (mostrado) | `impuesto_ganancias_raw * (-1)` | (cambio de signo) | Columna "Impuesto a las Ganancias" |
| `resultado` (del ejercicio) | `resultado_tecnico + resultado_financiero + resultado_operaciones - impuesto_ganancias_raw` | (no aplica) | Columna "Resultado del ejercicio" |
| `pct_result` | `resultado / primas_devengadas * 100` | `primas_devengadas` por compañía | "% s/primas devengadas" (columna de resultado) |

**Importante sobre el signo del impuesto**: en `base_otros_conceptos`, `impuesto_ganancias` se almacena con signo positivo (es un gasto, sumando lo que la compañía pagó). En el SQL del reporte:
- Se muestra invertido: `impuesto_ganancias * (-1)` → en el Excel aparece como número negativo.
- Pero en la fórmula del resultado del ejercicio se **resta sin invertir**: `... - bf.impuesto_ganancias` (es decir, se resta el valor positivo original). El neto contable queda correcto: `RT + RF + RO - impuesto`.

**Totales por tipo y por sección "ganaron"/"perdieron" (en `excel_generators/ganaron_perdieron.py:202-225`)**: suma todos los resultados absolutos y `primas_devengadas`, recalcula los porcentajes sobre esos totales agregados.

**Caso especial**: `primas_devengadas = 0` no está protegido (`crear_cuadro_datos` no usa `iif`); división por cero da `NULL` en SQL.

---

### `indicadores_solvencia` (ratios de liquidez)

Dos ratios. **No se calculan en SQL** — el SQL del JSON sólo devuelve los componentes (`inmuebles_inversion`, `inversiones`, `disponibilidades`, `deudas_con_asegurados`). Los ratios se calculan en `excel_generators/indicadores_solvencia.py`.

| Métrica | Fórmula | Denominador | Aparece en |
|---|---|---|---|
| Ratio 1 | `(disponibilidades + inversiones) / deudas_con_asegurados * 100` | `deudas_con_asegurados` por compañía | "Disp+Inv / Ds.c/aseg %" |
| Ratio 2 | `(disponibilidades + inversiones + inmuebles_inversion) / deudas_con_asegurados * 100` | `deudas_con_asegurados` por compañía | "Disp+Inv+Inm / Ds.c/aseg %" |

**Casos especiales**:
- **`deudas_con_asegurados = 0`** → el generador escribe el string `(*)` en lugar del ratio (línea 113-122) y agrega un footnote `"(*) No registra deudas con asegurados"` al final de la hoja. Ocurre típicamente con compañías de Retiro (su modelo de negocio no acumula deudas con asegurados clásicas).
- **Totales por tipo** (`calcular_totales_solvencia` línea 337): suma `disponibilidades`, `inversiones`, `inmuebles_inversion` y `deudas_con_asegurados` por separado y luego recalcula los ratios sobre esos totales agregados. Si el total de deudas es 0 para un tipo entero, devuelve `0.0`. **No es promedio simple** de los ratios individuales — es ratio agregado.

---

### `primas_cedidas_reaseguro`

Cuatro métricas por compañía. SQL en `ending_files/report_definitions.json` ("primas_cedidas_reaseguro").

| Métrica | Fórmula | Denominador | Aparece en |
|---|---|---|---|
| `pct_cesion` | `primas_cedidas / primas_emitidas * 100` | `primas_emitidas` por compañía | Columna "% / total" (cesión) |
| `primas_retenidas` | `primas_emitidas - primas_cedidas` | (no aplica) | Columna "Primas netas de reaseguro" |
| `pct_ret` | `primas_retenidas / primas_emitidas * 100` | `primas_emitidas` por compañía | Columna "% / total" (retención) |

**Casos especiales**:
- **División por cero protegida en SQL**: ambos porcentajes usan `iif(primas_emit = 0, 0, ...)` y `iif(primas_emit - primas_cedidas = 0, 0, ...)`. Compañías con producción cero quedan con porcentajes en 0, no NaN.
- El SQL filtra `WHERE b.primas_emit <> 0`, así que compañías sin producción no aparecen en el reporte.
- **Totales por tipo** (`excel_generators/primas_cedidas_reaseguro.py:151-167`, función `calcular_totales`): suma primas absolutas y recalcula `pct_cesion` y `pct_ret` sobre los totales (promedio ponderado por producción). Si el total de primas emitidas para un tipo es 0, devuelve `0.0`.

---

## Métricas en otros reportes (resumen)

Estas también son métricas calculadas (no columnas crudas), aunque no estaban entre los 4 reportes principales que pediste leer. Las incluyo para completitud.

### `apertura_por_subramo`

| Métrica | Fórmula | Denominador | Notas |
|---|---|---|---|
| `porcentaje` | `primas / total_subramo * 100` | Total de primas del subramo (todas las compañías que reportan en ese subramo) | Es **share de mercado** dentro del subramo |
| `porcentaje_acumulado` | `SUM(porcentaje) OVER (PARTITION BY subramo_denominacion ORDER BY primas DESC)` | (idem) | Window function: orden importa. Es la concentración acumulada al ranking N |

Ambas calculadas en SQL (`apertura_por_subramo` query). Usan datos de `base_subramos_corregida_actual`, **no filtran por período** (atadas a la última corrida del módulo de corrección). El generador Excel **no recalcula totales** — sólo presenta lo que vino del CSV.

### `ranking_comparativo` y `ranking_comparativo_por_ramo`

| Métrica | Fórmula | Denominador | Notas |
|---|---|---|---|
| `variacion` | `((primas_emitidas / primas_emitidas_anterior) - 1) * 100` | `primas_emitidas_anterior` (período anterior corregido) | Variación interanual % |

Calculada en SQL con `iif(primas_anterior = 0, 0, ...)`. **Totales** (en `crear_hoja_ranking` y `crear_hoja_ranking_total` del generador): el Excel suma primas absolutas del actual y anterior por separado y luego recalcula la variación con la misma fórmula sobre los totales (promedio ponderado por tamaño de la compañía). El total se fija en 0 si el agregado anterior es 0 (`calcular_totales_tipo` línea 345).

### `sueldos_y_gastos`

Subconceptos calculados en SQL (CTE inicial):

| Métrica intermedia (CTE) | Fórmula |
|---|---|
| `gastos_produccion` | `gs_prod_comisiones + gs_prod_otros - gs_a_c_reaseguro` |
| `gastos_sueldos` | `gs_exp_sueldos` (alias) |
| `gastos_reaseguro` | `gs_a_c_reaseguro` (alias) |
| `gastos_totales` | `gastos_totales_devengados` (alias) |

Y los porcentajes finales **se calculan en Python**, no en SQL, en `excel_generators/sueldos_y_gastos.py:82-84`:

| Métrica | Fórmula | Denominador |
|---|---|---|
| `pct_sueldos` | `total_sueldos / total_primas_devengadas * 100` | `total_primas_devengadas` por compañía |
| `pct_gs_prod` | `total_gs_prod / total_primas_devengadas * 100` | `total_primas_devengadas` por compañía |
| `pct_total_gs` | `total_gs / total_primas_devengadas * 100` | `total_primas_devengadas` por compañía |

**Caso especial**: división por cero protegida con `if total_primas_devengadas != 0 else 0`. Los totales por tipo se recalculan como ratio agregado.

> **Importante**: si abrís el CSV de `sueldos_y_gastos.csv`, **no vas a ver los porcentajes** — sólo los montos absolutos. Los porcentajes existen sólo en el Excel.

### `detalle_gastos`

Calculadas íntegramente en SQL:

| Métrica intermedia (CTE) | Fórmula |
|---|---|
| `gastos_produccion` | `gs_prod_comisiones + gs_prod_otros - gs_a_c_reaseguro` |
| `gastos_explotacion` | `gs_exp_sueldos + gs_exp_ret_sindicos + gs_exp_honorarios + gs_exp_impuestos + gs_exp_publicidad + gs_exp_otros + gs_reaseg_act_prod` |
| `gastos_totales` | `gastos_totales_devengados` (alias) |

| Métrica final | Fórmula | Denominador |
|---|---|---|
| `pct_gastos_produccion` | `(total_gs_prod / total_primas_devengadas) * 100` | `total_primas_devengadas` por compañía |
| `pct_gastos_explotacion` | `(total_gs_explot / total_primas_devengadas) * 100` | `total_primas_devengadas` por compañía |
| `pct_gastos_totales` | `(total_gs / total_primas_devengadas) * 100` | `total_primas_devengadas` por compañía |

División por cero protegida en SQL con `iif(c.total_primas_devengadas = 0, 0, ...)`. Totales por tipo en el Excel: recalculados como ratio agregado (`crear_hoja_principal_gastos` línea 109-117).

### `distribucion_inversiones`

| Métrica | Fórmula | Denominador |
|---|---|---|
| `total_inv` | `inmuebles_inversion + inversiones` | (no aplica, es absoluto) |
| `total_inv_inm` | `inmuebles_inversion` (alias) | — |
| `total_inv_liq` | `inversiones` (alias) | — |
| `pct_inmuebles_inversion` | `(inmuebles_inversion / (inmuebles_inversion + inversiones)) * 100` | `total_inv` por compañía |
| `pct_inversiones_liquidas` | `(inversiones / (inmuebles_inversion + inversiones)) * 100` | `total_inv` por compañía |

División por cero protegida en SQL con `iif(b.inmuebles_inversion + b.inversiones = 0, 0, ...)`. Totales por tipo: ratio agregado en Python (`crear_hoja_principal_inversiones` línea 124-128).

### `detalle_inmuebles` y `cuadro_nuevo`

Más simples — sólo sumas:

| Reporte | Métrica | Fórmula |
|---|---|---|
| `detalle_inmuebles` | `inmuebles_total` | `inmuebles_inversion + inmuebles_uso_propio` |
| `cuadro_nuevo` | `inmuebles` | `inmuebles_inversion + inmuebles_uso_propio` |
| `cuadro_nuevo` | `deudas_total_aseg` | `deudas_con_asegurados - deudas_con_asegurados_ac_reaseguros` |
| `cuadro_nuevo` | `deudas_neto` | `deudas_con_asegurados` (alias, no es cálculo) |

No hay porcentajes ni casos especiales en estos dos.

---

## Patrones transversales

Tres reglas que aplican a casi todos los reportes:

### 1. Promedio ponderado, no promedio simple

Cuando un Excel muestra "Total" para un grupo (tipo de compañía, ramo, etc.), los porcentajes en esa fila **siempre** se recalculan como ratio agregado:

```
pct_total = (sum(numerador) / sum(denominador)) * 100
```

No como `mean(pct_individuales)`. Esto es deliberado y se repite en todos los generadores. Si reproducís estos reportes desde cero hay que respetarlo, sino los totales no van a coincidir.

### 2. División por cero — cuatro estrategias diferentes

El proyecto no tiene una convención única. Según el reporte:

- **`iif(denom = 0, 0, ...)` en SQL** — primas_cedidas, ranking_comparativo, ranking_comparativo_por_ramo, distribucion_inversiones, detalle_gastos.
- **`if denom != 0 else 0` en Python** — sueldos_y_gastos, totales de varios reportes.
- **`(*)` con footnote** — sólo indicadores_solvencia.
- **Sin protección explícita** — cuadro_principal, ganaron_perdieron, los totales generales de algunos reportes. Si el denominador es 0 el SQL devuelve `NULL` y el Excel muestra vacío; en algunos cálculos del generador se podría producir `ZeroDivisionError`. Los totales agregados típicamente no llegan a cero porque suman cientos de compañías.

### 3. Las primas siempre son devengadas, salvo cuando son emitidas

Convención del dominio: los **resultados** (técnicos, financieros, ratios de gastos) se calculan sobre **primas devengadas** (las que la compañía ya ganó por el paso del tiempo). Los **rankings y participación de mercado** se calculan sobre **primas emitidas** (las que la compañía contrató, independientemente del devengamiento).

Por eso `cuadro_principal`, `ganaron_perdieron`, `sueldos_y_gastos` y `detalle_gastos` usan `primas_devengadas` como denominador, mientras que `ranking_comparativo`, `apertura_por_subramo` y `primas_cedidas_reaseguro` usan `primas_emitidas`.
