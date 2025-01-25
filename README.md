# Reportes del Mercado Asegurador

Sistema automatizado para la generación de reportes del sector asegurador.

## Instalación

Para ejecutar este proyecto, asegúrate de tener Python 3.11 instalado en tu sistema. Puedes descargarlo desde [python.org](https://www.python.org/downloads/).

Este proyecto utiliza [Conda](https://docs.conda.io/en/latest/) como sistema de gestión de paquetes y entornos. Asegúrate de tener Conda instalado en tu sistema para seguir estas instrucciones. Puedes instalar Conda a través de [Miniconda](https://docs.conda.io/en/latest/miniconda.html) o [Anaconda](https://www.anaconda.com/products/distribution).

Una vez instalado Python, sigue estos pasos para configurar tu entorno de desarrollo:

1. Clonar repositorio:
```bash
git clone https://github.com/diegonf84/reportes_revista
```

2. Crear y activar entorno Conda:
```bash
conda env create -f environment.yml
conda activate nombre_entorno
```

3. Instalar módulos locales:
```bash
pip install -e .
```

## Estructura del Proyecto
```
├── initial_scripts/               # Scripts iniciales
│   ├── create_conceptos_reportes.py
│   ├── create_parametros_reportes.py
│   └── create_principal_table.py
│
├── mdb_files_to_load/            # Archivos a procesar
│
├── modules/                       # Módulos principales
│   ├── __init__.py
│   ├── carga_base_principal.py
│   ├── check_cantidad_cias.py
│   ├── check_ultimos_periodos.py
│   ├── crea_tabla_subramos.py
│   └── crea_tabla_ultimos_periodos.py
│
├── utils/                        # Utilidades
│   ├── __init__.py
│   ├── db_functions.py
│   └── other_functions.py
│
├── .env                         # Variables de entorno
├── .gitignore                   # Archivos ignorados por git
├── config_for_load.yml          # Configuración de carga
├── environment.yml              # Entorno virtual
└── setup.py                     # Configuración del proyecto
```

Para más detalles sobre el uso y funcionamiento, consulte la [Guía de Uso](USAGE.md).

## TODO
* Incluir los nombres de ramos, subramos y compañias
* Agregar el resto de conceptos de reportes (primas cedidas, y los que falten)
* Generar una tabla con los conceptos que van sin subramos alguno (resultados, ganancias, perdidas, etc)