# Reportes del Mercado Asegurador

El objetivo principal es automatizar la creación de reportes del sector asegurador

Los pasos a seguir son
* Definir los reportes a incluir
* Generar las funciones de extracción de información
* Generar la lógica de transformación
* Chequear output de los reportes
* Dar formato en Excel

## Configuración del Entorno

Para ejecutar este proyecto, asegúrate de tener Python 3.11 instalado en tu sistema. Puedes descargarlo desde [python.org](https://www.python.org/downloads/).

Este proyecto utiliza [Conda](https://docs.conda.io/en/latest/) como sistema de gestión de paquetes y entornos. Asegúrate de tener Conda instalado en tu sistema para seguir estas instrucciones. Puedes instalar Conda a través de [Miniconda](https://docs.conda.io/en/latest/miniconda.html) o [Anaconda](https://www.anaconda.com/products/distribution).

Una vez instalado Python, sigue estos pasos para configurar tu entorno de desarrollo:

1. Clona este repositorio en tu máquina local:
https://github.com/diegonf84/reportes_revista

2. Navega al directorio del proyecto:

3. **Crear el Entorno Conda**: Utiliza el archivo `environment.yml` para crear un entorno Conda con todas las dependencias necesarias. Ejecuta:

`conda env create -f environment.yml`

Esto creará un nuevo entorno Conda según las especificaciones del archivo `environment.yml`.

4. **Activar el Entorno Conda**: Una vez creado el entorno, actívalo con:

`conda activate nombre_entorno`

Esto debería mostrar la versión de Python especificada en `environment.yml`. También puedes ejecutar `pip list` para ver las dependencias instaladas en el entorno.

### Trabajar con el Proyecto

Ahora que has configurado el entorno, puedes comenzar a trabajar en el proyecto. Recuerda activar el entorno Conda (`conda activate nombre_del_entorno`) cada vez que trabajes en el proyecto.

### Desactivar el Entorno

Cuando termines de trabajar en el proyecto, puedes desactivar el entorno Conda con:

`conda deactivate`


