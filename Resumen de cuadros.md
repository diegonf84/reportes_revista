# Resumen de Cuadros

## 1. Cuadro Principal
**Archivo:** `{periodo}_cuadro_principal.xlsx`

**Propósito:** Mostrar resultados técnicos totales por ramo (primas emitidas, primas devengadas, siniestros, gastos y resultados).

**Nivel de información:** Compañía-Período-Ramo

**Ramos incluidos:**
- Generales: Automotores, Incendio, RC, Motovehículos, Combinado Familiar, Transporte, Caución, Técnico, etc.
- Vida: Vida, Accidentes Personales, Salud, Sepelio, Retiro
- ART: Riesgos del Trabajo

**Descripción:** Presenta 3 hojas (Generales, Vida, ART). Cada hoja incluye un cuadro resumen con todos los ramos y cuadros individuales por ramo con detalle de cada compañía. Muestra valores monetarios y porcentajes calculados sobre primas devengadas.

---

## 2. Cuadro Nuevo
**Archivo:** `{periodo}_cuadro_nuevo.xlsx`

**Propósito:** Balance patrimonial simplificado mostrando producción, activos y pasivos principales.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados (no distingue por tipo de ramo)

**Descripción:** Una sola hoja con secciones por tipo de compañía (ART, Generales, M.T.P.P., Retiro, Vida). Muestra producción, disponibilidades, inversiones, inmuebles, deudas con asegurados, siniestros a/c reaseguros, deudas neto y patrimonio neto. Incluye totales por tipo.

---

## 3. Ganaron y Perdieron
**Archivo:** `{periodo}_ganaron_perdieron.xlsx`

**Propósito:** Clasificar compañías según obtuvieron ganancias o pérdidas, mostrando resultados técnicos, financieros y del ejercicio.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados

**Descripción:** Hojas separadas por tipo de compañía (ART, Generales, M.T.P.P., Retiro, Vida). Cada hoja tiene dos secciones: "LAS QUE GANARON" y "LAS QUE PERDIERON". Muestra resultados técnicos, resultado financiero, resultado de operaciones extraordinarias, impuesto a las ganancias y resultado del ejercicio (en $ y %).

---

## 4. Primas Cedidas al Reaseguro
**Archivo:** `{periodo}_primas_cedidas_reaseguro.xlsx`

**Propósito:** Analizar nivel de cesión al reaseguro mostrando producción, primas cedidas y primas retenidas.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados excepto Retiro

**Descripción:** Hojas separadas por tipo (ART, Generales, MTTP, Vida). Muestra producción total, primas cedidas al reaseguro ($ y %), y primas netas de reaseguro/retenidas ($ y %). Los porcentajes se calculan sobre producción total.

---

## 5. Ranking de Producción
**Archivo:** `{periodo}_ranking_produccion.xlsx`

**Propósito:** Rankings de producción con diferentes niveles de agregación y participación de mercado.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados

**Descripción:** Tres hojas: 1) "Ranking Generales" - solo compañías generales ordenadas por producción descendente. 2) "Varios" - secciones por tipo con % del rubro y % acumulado, más cuadro resumen lateral. 3) "Ranking" - todas las compañías ordenadas por producción total descendente.

---

## 6. Ranking Comparativo
**Archivo:** `{periodo}_ranking_comparativo.xlsx`

**Propósito:** Comparar producción del período actual con el anterior, mostrando variaciones porcentuales.

**Nivel de información:** Compañía-Período con comparativa histórica (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados

**Descripción:** Tres hojas: 1) "Ranking" - secciones por tipo ordenadas alfabéticamente. 2) "Ranking Total Comparativo" - todas las compañías ordenadas por producción descendente. 3) "base_detalle" - datos completos incluyendo primas del período anterior.

---

## 7. Ranking Comparativo por Ramo
**Archivo:** `{periodo}_ranking_comparativo_por_ramo.xlsx`

**Propósito:** Comparar producción del período actual con el anterior desagregada por ramo individual.

**Nivel de información:** Compañía-Período-Ramo con comparativa histórica

**Ramos incluidos:** Todos los ramos disponibles (Automotores, Incendio, RC, Vida, Salud, ART, etc.)

**Descripción:** Dos hojas: 1) "Ranking" - secciones separadas por ramo, ordenamiento alfabético por entidad. 2) "base_detalle" - datos completos con ramo, entidad, primas actuales, variación % y primas anteriores.

---

## 8. Apertura por Subramo
**Archivo:** `{periodo}_apertura_por_subramo.xlsx`

**Propósito:** Desglosar producción de ramos clave en sus subramos componentes con participación de mercado.

**Nivel de información:** Compañía-Período-Subramo (máxima granularidad)

**Ramos y subramos incluidos:**
- Combinado Familiar e Integral: Combinado Familiar, Integral de Comercio, Otros
- Automotores: Cascos y Otras Coberturas, RC Exclusivo
- Motovehículos: Cascos y Otras Coberturas, RC Exclusivo
- RC: Mala Praxis Médica, Otras Profesiones, Accidentes de Trabajo, Otros
- Otros Riesgos Patrimoniales: Cristales, Riesgos Varios, Otros
- Accidentes Personales: Individual, Colectivo
- Salud: Individual, Colectivo
- Vida: Individual, Colectivo, Obligatorios, Saldo Deudor
- Sepelio: Individual, Colectivo
- Retiro: Individual, Colectivo

**Descripción:** Una hoja por ramo principal. Dentro de cada hoja, secciones por subramo ordenadas por producción descendente. Muestra producción, % del total del subramo y % acumulado.

---

## 9. Sueldos y Gastos
**Archivo:** `{periodo}_sueldos_y_gastos.xlsx`

**Propósito:** Analizar estructura de gastos mostrando peso de sueldos y categorías de gastos sobre primas devengadas.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados

**Descripción:** Hojas por tipo de compañía (ART, Generales, M.T.P.P., Retiro, Vida) más hoja "base_detalle". Muestra: % sueldos y cargas sociales, % total gastos de producción y % total gastos (todos sobre primas devengadas). Incluye totales ponderados por tipo.

---

## 10. Detalle de Gastos
**Archivo:** `{periodo}_detalle_gastos.xlsx`

**Propósito:** Análisis detallado de estructura de gastos separando gastos de producción, explotación y totales.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados

**Descripción:** Dos hojas: 1) "Detalle Gastos" - secciones por tipo con solo porcentajes. 2) "base_detalle" - valores absolutos y porcentajes consolidados. Muestra % gastos de producción, % gastos de explotación y % gastos totales (sobre primas devengadas).

---

## 11. Detalle de Inmuebles
**Archivo:** `{periodo}_detalle_inmuebles.xlsx`

**Propósito:** Mostrar tenencia de inmuebles distinguiendo entre inmuebles de inversión y de uso propio.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados

**Descripción:** Una sola hoja con secciones por tipo de compañía (ART, Generales, M.T.P.P., Retiro, Vida). Muestra inmuebles de inversión, inmuebles de uso propio y total inmuebles. Incluye totales por tipo.

---

## 12. Distribución de Inversiones
**Archivo:** `{periodo}_distribucion_inversiones.xlsx`

**Propósito:** Analizar composición de cartera de inversiones mostrando peso de inmuebles de inversión versus inversiones líquidas.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados

**Descripción:** Dos hojas: 1) "Distribucion Inversiones" - secciones por tipo con total y porcentajes. 2) "base_detalle" - valores absolutos consolidados. Muestra total de inversiones, % de inmuebles de inversión y % de inversiones líquidas.

---

## 13. Indicadores de Solvencia
**Archivo:** `{periodo}_indicadores_solvencia.xlsx`

**Propósito:** Evaluar capacidad de responder a obligaciones con asegurados mediante ratios de liquidez y solvencia.

**Nivel de información:** Compañía-Período (todos los ramos consolidados)

**Ramos incluidos:** Todos consolidados

**Descripción:** Dos hojas: 1) "Indicadores Solvencia" - secciones por tipo (ART, Generales, M.T.P.P., Retiro, Vida) con ratios calculados y totales por tipo. 2) "base_detalle" - valores absolutos de componentes (inmuebles, inversiones, disponibilidades, deudas) y ratios calculados, agrupado por tipo.

**Fórmulas:**

- Ratio 1: (Disponibilidades + Inversiones) / Deudas con Asegurados × 100
- Ratio 2: (Disponibilidades + Inversiones + Inmuebles Inversión) / Deudas con Asegurados × 100
- Cuando deudas = 0, muestra (*) con nota explicativa
---

## Notas Generales

**Qué significa "corregida":**
Aplica ajustes específicos para ciertas compañías en períodos particulares (ejemplo: septiembre) para asegurar consistencia en reportes.

**Tipos de compañías:**
- ART: Aseguradoras de Riesgos del Trabajo
- Generales: Seguros patrimoniales
- M.T.P.P./MTTP: Mutual de Transporte Público de Pasajeros
- Retiro: Seguros de retiro
- Vida: Seguros de personas

**Formatos:**
- Valores monetarios: Miles de pesos
- Porcentajes: Con 1 o 2 decimales según el cuadro
- Períodos: Formato YYYYMM (ejemplo: 202501)

**Variaciones:**
La variacion corresponde a la comparacion con el mismo periodo de un año anterior

Variación = ((Actual / Anterior) - 1) × 100

