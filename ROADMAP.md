# Roadmap: Docker, Dev Environment y Backups

## Objetivo

Ordenar el proyecto en tres pasos: containerizarlo para poder desplegarlo en cualquier lado, tener un ambiente de desarrollo aislado para probar código sin tocar producción, y agregar tests de forma incremental. Los backups serán manuales — un recordatorio en la UI y un comando para subir la base cuando se necesite.

---

## Paso 1 — Dockerizar la aplicación

**Prerequisitos de código:**
- Generar `requirements.txt` con `pip freeze > requirements.txt` dentro del entorno conda `revista_tr_cuadros`
- Crear `wsgi.py` en la raíz (entry point para gunicorn, reemplaza el dev server de Flask)
- Cambiar `DATABASE` en `.env` a path absoluto (el path relativo rompe con gunicorn)

**Archivos a crear:**
- `Dockerfile` — imagen `python:3.11-slim`, instala `mdbtools`, instala `requirements.txt`, usa gunicorn como CMD con `--workers 2 --timeout 600`
- `docker-compose.yml` — un servicio `app` con 4 volúmenes montados desde el host: base de datos, `mdb_files_to_load/`, `ending_files/`, `excel_final_files/`
- `.env.docker` (no commiteado) — igual al `.env` actual pero con `DATABASE=/data/revista_tr_database.db` y `FLASK_DEBUG=False`
- `wsgi.py`
- `requirements.txt`

**Verificación:** `docker-compose up` → dashboard carga → generación de reportes funciona desde el contenedor.

---

## Paso 2 — Ambiente de desarrollo aislado

Tener una copia de la DB de producción para probar código nuevo sin riesgo.

**Cómo funciona:**
- Copiar `revista_tr_database.db` → `revista_tr_database_dev.db` (mismo directorio, fuera del repo)
- Crear `.env.dev` apuntando a esa copia
- Para correr en modo dev: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`
- Si algo sale mal en la dev: volver a copiar desde producción para resetear

**Archivos a crear:**
- `.env.dev` (no commiteado)
- `docker-compose.dev.yml` (commiteado) — solo contiene el override del volumen de DB y `FLASK_DEBUG=True`

**Flujo de trabajo:** rama nueva en git + base dev → probar → si hay que resetear la DB dev, `cp revista_tr_database.db revista_tr_database_dev.db`.

---

## Paso 3 — Backup manual con aviso

No hace falta automatizar. El flujo es: se genera un período nuevo → aparece un recordatorio en la UI → se ejecuta un comando para subir la DB a S3.

**Archivos a crear/modificar:**
- `utils/backup_db.py` — lee `DATABASE` y credenciales AWS del `.env`, usa `sqlite3 connection.backup()` (seguro con Flask corriendo), sube a S3 con nombre que incluye fecha y período (ej: `backups/revista_tr_database_202504_20260602.db`). Uso: `python utils/backup_db.py 202504`
- `app/templates/data_processing/report_generation.html` — agregar recordatorio de backup en el mensaje de éxito post-generación

---

## Paso 4 — Tests (después de tener Docker y dev environment)

Agregar tests de forma incremental una vez que el ambiente de dev esté estable.

- `pytest.ini` en la raíz
- `tests/unit/` — funciones puras sin DB: `validate_period`, `calculate_periods`, `_period_to_title`. Corren en segundos.
- `tests/integration/` — operaciones con DB usando la `_dev.db` como base. Se construyen una vez consolidado el ambiente dev.

---

## Secuencia de implementación

1. Generar `requirements.txt` + crear `wsgi.py`
2. Escribir `Dockerfile` y `docker-compose.yml`
3. Crear `.env.docker`, verificar que `docker-compose up` funciona end-to-end
4. Copiar DB de producción a `_dev.db`, crear `.env.dev` y `docker-compose.dev.yml`
5. Crear `utils/backup_db.py` + recordatorio en la UI
6. Comenzar tests unitarios (`tests/unit/`)
