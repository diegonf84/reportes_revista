# Briefing para el agente de reportes

Este documento es un brief para diseñar el **agente AI** que va a operar sobre el proyecto `reportes_revista`. No es código del agente — es la especificación de qué tiene que saber, qué puede hacer, y qué reglas no puede violar.

El agente se va a desarrollar en otro repo. Este archivo es lo que viaja con él como contexto.

---

## 1. Propósito

El agente asiste al usuario (analista de seguros) en tareas operativas y analíticas sobre los datos del balance trimestral del mercado asegurador argentino. Los tres usos principales:

1. **Generar reportes** — orquestar el pipeline para producir los Excels del trimestre.
2. **Responder preguntas** sobre los datos y los reportes ya generados (rankings, variaciones, composición, etc.).
3. **Verificar balances** — validar consistencia, detectar datos faltantes o desactualizados, comparar entre períodos.

Eventualmente puede crecer a otras tareas (análisis ad-hoc, comparaciones inter-compañías, alertas), pero estos tres son el núcleo.

---

## 2. Casos de uso concretos

### A. Generación de reportes

- "Generá los reportes para el trimestre 202503."
- "Faltan los reportes 4 y 7 del último trimestre, regeneralos."
- "Corré el pipeline completo desde cero para 202504."

### B. Preguntas analíticas

- "¿Cuál fue el ranking de las top 10 compañías por primas emitidas en automotores el último trimestre?"
- "¿Cuánto creció el ramo riesgos del trabajo entre 202502 y 202503?"
- "Dame la siniestralidad de Sancor en patrimoniales para los últimos 4 trimestres."
- "¿Qué compañías ganaron market share en automotores este trimestre?"
- "¿Cuáles son los 5 subramos con mayor crecimiento real (ajustado por IPC) año contra año?"

### C. Verificación / control de calidad

- "¿La tabla `base_subramos_corregida_actual` está al día para 202503?"
- "¿Faltan compañías en el último período cargado?"
- "Las primas emitidas de la compañía 0829 dan raras este trimestre, mostrame el detalle."
- "Compará los totales de primas del CSV con los del Excel del reporte 4 para detectar diferencias."

### D. Apoyo a investigación

- "Explicame por qué este número de siniestralidad da negativo."
- "¿Qué cuentas componen el concepto 'gastos de producción' en el reporte 5?"
- "Para el ramo caución, ¿qué compañías entran en el reporte y por qué?"

---

## 3. Lecturas obligatorias antes de operar

El agente debe cargar/leer estos documentos del repo `reportes_revista` como contexto base. Están en `docs/`:

| Documento | Para qué sirve |
|---|---|
| `docs/TABLAS.md` | Catálogo de tablas SQLite, su origen, columnas clave, relaciones. **Mapa del territorio.** |
| `docs/MAPEO_REPORTES.md` | Qué reporte usa qué tabla y qué columnas, en qué orden generarlos. **Cuando el usuario pida un reporte.** |
| `docs/GLOSARIO.md` | YYYYPP, compañías especiales (0829/0541/0686), "corregida", ramo vs subramo, ciclo fiscal. **Para entender la pregunta del usuario.** |
| `docs/METRICAS.md` | Fórmulas exactas de las métricas calculadas (siniestralidad, gastos, resultado técnico, etc.). **Cuando el usuario pregunte por un número.** |
| `docs/LIMITACIONES_PIPELINE.md` | Qué se puede romper silenciosamente, cómo detectarlo, cuándo regenerar. **Reglas operativas no negociables.** |
| `docs/MODULES.md` | Inventario de scripts/módulos del pipeline. |
| `README.md` | Overview general + sección "TODO técnico" con bugs conocidos. |

**Regla**: si el agente no encontró el dato en estos documentos y la respuesta dependería de algo del código, debe leer el módulo correspondiente antes de responder, no inventar.

---

## 4. Capacidades necesarias

### Lectura de datos
- **SQL contra `data/revista_tr_database.db`** (SQLite): consultas a `base_balance_ultimos_periodos`, `base_subramos`, `base_ramos`, `base_otros_conceptos`, las `*_corregida_actual`, y las tablas de configuración (`datos_companias`, `datos_ramos_subramos`, `parametros_reportes`, `conceptos_reportes`, `datos_ipc`).
- **Lectura de CSVs** generados en `outputs/csv_results/` (12 reportes intermedios).
- **Lectura de Excels** ya generados en `outputs/excel_results/` (sólo si el usuario quiere validar o re-leer un reporte ya producido).

### Ejecución del pipeline
- Invocar los módulos del pipeline como subprocess o importarlos:
  - `modules/crea_tabla_ultimos_periodos.py`
  - `modules/crea_tabla_subramos.py`, `crea_tabla_ramos.py`, `crea_tabla_otros_conceptos.py`
  - `modules/crea_tabla_subramos_corregida.py`, `crea_tabla_ramos_corregida.py`, `crea_tabla_cias_corregida.py`
  - `ending_files/generate_all_reports.py {periodo}`
  - `excel_generators/generate_all_excel.py {periodo}`
- Idealmente respetando la **misma lógica que `app/routes/data_processing.py`** (los endpoints `/api/create-subramos`, `/api/generate-all-reports`, etc.). Si el agente puede reusar esos endpoints HTTP en lugar de relanzar subprocess, mejor — son la API ya pensada para orquestación.

### Comunicación
- Responder en lenguaje natural, en español.
- Devolver tablas / dataframes formateados cuando la pregunta lo amerite.
- Cuando ejecuta el pipeline, **mostrar el progreso** (qué módulo está corriendo, cuánto tardó). El pipeline completo puede demorar varios minutos.

---

## 5. Herramientas (tools) sugeridas para el agente

Un mapeo razonable de herramientas si lo armás con un framework tipo Claude Agent SDK / LangGraph / MCP:

| Tool | Descripción | Notas |
|---|---|---|
| `sql_query(query: str)` | Ejecuta SELECT contra la BD. Read-only. | Limitar a SELECT — nunca DROP/UPDATE/DELETE. |
| `list_tables()` | Lista tablas de la BD con conteo de filas y, si aplica, período. | Útil como primer paso de cualquier verificación. |
| `check_period_status(periodo: int)` | Verifica si un período está disponible en `datos_balance` y si las corregidas parecen al día. | Implementa las heurísticas de `LIMITACIONES_PIPELINE.md`. |
| `run_pipeline_step(step: str, periodo: int)` | Corre un módulo específico (`subramos`, `ramos`, `corregidas`, `otros_conceptos`, `reports`, `excel`). | Puede mapearse a los endpoints del web UI. |
| `run_full_pipeline(periodo: int)` | Cadena completa para un período: ultimos_periodos → subramos/ramos/otros → corregidas → reports → excel. | Atómico desde la perspectiva del usuario. |
| `read_csv_report(name: str)` | Lee un CSV de `outputs/csv_results/`. | Usar nombres canónicos de `MAPEO_REPORTES.md`. |
| `read_excel_report(name: str, sheet: str = None)` | Lee un Excel ya generado. | Sólo lectura. |
| `lookup_company(cod_or_name: str)` | Busca compañía en `datos_companias` por código o por substring del nombre. | Para cuando el usuario diga "Sancor" en vez de "0001". |
| `lookup_concept(name: str)` | Busca concepto en `conceptos_reportes` y muestra qué cuentas mapea. | Para preguntas tipo "qué incluye 'gastos de producción'". |
| `ipc_inflate(monto: float, periodo_origen: int, periodo_destino: int)` | Ajusta montos por IPC usando `datos_ipc`. | Para análisis de variación real. |

Si arrancás simple, los primeros 3 (`sql_query`, `run_pipeline_step`, `read_csv_report`) cubren ~80% de los casos.

---

## 6. Reglas operativas no negociables

Estas reglas vienen de `docs/LIMITACIONES_PIPELINE.md` y son las que el agente debe respetar siempre:

1. **Antes de generar reportes para un período X**: regenerar las 3 tablas corregidas (`subramos`, `ramos`, `cias`). No hay forma confiable de saber si están al día — las tablas `*_corregida_actual` no tienen columna `periodo`.

2. **Antes de eso**: chequear que `base_balance_ultimos_periodos` cubra al menos 2 años hacia atrás del período objetivo. Si no, las correcciones para T1/T2 dejan **fuera del reporte a las compañías especiales 0829, 0541, 0686** sin error visible.

3. **Si cambia el período objetivo**: regenerar también `base_otros_conceptos` (sino los reportes 1, 3, 10, 12, 13 quedan con datos viejos).

4. **Validación de período**: usar el formato YYYYPP estricto (6 dígitos, año razonable, trimestre 1-4). Rechazar períodos posteriores al máximo de `datos_balance` — no tiene sentido.

5. **No confiar en "el Excel se generó OK"**: validación tiene que ser semántica (chequear un número conocido), no estructural. El pipeline tiende a generar archivos consistentes en formato pero con datos del período anterior cuando faltan pasos.

6. **Compañías especiales (0829, 0541, 0686)**: cierran balance en diciembre, no en junio. La corrección de 12 meses se hace para alinearlas. Si el usuario pregunta por estas compañías sin contexto, vale la pena recordárselo.

7. **Read-only por defecto**: el agente puede consultar y ejecutar el pipeline, pero **no debe modificar manualmente la BD**. Cargas iniciales (`carga_base_principal.py`, `create_*.py`) requieren confirmación humana porque tocan datos de configuración.

8. **Confirmar antes de regenerar**: si el usuario pide algo que implica regenerar el pipeline completo (varios minutos de cómputo), el agente debe avisar y confirmar — no ejecutar a ciegas.

---

## 7. Flujos típicos

### Flujo A — "Generá los reportes para 202503"

```
1. Validar período (formato, rango, que exista en datos_balance).
2. Verificar base_balance_ultimos_periodos:
   - ¿Contiene 202503? ¿Contiene 202301 (2 años atrás)?
   - Si no, correr crea_tabla_ultimos_periodos.py 202503.
3. Verificar base_subramos / base_ramos:
   - ¿Tienen filas para 202503?
   - Si no, correr crea_tabla_subramos.py y crea_tabla_ramos.py.
4. Correr crea_tabla_otros_conceptos.py 202503.
5. Correr las 3 corregidas (subramos, ramos, cias) para 202503.
6. Correr generate_all_reports.py 202503.
7. Correr generate_all_excel.py 202503.
8. Reportar al usuario: archivos generados, ubicación, tiempo total.
9. Sugerir validación semántica (un número conocido).
```

### Flujo B — "¿Cuánto creció el ramo automotores entre 202502 y 202503?"

```
1. Confirmar el sentido de "creció": ¿primas emitidas? ¿pólizas? ¿real o nominal?
2. SELECT primas_emitidas FROM base_ramos WHERE ramo='automotores' AND periodo IN (202502, 202503)
3. Si la pregunta es "real", aplicar IPC con datos_ipc.
4. Devolver: monto absoluto + variación nominal + (si aplica) variación real.
5. Mencionar que es primas emitidas (no devengadas) y que 202503 es el cierre de septiembre.
```

### Flujo C — "Verificá si los datos de 202503 están al día"

```
1. SELECT MAX(periodo), MIN(periodo) FROM base_balance_ultimos_periodos
   → ¿Cubre 202503 y 202301?
2. SELECT MAX(periodo) FROM base_subramos / base_ramos
   → ¿Llegan a 202503?
3. SELECT DISTINCT periodo FROM base_otros_conceptos
   → ¿Es 202503?
4. Para las corregidas: como no se puede determinar el período desde la tabla,
   sugerir regenerarlas o verificar logs.
5. Devolver: estado por tabla + recomendación accionable.
```

### Flujo D — "Compará primas de Sancor en automotores entre los últimos 4 trimestres"

```
1. lookup_company("Sancor") → cod_cia.
2. SELECT periodo, primas_emitidas FROM base_subramos
   WHERE cod_cia=? AND ramo_codigo=? ORDER BY periodo DESC LIMIT 4.
3. Calcular variación trimestre a trimestre y respecto al mismo trimestre del año anterior.
4. Si se piden 4 trimestres consecutivos, mencionar el ciclo fiscal de la compañía.
5. Formato: tabla con período, monto, variación %.
```

---

## 8. Decisiones abiertas — para definir antes de programar

Estas son cuestiones que el usuario tiene que decidir cuando arme el agente:

1. **Stack del agente**: ¿Claude Agent SDK con tools nativas? ¿LangGraph? ¿Una orquestación simple con function calling de la API? Recomendado arrancar con Claude Agent SDK — el menor overhead.

2. **Cómo se conecta al pipeline**:
   - **Opción A**: el agente vive en otro repo y llama al web UI (`localhost:5000/api/...`) por HTTP. Más limpio, requiere que el web UI esté corriendo.
   - **Opción B**: el agente importa los módulos de `reportes_revista` directamente (instala el paquete o referencia el path). Más rápido, más acoplado.
   - **Opción C**: subprocess (lanza `python modules/...py`). Más simple, peor manejo de errores.

3. **Modelo**: Claude Sonnet 4.6 alcanza para casi todo y es 5× más barato que Opus. Para el caso de uso (preguntas sobre datos + ejecución de pipeline), sobra. Reservar Opus 4.7 para casos donde haga falta razonamiento sobre métricas complejas.

4. **Memoria / persistencia**: ¿el agente recuerda conversaciones previas? ¿guarda preferencias del usuario (formato de tabla, idioma, qué compañías sigue)? Para empezar, sin memoria.

5. **Autorización**: ¿quién puede correr el pipeline? Hoy `data_processing.py` no tiene auth. Si el agente expone esto, conviene agregar al menos un check de identidad básico.

6. **Salida de reportes**: ¿el agente devuelve la ruta del Excel? ¿lo sube a algún lado (S3, Google Drive)? Hoy el pipeline tiene la lógica de subir parquet a S3 — definir si el agente debe orquestar eso también.

7. **Validación semántica automática**: ¿el agente debe correr checks post-generación (algún número conocido vs valor esperado) o sólo reporta que terminó? Para un MVP basta con reportar; para producción conviene tener checks.

---

## 9. Sugerencia de fases

**Fase 1 — Solo lectura** (1-2 días)
- Tools: `sql_query`, `list_tables`, `lookup_company`, `lookup_concept`, `read_csv_report`.
- Cubre: preguntas analíticas, verificación de datos, exploración.
- Sin riesgo de romper nada.

**Fase 2 — Verificación de pipeline** (1 día)
- Tool: `check_period_status`.
- Cubre: "¿está al día? ¿qué falta?".

**Fase 3 — Ejecución de pipeline** (2-3 días)
- Tools: `run_pipeline_step`, `run_full_pipeline`.
- Requiere confirmación del usuario antes de correr.
- Cubre: el caso de uso "generá los reportes".

**Fase 4 — Cosas más avanzadas**
- IPC, comparaciones cruzadas, alertas, validación semántica automática.

---

## 10. Qué NO debe hacer el agente

- No modificar `parametros_reportes`, `conceptos_reportes`, `datos_companias`, `datos_ramos_subramos`. Son configuración de negocio que se cambia con criterio humano.
- No correr cargas iniciales (`carga_base_principal.py`, `create_*.py`) sin confirmación explícita.
- No inferir negocio que no esté en los docs. Si el usuario pregunta algo cuya respuesta no está en `GLOSARIO.md` ni en el código, debe decir "no lo sé" y pedir aclaración, no improvisar.
- No mezclar montos nominales con reales sin avisar al usuario qué eligió.
- No mezclar conceptos de "primas emitidas" con "primas devengadas" — son cosas distintas (ver `GLOSARIO.md`).
- No asumir que las `*_corregida_actual` están al día. Siempre verificar o regenerar.

---

## 11. Recursos del repo

```
reportes_revista/
├── data/
│   └── revista_tr_database.db          ← BD SQLite (lectura para el agente)
├── modules/                             ← Scripts del pipeline intermedio
├── ending_files/
│   └── generate_all_reports.py         ← Genera los 12 CSVs
├── excel_generators/
│   └── generate_all_excel.py           ← Genera los 13 Excels
├── outputs/
│   ├── csv_results/                    ← CSVs intermedios (12 archivos)
│   └── excel_results/                  ← Excels finales (13 archivos)
├── app/
│   ├── routes/data_processing.py       ← API HTTP del web UI (referencia para orquestación)
│   └── ...
└── docs/                                ← Documentación que el agente debe cargar
    ├── TABLAS.md
    ├── MAPEO_REPORTES.md
    ├── GLOSARIO.md
    ├── METRICAS.md
    ├── LIMITACIONES_PIPELINE.md
    ├── MODULES.md
    └── AGENTE.md                       ← Este documento
```

---

## 12. Próximos pasos sugeridos

1. Decidir stack (Claude Agent SDK + tools custom es lo recomendado).
2. Decidir si el agente vive en otro repo y llama por HTTP, o si importa los módulos directamente.
3. Empezar por Fase 1 (read-only) — implementar `sql_query` + cargar los docs de `docs/` como contexto del system prompt.
4. Validar con 5-10 preguntas reales del caso de uso B (preguntas analíticas) antes de avanzar a ejecución.
5. Recién después agregar las tools de ejecución de pipeline.
