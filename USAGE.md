# Guía de Uso

## Módulos Principales

### Carga de Datos
- `carga_base_principal.py`: Procesa archivos MDB y los carga en la base de datos.
- `check_cantidad_cias.py`: Verifica la cantidad de compañías en cada archivo.
- `check_ultimos_periodos.py`: Lista los períodos disponibles en la base.

### Procesamiento
- `crea_tabla_ultimos_periodos.py`: Genera tabla con datos de los últimos 2 años.
- `crea_tabla_subramos.py`: Crea tabla agregada por subramos del último año.

## Flujo de Trabajo

1. **Preparación**
   - Colocar archivos MDB en `/mdb_files_to_load`
   - Configurar `config_for_load.yml` con los datos del archivo

2. **Verificación**
   ```bash
   python modules/check_cantidad_cias.py
   python modules/check_ultimos_periodos.py
   ```

3. **Carga de Datos**
   ```bash
   python modules/carga_base_principal.py
   ```

4. **Procesamiento**
   ```bash
   python modules/crea_tabla_ultimos_periodos.py
   python modules/crea_tabla_subramos.py
   ```

## Archivos de Configuración

### config_for_load.yml
```yaml
directorio: "mdb_files_to_load"
nombre_archivo_zip: "2024-1.zip"
nombre_tabla: "Balance"
```

### .env
Requiere configuración de:
- DATABASE: ruta a la base de datos SQLite