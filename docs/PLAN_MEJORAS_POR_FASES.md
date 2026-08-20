# Plan de mejoras por fases

Checklist vivo para fortalecer la operación, los controles y la mantenibilidad de `reportes_revista`. Cada fase está pensada para trabajarse en una sesión independiente y debe actualizarse con evidencia al finalizarla.

## Estado general

| Fase | Tema | Complejidad estimada | Estado |
|---|---|---:|---|
| 1 | Generación confiable de reportes | Alta | Completada |
| 2 | Recarga segura de períodos | Alta | Completada |
| 3 | Pipeline completo por período | Alta | Pendiente |
| 4 | Mensajes, progreso y experiencia operativa | Media | Pendiente |
| 5 | Controles de datos maestros y conciliación | Alta | Pendiente |
| 6 | Tests automatizados | Alta | Pendiente |
| 7 | Base de datos, arquitectura y entorno | Alta | Pendiente |
| 8 | Seguridad y preparación para despliegue | Media | Pendiente |

**Estado del plan:** en ejecución  
**Fase activa:** Ninguna; próxima sugerida: Fase 3 — Pipeline completo por período
**Última actualización:** 2026-08-19

## Criterios acordados

- [x] No se conservará un historial de cada generación Excel de un mismo período.
- [x] Cada período tendrá una salida Excel oficial que podrá sobrescribirse.
- [x] Con la misma base y configuración, la generación debe producir el mismo contenido y estructura.
- [x] La trazabilidad se concentrará en la base utilizada, los controles ejecutados y el resultado final de la corrida.
- [x] Los errores funcionales informarán qué no se generó, sin exponer detalles técnicos al usuario.
- [x] Los botones individuales se podrán conservar para diagnóstico o uso avanzado.

## Cómo mantener este checklist

- Marcar una única fase como **En curso**.
- Trabajar una fase por sesión, salvo que sea demasiado grande y deba dividirse explícitamente.
- Cambiar una tarea a `[x]` sólo después de verificarla.
- Registrar debajo de cada fase la fecha, evidencia, pruebas y archivos afectados.
- No ampliar el alcance de una fase sin anotarlo primero en este documento.
- Si un hallazgo deja de aplicar, marcarlo como descartado y explicar el motivo; no eliminarlo sin registro.

---

## Fase 1 — Generación confiable de reportes

**Objetivo:** asegurar que el sistema nunca informe éxito cuando faltan CSV o Excel y que la carpeta del período represente correctamente la última generación oficial.

### Checklist

- [x] Propagar los errores reales de cada consulta CSV hasta el orquestador.
- [x] Evitar que un error de consulta termine con código de salida exitoso.
- [x] Informar por separado éxito total, generación parcial y fallo total.
- [x] Verificar la cantidad esperada de CSV y Excel antes de confirmar éxito.
- [x] Verificar que cada archivo esperado pertenezca a la corrida actual y no sea un remanente anterior.
- [x] Sobrescribir la salida oficial del período sin acumular versiones históricas.
- [x] Evitar que una corrida fallida reemplace una salida oficial completa por archivos parciales.
- [x] Validar que los archivos no estén vacíos y contengan las columnas mínimas esperadas.
- [x] Validar el período de `base_otros_conceptos` antes de generar.
- [x] Validar el período de las tres tablas `*_corregida_actual`.
- [x] Validar la cobertura histórica requerida por las correcciones especiales.
- [x] Confirmar determinismo funcional: misma base y configuración producen el mismo contenido y estructura.
- [x] Mantener el mensaje funcional con cantidad y nombres de los Excel no generados.

### Criterio de cierre

Una generación sólo se considera exitosa si están presentes y validados todos los archivos oficiales esperados. Una falla no deja una carpeta que pueda confundirse con una generación completa.

### Evidencia de cierre

- Fecha: 2026-08-19.
- Pruebas ejecutadas:
  - Suite automatizada: 9 pruebas aprobadas con `python -m unittest discover -s tests -v`.
  - Consulta CSV inválida: código de salida `1` y ningún archivo parcial publicado.
  - Preflight real del período `202602`: aprobado en modo de solo lectura.
  - Dos generaciones completas e independientes en staging: 13 CSV y 14 Excel validados en cada corrida.
  - Determinismo: los 13 CSV fueron idénticos byte a byte; los 14 Excel tuvieron contenido y estructura idénticos al excluir `docProps/core.xml`, que sólo contiene metadatos temporales del archivo.
  - Publicación segura: pruebas de reemplazo completo y restauración de ambas carpetas ante fallo.
- Archivos afectados:
  - `modules/report_generation.py` — contratos, preflight, validación y publicación segura.
  - `utils/report_generator.py` y `ending_files/generate_all_reports.py` — propagación de errores y resultado estructurado de CSV.
  - `excel_generators/` — soporte de staging y validación del conjunto Excel.
  - `app/routes/data_processing.py` — orquestación completa y mensajes funcionales.
  - `tests/test_report_generation.py` — cobertura automatizada de los controles incorporados.
- Observaciones: la salida oficial no se modificó durante las pruebas reales; las corridas se realizaron en directorios temporales. No se crean versiones históricas por período.

---

## Fase 2 — Recarga segura de períodos

**Objetivo:** impedir la pérdida de un período existente cuando se reemplaza su ZIP o falla la nueva carga.

### Checklist

- [x] Mantener el ZIP nuevo como temporal hasta que el usuario confirme la recarga.
- [x] Conservar el ZIP vigente si la comparación o validación del nuevo archivo falla.
- [x] Eliminar o aislar el MDB extraído anterior antes de validar el nuevo ZIP.
- [x] Validar que el ZIP contenga el MDB esperado y no archivos inesperados.
- [x] Validar tamaño, estructura y extracción segura del ZIP.
- [x] Comprobar el resultado de `mdb-export` antes de leer el CSV producido.
- [x] Evitar el esquema actual de borrar primero y cargar después sin recuperación.
- [x] Definir una estrategia de rollback o restauración si la nueva carga falla.
- [x] Realizar un backup consistente antes de una recarga destructiva.
- [x] Verificar después de la carga cantidad de filas, compañías y período insertado.
- [x] Informar claramente si la recarga fue confirmada, cancelada o revertida.
- [x] Regenerar o invalidar explícitamente las tablas derivadas después de recargar un período.

### Criterio de cierre

Una recarga fallida deja intactos el ZIP vigente y los datos originales del período. El reemplazo sólo se publica después de superar controles de archivo y conciliación.

### Evidencia de cierre

- Fecha: 2026-08-19.
- Pruebas ejecutadas:
  - Suite completa: 19 pruebas aprobadas con `python -m unittest discover -s tests -v`.
  - Casos específicos de recarga: ZIP inválido, fallo de `mdb-export`, cancelación, confirmación y fallo de commit con restauración de base, ZIP y MDB.
  - Prueba real aislada con `2026-2.zip`: 150.200 filas, 185 compañías y período único `202602` cargados y conciliados en una base temporal.
  - En la prueba real se conservó otro período, se reemplazó el ZIP temporal por el oficial, se eliminó el MDB anterior y se invalidaron las tablas derivadas afectadas.
- Archivos afectados:
  - `modules/period_reload.py` — staging, validación ZIP/MDB, transacción, conciliación, invalidación y rollback.
  - `app/routes/data_processing.py` — preparación, confirmación y cancelación de recargas.
  - `app/templates/data_processing/verification.html` — token de recarga y cancelación real del staging.
  - `tests/test_period_reload.py` — pruebas aisladas y de endpoints para la Fase 2.
- Observaciones: la base y los archivos operativos no se modificaron durante las pruebas. El respaldo de filas vive dentro de la misma transacción SQLite y los archivos vigentes se conservan hasta confirmar el commit.

---

## Fase 3 — Pipeline completo por período

**Objetivo:** reducir el trabajo manual y ejecutar en orden todas las etapas necesarias para dejar un período listo para reportes.

### Checklist

- [ ] Definir formalmente las etapas y dependencias del pipeline completo.
- [ ] Incorporar una acción normal de “Procesar período completo”.
- [ ] Ejecutar en orden períodos recientes, bases, conceptos, tablas corregidas, CSV y Excel.
- [ ] Detener el pipeline ante el primer fallo que invalide pasos posteriores.
- [ ] No marcar etapas posteriores como completas si una dependencia falló.
- [ ] Mantener las acciones individuales como herramientas avanzadas.
- [ ] Seleccionar un único período de trabajo y reutilizarlo durante todo el flujo.
- [ ] Evitar defaults basados en la fecha actual cuando existe un período seleccionado.
- [ ] Mostrar qué etapas ya están actualizadas y cuáles deben regenerarse.
- [ ] Evitar dos pipelines simultáneos sobre la misma base o período.
- [ ] Definir qué etapas deben repetirse después de cambiar compañías, conceptos o parámetros.

### Criterio de cierre

Desde la interfaz se puede seleccionar un período y completar todo el flujo requerido sin ejecutar manualmente cada tabla, conservando las herramientas individuales para diagnóstico.

### Evidencia de cierre

- Fecha:
- Pruebas ejecutadas:
- Archivos afectados:
- Observaciones:

---

## Fase 4 — Mensajes, progreso y experiencia operativa

**Objetivo:** hacer visible qué está ocurriendo, qué terminó y qué necesita intervención, sin mensajes contradictorios o efímeros.

### Checklist

- [ ] Definir una política única para mensajes informativos, exitosos, advertencias y errores.
- [ ] Mantener visibles los resultados importantes hasta que el usuario los cierre.
- [ ] Reservar el auto-cierre para avisos menores.
- [ ] Eliminar diferencias arbitrarias de 5, 8 y 10 segundos entre pantallas.
- [ ] Mostrar progreso real por etapa en lugar de una barra estática al 100 %.
- [ ] Mostrar el paso actual, pasos completados y paso fallido.
- [ ] Mantener un resumen visible aunque se cierre o recargue la pantalla.
- [ ] Deshabilitar acciones incompatibles mientras hay un proceso activo.
- [ ] Evitar mensajes dobles o contradictorios ante una misma respuesta.
- [ ] Separar el mensaje funcional para el usuario de los detalles técnicos de diagnóstico.
- [ ] Mostrar un inventario final de archivos oficiales generados.
- [ ] Facilitar descarga o apertura de la ubicación de salida.
- [ ] Incorporar al dashboard el estado real del último período procesado.

### Criterio de cierre

El usuario puede saber en todo momento qué operación está activa, cuál fue su resultado y qué debe hacer después, sin depender de mensajes temporales ni de revisar carpetas manualmente.

### Evidencia de cierre

- Fecha:
- Pruebas ejecutadas:
- Archivos afectados:
- Observaciones:

---

## Fase 5 — Controles de datos maestros y conciliación

**Objetivo:** impedir que compañías, conceptos o mapeos incompletos produzcan reportes parciales o valores silenciosamente incorrectos.

### Checklist

- [ ] Verificar antes del pipeline que todas las compañías del período existan en `datos_companias`.
- [ ] Mostrar clasificaciones obligatorias faltantes como hallazgo de calidad.
- [ ] Distinguir compañías activas, históricas e inactivas.
- [ ] Evitar eliminar una compañía utilizada por datos históricos sin un control explícito.
- [ ] Evaluar el impacto antes de permitir el cambio de `cod_cia`.
- [ ] Definir vigencia o historial para cambios de nombre y clasificación cuando corresponda.
- [ ] Validar que cada concepto tenga parámetros contables utilizables.
- [ ] Impedir duplicados lógicos de compañías, conceptos y parámetros a nivel de base.
- [ ] Detectar códigos contables duplicados con signos incompatibles.
- [ ] Proteger las divisiones por cero pendientes en las definiciones de reportes.
- [ ] Conciliar cantidades de compañías y filas contra el período anterior.
- [ ] Definir controles de totales para los reportes críticos.
- [ ] Mostrar variaciones extraordinarias como advertencias, no como causas automáticas.
- [ ] Revisar los registros maestros con clasificaciones SSN vacías y determinar si siguen activos.

### Criterio de cierre

Las inconsistencias de catálogos y mapeos se detectan antes de generar reportes. Los cambios sobre datos maestros informan su impacto y no rompen silenciosamente períodos históricos.

### Evidencia de cierre

- Fecha:
- Pruebas ejecutadas:
- Archivos afectados:
- Observaciones:

---

## Fase 6 — Tests automatizados

**Objetivo:** proteger los contratos de cálculo y los flujos críticos para reducir la dependencia de pruebas manuales.

### Checklist

- [ ] Preparar una base pequeña y reproducible para pruebas.
- [ ] Cubrir validación y conversión de períodos.
- [ ] Cubrir reemplazo de ZIP y eliminación del MDB anterior.
- [ ] Cubrir recarga exitosa, cancelada y fallida.
- [ ] Cubrir rollback o recuperación después de una carga fallida.
- [ ] Cubrir detección de compañías sin parametrizar.
- [ ] Cubrir conceptos sin mapeo y parámetros duplicados.
- [ ] Cubrir generación CSV exitosa, parcial y fallida.
- [ ] Cubrir generación Excel exitosa, parcial y fallida.
- [ ] Verificar que no se reutilicen archivos antiguos como resultado actual.
- [ ] Verificar determinismo funcional de reportes con una base estable.
- [ ] Cubrir endpoints Flask principales con una base de prueba aislada.
- [ ] Incorporar una prueba end-to-end del pipeline completo.
- [ ] Definir un comando único para ejecutar toda la suite.

### Criterio de cierre

Los fallos ya observados y los caminos destructivos tienen pruebas reproducibles. La suite puede ejecutarse sin utilizar ni modificar la base operativa.

### Evidencia de cierre

- Fecha:
- Pruebas ejecutadas:
- Archivos afectados:
- Observaciones:

---

## Fase 7 — Base de datos, arquitectura y entorno

**Objetivo:** mejorar rendimiento, integridad y capacidad de mantenimiento sin alterar los contratos de cálculo.

### Checklist

- [ ] Medir consultas críticas antes de decidir índices.
- [ ] Incorporar índices justificados para períodos, compañías, cuentas y joins frecuentes.
- [ ] Definir claves primarias y restricciones de unicidad donde el modelo lo permita.
- [ ] Revisar el uso efectivo de claves foráneas y sus reglas de actualización/eliminación.
- [ ] Separar rutas web, servicios de aplicación y operaciones de datos.
- [ ] Reducir responsabilidades de `app/routes/data_processing.py`.
- [ ] Extraer el JavaScript duplicado de mensajes, solicitudes y progreso.
- [ ] Reemplazar la captura global de logs por resultados aislados por ejecución.
- [ ] Eliminar o archivar código duplicado como `data_processing_backup.py`.
- [ ] Normalizar imports para que `create_app()` pueda importarse como paquete.
- [ ] Usar el mismo intérprete Python para la aplicación y sus subprocess.
- [ ] Eliminar paths personales hardcodeados en scripts iniciales.
- [ ] Fijar y documentar dependencias reproducibles.
- [ ] Separar claramente entorno operativo y entorno de desarrollo.
- [ ] Actualizar README, uso y limitaciones para reflejar el comportamiento real.

### Criterio de cierre

El proyecto puede instalarse, probarse y ejecutarse de manera reproducible. Los cambios en UI, pipeline o datos no requieren modificar un único módulo central de gran tamaño.

### Evidencia de cierre

- Fecha:
- Pruebas ejecutadas:
- Archivos afectados:
- Observaciones:

---

## Fase 8 — Seguridad y preparación para despliegue

**Objetivo:** conservar el uso local actual y evitar riesgos si la aplicación se comparte o despliega en otro entorno.

### Checklist

- [ ] Confirmar formalmente si la aplicación seguirá siendo exclusivamente local.
- [ ] Parametrizar y validar el modo debug según el entorno.
- [ ] Eliminar el fallback inseguro de `SECRET_KEY` para entornos no locales.
- [ ] Parametrizar todas las consultas del Inspector.
- [ ] Aplicar protección CSRF consistente a operaciones que modifican datos.
- [ ] Definir autenticación antes de permitir acceso desde otra máquina.
- [ ] Establecer límites de tamaño para uploads.
- [ ] Validar extracción segura de ZIP y prevenir archivos fuera del directorio esperado.
- [ ] Evitar mostrar excepciones técnicas o rutas sensibles en respuestas al usuario.
- [ ] Definir un servidor WSGI y configuración de despliegue sólo si el uso deja de ser local.

### Criterio de cierre

El modo local está explícitamente delimitado y cualquier despliegue compartido cuenta con controles mínimos de acceso, validación y protección de datos.

### Evidencia de cierre

- Fecha:
- Pruebas ejecutadas:
- Archivos afectados:
- Observaciones:

---

## Registro de decisiones y cambios

| Fecha | Fase | Decisión o cambio | Motivo |
|---|---|---|---|
| 2026-08-19 | General | Se crea el checklist por fases. | Trabajar mejoras en sesiones separadas sin perder contexto. |
| 2026-08-19 | 1 | No se versionará cada generación Excel. | La salida oficial debe ser determinística y sobrescribible para una base estable. |
