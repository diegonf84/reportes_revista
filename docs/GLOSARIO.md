# Glosario de negocio

Conceptos y convenciones del dominio asegurador que aparecen en este proyecto y no son obvios desde el código. Sirve como referencia rápida para entender por qué el sistema hace lo que hace.

---

## Sistema de períodos `YYYYPP`

El proyecto identifica cada trimestre fiscal con un entero de 6 dígitos: 4 dígitos de año + 2 dígitos de período (no de mes).

| Código `PP` | Trimestre fiscal | Mes calendario de cierre |
|---|---|---|
| `01` | T1 | **Marzo** |
| `02` | T2 | Junio |
| `03` | T3 | Septiembre |
| `04` | T4 | Diciembre |

> **Por qué `01` es marzo y no enero**: el año fiscal estándar de las compañías de seguros generales (no especiales) en Argentina **arranca el 1 de julio y termina el 30 de junio**. El primer cierre trimestral del año fiscal cae entonces en septiembre, pero el sistema regulatorio de la SSN reporta cuatrimestralmente desde marzo, ordenando los trimestres por mes calendario, no por trimestre del año fiscal.
>
> En la práctica el código `PP` mapea al **trimestre del año calendario que termina con el cierre del balance**: marzo es `01` porque es el primer cierre trimestral del año calendario, no porque sea el primer trimestre del año fiscal.

**Ejemplos**:
- `202501` = balance cerrado al 31 de marzo de 2025.
- `202504` = balance cerrado al 31 de diciembre de 2025.

**No confundir con el formato mensual `YYYYMM`** que usa exclusivamente la tabla `monthly_ipc_data` (donde `202503` significa marzo 2025, no septiembre).

---

## Compañías especiales: `0829`, `0541`, `0686`

Tres compañías reportan sus balances con un **ciclo de cierre fiscal distinto** al resto del mercado. Aparecen como caso particular en todos los módulos `crea_tabla_*_corregida.py`.

| `cod_cia` | Cierre fiscal | Año fiscal |
|---|---|---|
| `0829`, `0541`, `0686` | **31 de diciembre** | enero–diciembre (calendario) |
| Resto del mercado | 30 de junio | julio–junio |

Esto rompe la comparabilidad directa: si en un período (digamos `202503` = septiembre 2025) sumás "primas emitidas anuales" para todas las compañías, las **comunes te dan los últimos 12 meses** (octubre 2024 – septiembre 2025), pero las **especiales te dan enero – septiembre 2025** (sólo 9 meses acumulados).

El proyecto resuelve esto con las tablas `*_corregida_actual`, que aplican fórmulas de **12 meses móviles** sobre las compañías especiales según el trimestre. Ver `TABLAS.md` y la docstring de `modules/crea_tabla_subramos_corregida.py` para las fórmulas exactas.

---

## "Corregida" — qué significa en términos de negocio

Cuando ves una tabla con sufijo `_corregida_actual` (o un módulo `crea_tabla_*_corregida.py`), "corregida" significa: **datos homogeneizados para que todas las compañías reporten el mismo período de 12 meses**, independientemente de su cierre fiscal.

Es un ajuste **exclusivamente para las tres compañías especiales**. Las compañías comunes pasan tal cual del período actual contra el mismo período del año anterior; las especiales reciben fórmulas de 12 meses móviles que combinan trimestres parciales con cierres anteriores.

Sin esa corrección, los rankings y comparaciones interanuales darían erróneos para las especiales (por sobre o sub-reporte de meses).

> Ojo: "corregida" **no significa "datos depurados"** ni "datos validados". Es estrictamente un ajuste de ventana temporal.

---

## Ramo vs subramo

Los dos niveles forman una jerarquía contable definida por la SSN:

- **Subramo** (`cod_subramo`, ej. `'1.020.01'`): granularidad mínima del reporte regulatorio. Identifica un producto o cobertura específica (`Automotores - Cascos y Otras Cob.`, `Vida - Individual`, `RC - Mala Práctica Médica`).
- **Ramo** (`ramo_denominacion`, ej. `'Automotores'`): agrupación comercial a la que pertenecen varios subramos (`Automotores`, `Responsabilidad Civil`, `Vida`, `Riesgos del Trabajo`).

Un ramo se compone de uno o más subramos. La tabla `datos_ramos_subramos` contiene el mapeo `cod_subramo → ramo_denominacion` (y también `subramo_denominacion`, el nombre legible del subramo).

**Cuándo usar cada nivel**:
- Reportes a nivel ejecutivo / participación de mercado → ramo.
- Análisis de mix de productos, comparaciones operativas finas → subramo.
- Cuando el modelo necesita evitar discontinuidades por reasignación de subramos entre ramos → totales por compañía (que viven en `base_cias_corregida_actual`).

---

## Unidades de los importes

- **Todos los importes monetarios están en pesos argentinos** (ARS), sin escala. Un valor `1500000000` significa $1.500.000.000.
- **Pero los Excels los muestran en miles**. El formato openpyxl `'#,##0,'` (con coma final) divide visualmente por 1000 al renderizar, sin alterar el dato. Por eso las planillas tienen títulos como "EN MILES DE PESOS" y los números se ven con un cero menos que el subyacente.
- **Las primas cedidas son positivas** en este modelo, no negativas. Para calcular "primas retenidas" hay que hacer `primas_emitidas - primas_cedidas` (no sumar).
- **El impuesto a las ganancias** viene con signo positivo desde la fuente; en `ganaron_perdieron` el SQL lo invierte (`* (-1)`) antes de sumarlo al resultado del ejercicio.

---

## Variación comparativa

Los reportes comparativos (`ranking_comparativo`, `ranking_comparativo_por_ramo`) calculan variación interanual con la fórmula:

```
variacion (%) = ((primas_emitidas / primas_emitidas_anterior) - 1) * 100
```

Donde `primas_emitidas_anterior` viene **ya corregida** desde las tablas `*_corregida_actual` para mantener coherencia entre actual y anterior.

**Casos especiales**:
- Si `primas_anterior = 0` → la variación se fija en `0` (no NaN, no infinito) tanto en SQL (`iif(primas_anterior=0, 0, ...)`) como en los recálculos de Python.
- Si la compañía **no existía** en el período anterior (caso compañía nueva), aparece con `primas_anterior = 0` y por ende `variacion = 0`. Eso enmascara que sería un crecimiento "infinito"; tenerlo en cuenta al leer el ranking.
- Si la compañía existía antes pero no ahora, queda fuera del reporte (los JOIN son LEFT desde el período actual).

**Nota técnica**: `base_ramos_corregida_actual` y `base_cias_corregida_actual` usan `FULL OUTER JOIN` para las compañías comunes en T1, T2 y T4, con lo cual sí mantienen compañías que aparecieron sólo en uno de los dos períodos. `base_subramos_corregida_actual` usa `LEFT JOIN` y filtra a las del período actual.

---

## Tipos de compañías

Cinco categorías de compañías aseguradoras conviven en `datos_companias.tipo_cia`. Cada una está regulada de forma distinta y aparece en reportes diferentes.

| `tipo_cia` | Qué cubre | Comentarios |
|---|---|---|
| **Generales** | Patrimoniales: Automotores, Combinado Familiar, Caución, Incendio, RC, Riesgos Agropecuarios, Robo, Transporte, Técnico, Motovehículos, Otros riesgos de daños patrimoniales, Riesgos del Trabajo (cuando lo cubren), accidentes a pasajeros, transporte público de pasajeros. | El "core" del mercado. Mayor cantidad de compañías y volumen. |
| **Vida** | Vida individual y colectivo, Salud, Sepelio, Accidentes Personales, Saldo Deudor, seguros obligatorios. | Suelen ser compañías mixtas o especializadas en personas. |
| **Retiro** | Seguros de retiro individual y colectivo. Producto financiero de largo plazo (similar a previsión privada). | **Categoría especial**: muchas tienen `deudas_con_asegurados = 0` por el modelo de negocio (no hay siniestros típicos), por eso `indicadores_solvencia` muestra `(*)` para ellas. Algunos reportes (`primas_cedidas_reaseguro`) las excluyen explícitamente. |
| **ART** | Aseguradoras de Riesgos del Trabajo. Cubren accidentes laborales y enfermedades profesionales. | Submercado especializado, regulado por la SRT además de la SSN. En `cuadro_principal` aparecen en su propia hoja. |
| **M.T.P.P.** | Mutuales de Transporte Público de Pasajeros. | Categoría chica y específica del transporte. En el código se renombra a `MTTP` para los nombres de hoja Excel (Excel no admite `.` en sheet names cuando terminan con punto). |

Los reportes filtran o agrupan por `tipo_cia` con listas hardcoded en cada generador. Ver `MAPEO_REPORTES.md` para qué reporte incluye qué tipo.

---

## Ciclo de cierre fiscal y por qué importa

Las compañías de seguros en Argentina cierran balance trimestralmente y reportan a la SSN. El "ciclo de cierre" es el calendario en que cada compañía consolida y publica sus números.

**Por qué importa para este proyecto**:

1. **Ventana de 12 meses móviles**: la mayoría de las métricas de mercado (primas anuales, ranking comparativo, variación interanual) se calculan sobre los últimos 12 meses, no sobre el trimestre individual. El ciclo de cierre define qué meses entran en esa ventana.
2. **Comparabilidad**: si una compañía cierra en junio y otra en diciembre, el "primas anuales" reportado al cierre de septiembre 2025 cubre ventanas distintas — esto rompe rankings si no se corrige.
3. **Cuándo llegan los datos**: una compañía publica sus números semanas después del cierre. Por eso un período se considera "completo" cuando todas las compañías han reportado, lo cual depende del cierre y los plazos regulatorios. La verificación de qué compañías faltan se hace en `modules/check_cantidad_cias.py`.
4. **Las tres especiales**: como cierran en diciembre, en cada trimestre del año calendario hay que aplicar una fórmula distinta para llevar sus datos a "12 meses móviles" alineados con el trimestre del resto del mercado. Ver `TABLAS.md` y la docstring de `modules/crea_tabla_subramos_corregida.py:1-46` para las fórmulas detalladas.

**Resumen práctico**: cuando veas un reporte que no cuadra entre dos compañías para el mismo período, lo primero a chequear es si una es especial (`0829`, `0541`, `0686`) y si los datos están leyendo desde la tabla cruda (`base_subramos`) o desde la corregida (`base_subramos_corregida_actual`).
