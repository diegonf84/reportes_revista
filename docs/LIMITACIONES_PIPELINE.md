# Limitaciones del pipeline

Documento de advertencias sobre cómo funciona realmente el pipeline de datos: qué se puede romper silenciosamente, qué tablas son traicioneras y cómo detectarlo. Pensado para evitar que un agente o un humano genere reportes "exitosos" pero con datos viejos.

---

## Tablas que NO son históricas — sólo contienen un período

Cuatro tablas se sobreescriben en cada ejecución y siempre contienen un único período. **No mantienen historial**. Si las consultás para un período distinto al de la última corrida, no encontrás nada (o peor, datos del período viejo que parecen actuales).

| Tabla | Período que contiene | Módulo que la genera |
|---|---|---|
| `base_otros_conceptos` | El último período cargado en `base_balance_ultimos_periodos` (o el que se pasa por argumento) | `modules/crea_tabla_otros_conceptos.py` |
| `base_subramos_corregida_actual` | El que se pasa por argumento (obligatorio) | `modules/crea_tabla_subramos_corregida.py` |
| `base_ramos_corregida_actual` | El que se pasa por argumento (obligatorio) | `modules/crea_tabla_ramos_corregida.py` |
| `base_cias_corregida_actual` | El que se pasa por argumento (obligatorio) | `modules/crea_tabla_cias_corregida.py` |

**Implicancia**: si pedís un reporte para período X pero la última corrida de los módulos corregidos fue para el período X−1, **los reportes 4, 6, 7 y 8** (`apertura_por_subramo`, `ranking_comparativo`, `ranking_comparativo_por_ramo`, `ranking_generales`) salen **con datos del período viejo**, sin que ningún logging avise.

### Particularidad de las tablas `*_corregida_actual`

**No tienen columna `periodo`**. Mirando la tabla no se puede saber para qué período fueron generadas. Las formas de averiguarlo son:
- Recordar la última corrida.
- Revisar los logs de la última ejecución.
- Inferir cruzándola contra `base_subramos` (`max(b.primas_emitidas) WHERE periodo = ?` para ver cuál cuadra).

Para automatización, la estrategia segura es **regenerar siempre las corregidas antes de los reportes**.

---

## Orden estricto de creación de tablas

Las tablas se construyen en cadena. Saltarse un paso o desordenarlos rompe los siguientes módulos. Aunque `crea_tabla_subramos.py` y `crea_tabla_ramos.py` validan que las tablas previas existan (con `db_manager.table_exists()`), no validan que estén actualizadas.

### Cadena obligatoria

```
1. CARGAS INICIALES (una vez por proyecto, o cuando llega config nueva):
   - datos_balance               ← carga_base_principal.py (de archivos .mdb)
   - datos_companias             ← create_nombres_cias.py
   - datos_ramos_subramos        ← create_nombres_ramos.py
   - conceptos_reportes          ← create_conceptos_reportes.py + insert_concepts.py
   - parametros_reportes         ← create_parametros_reportes.py

2. PIPELINE INTERMEDIO (cada vez que llega un período nuevo):
   - base_balance_ultimos_periodos    ← crea_tabla_ultimos_periodos.py
       ↓ requiere
   - base_subramos                    ← crea_tabla_subramos.py
   - base_ramos                       ← crea_tabla_ramos.py
   - base_otros_conceptos             ← crea_tabla_otros_conceptos.py

3. CORRECCIONES (siempre antes de generar reportes para un período):
   - base_subramos_corregida_actual   ← crea_tabla_subramos_corregida.py {period}
   - base_ramos_corregida_actual      ← crea_tabla_ramos_corregida.py {period}
   - base_cias_corregida_actual       ← crea_tabla_cias_corregida.py {period}

4. SALIDA:
   - python ending_files/generate_all_reports.py {period}
   - python excel_generators/generate_all_excel.py {period}
```

**Reglas críticas**:

- **`base_balance_ultimos_periodos` debe contener al menos 2 años hacia atrás** desde el período objetivo. Las correcciones de las compañías especiales para T1 y T2 hacen JOIN contra `junio_prev_prev` y `diciembre_prev_prev` (período −2 años). Si esos períodos faltan, los JOINs internos fallan silenciosamente y las **compañías 0829, 0541, 0686 desaparecen** del reporte sin error.
- **Re-ejecutar `crea_tabla_otros_conceptos.py` con un período distinto al actual invalida 5 reportes** (1, 3, 10, 12, 13) hasta que se vuelva a correr para el período correcto. No hay aviso.
- **El web UI (`/api/create-subramos`)** ejecuta los 3 módulos de corrección en serie pero no es atómico: si falla el segundo, el primero ya está creado para el nuevo período. Como las tres tablas no tienen `periodo`, queda inconsistencia detectable sólo regenerando todo.

---

## Qué pasa si el pipeline no se ejecutó completamente

Casos comunes y sus síntomas:

### Caso 1: Falta `base_balance_ultimos_periodos` actualizada
- **Síntoma**: `crea_tabla_subramos.py` y `crea_tabla_ramos.py` tiran `ValueError("Required table 'base_balance_ultimos_periodos' does not exist")`.
- **Detección**: error explícito al correr el módulo.
- **Solución**: correr `crea_tabla_ultimos_periodos.py` antes.

### Caso 2: Falta `base_subramos` o `base_ramos`
- **Síntoma**: `crea_tabla_*_corregida.py` puede correr sin error pero el resultado queda **vacío o incompleto**, porque los JOINs internos no encuentran filas para el período objetivo.
- **Detección**: revisar `SELECT COUNT(*) FROM base_*_corregida_actual` — si es 0 o muy bajo, el período del input no estaba en `base_subramos`.

### Caso 3: `base_balance_ultimos_periodos` no cubre 2 años atrás
- **Síntoma**: Las correcciones para T1 y T2 generan tablas pero **sin las 3 compañías especiales** (0829, 0541, 0686). El resto del mercado aparece, las especiales no.
- **Detección**: `SELECT cod_cia FROM base_subramos_corregida_actual WHERE cod_cia IN ('0829','0541','0686')` debe devolver datos. Si está vacío, faltan los períodos históricos.
- **Solución**: re-correr `crea_tabla_ultimos_periodos.py {periodo}` con el período objetivo (no el actual) para asegurar 2 años hacia atrás.

### Caso 4: Olvido de regenerar las corregidas
- **Síntoma**: los reportes salen con datos del período viejo. **Sin error, sin aviso**. Los archivos Excel se ven correctos en estructura pero los números corresponden al trimestre anterior.
- **Detección manual**: comparar manualmente alguna cifra del Excel `apertura_por_subramo.xlsx` contra una compañía conocida — si no coincide con el trimestre objetivo, las corregidas están desactualizadas.
- **Detección automatizable**: ejecutar antes de los reportes:
  ```sql
  -- Verificar que el conteo de filas para el período actual cuadre
  SELECT COUNT(*) FROM base_subramos WHERE periodo = {period};
  SELECT COUNT(*) FROM base_subramos_corregida_actual;
  -- No tienen que ser iguales, pero el segundo debe ser >0 y razonable
  ```
- **Mejor estrategia**: **siempre regenerar las 3 tablas corregidas antes de correr reportes**, aunque parezca redundante.

### Caso 5: Olvido de regenerar `base_otros_conceptos`
- **Síntoma**: los reportes 1, 3, 10, 12, 13 salen con datos del período viejo. La columna `periodo` en `base_otros_conceptos` permite detectarlo (a diferencia de las corregidas).
- **Detección**:
  ```sql
  SELECT DISTINCT periodo FROM base_otros_conceptos;
  -- Debe coincidir con el período del reporte que estás generando
  ```

---

## Cómo saber si las tablas de análisis están desactualizadas

| Tabla | Cómo verificar el período actual |
|---|---|
| `base_balance_ultimos_periodos` | `SELECT MAX(periodo), MIN(periodo) FROM base_balance_ultimos_periodos` |
| `base_subramos` | `SELECT MAX(periodo) FROM base_subramos` (debe contener el período objetivo) |
| `base_ramos` | `SELECT MAX(periodo) FROM base_ramos` |
| `base_otros_conceptos` | `SELECT DISTINCT periodo FROM base_otros_conceptos` (devuelve un solo valor) |
| `base_subramos_corregida_actual` | **No se puede determinar** desde la tabla. Mirar logs o regenerar. |
| `base_ramos_corregida_actual` | **No se puede determinar** desde la tabla. Mirar logs o regenerar. |
| `base_cias_corregida_actual` | **No se puede determinar** desde la tabla. Mirar logs o regenerar. |

**Recomendación práctica**: antes de generar reportes para período X, ejecutar todo el pipeline desde el paso 2 (en `data_processing.py` esto es lo que hace el endpoint `/api/create-subramos` en modo no-testing — corre los 3 módulos de corrección en cadena).

---

## Resumen accionable

Si construís un agente sobre este sistema, las reglas mínimas que tiene que respetar:

1. **Antes de generar reportes para un período X**: ejecutar `crea_tabla_subramos_corregida.py X`, `crea_tabla_ramos_corregida.py X` y `crea_tabla_cias_corregida.py X` aunque parezca redundante. No hay forma de saber si ya están al día.
2. **Antes de eso**: chequear que `base_subramos` y `base_ramos` contengan datos para X y para X de 2 años atrás (`SELECT MAX(periodo), MIN(periodo)`). Si no, regenerar `base_balance_ultimos_periodos` con `--periodo X`.
3. **Si tocaste el período**: regenerar también `base_otros_conceptos` con `--periodo X`, sino los reportes patrimoniales quedan desfasados.
4. **No confíes en que un Excel "se generó OK"**: el pipeline tiende a generar archivos consistentes en formato pero con datos del período anterior cuando faltan pasos. La validación tiene que ser semántica (un número conocido), no estructural.
5. **Validá el período fuerte**: usar `validate_period` siempre, no sólo `len == 6`. Y rechazar períodos posteriores al máximo de `datos_balance` (no tiene sentido pedir reportes para datos que no existen).
