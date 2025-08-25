<!-- Encabezado -->

[![Colaboradores][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Estrellas][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]

<!-- Título -->
<br />
<div align="center">

<h1 align="center">Auto-Az-Spark</h1>
  <p align="center">
    Automatización para el despliegue de un cluster de Apache Spark con Azure, Cloudflare y Azure DevOps
    <br />
    <a href="https://github.com/daniel-lara-ec/Auto-Az-Spark/issues">Reportar un Problema</a>
    <br />
    <br />
  </p>
</div>

<!-- Cuerpo -->

## Sobre el Proyecto

Este proyecto orquesta la creación de un cluster de Apache Spark desde la generación de máquinas virtuales, instalación de dependencias y configuración de repositorios privados para un trabajo rápido y eficiente sobre Azure.

### Construido con

[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#)
[![Microsoft Azure](https://custom-icon-badges.demolab.com/badge/Microsoft%20Azure-0089D6?logo=msazure&logoColor=white)](#)
[![Cloudflare](https://img.shields.io/badge/Cloudflare-F38020?logo=Cloudflare&logoColor=white)](#)
[![Bash](https://img.shields.io/badge/Bash-4EAA25?logo=gnubash&logoColor=fff)](#)
[![Apache Spark](https://img.shields.io/badge/Apache%20Spark-E25A1C?logo=apachespark&logoColor=fff)](#)

## Descripción

Este proyecto en Python proporciona una herramienta de línea de comandos para gestionar un clúster de forma automatizada. Permite crear y eliminar recursos, instalar dependencias, iniciar nodos, configurar DNS y entornos de DevOps, así como orquestar acciones sobre el clúster de manera centralizada.

El script está diseñado para simplificar tareas repetitivas de administración y despliegue, facilitando la gestión integral de la infraestructura.

### Uso del script

Para su uso es necesario definir las variables de entorno en el archivo `.env`. A continuación un ejemplo:

```
ID_SUSRCIPCION="idsuscripcion"
NOMBRE_CLUSTER="cluster"
NUMERO_NODOS="1"
TAMANIO_INSTANCIA_DRIVER="Standard_B2"
GRUPO_RECURSOS="GrupoRecursos"
NOMBRE_RED_VIRTUAL="Vnet"
NOMBRE_SUBRED="Subnet"
NOMBRE_CLAVE_SSH="clavessh"
REGION="eastus"
USERNAMEAZ="usuario"
GRUPO_RECURSOS_VNET="GrupoRecursos"
TAMANIO_INSTANCIA_WORKER="Standard_D2"
IP_PUBLICA="1.1.1.1"
RUTA_SCRIPTS_DEPENDENCIAS="C:/Usuario/user/scripts"
CLOUDFLARE_TOKEN="token-secreto"
ZONA_DNS="dominio.com"
ZONA_DNS_ID="id-zona"
PATRON_DNS="cluster.spark"
CORREO_CLOUDFLARE="correo@mail.com"
CLAVE_PRIVADA_DEVOPS="C:/Usuario/user/id_rsa"
```

El script puede ejecutarse desde la línea de comandos con diferentes argumentos para gestionar el clúster.

- Crear un recurso

```
python main.py --crear
```

Documentación sobre los prerrequisitos necesarios la puedes encontrar en: [Requisitos](docs/Requisitos.md)

#### Nota

Esta automatización utiliza un mirror propio para la instalación de Hadoop y Spark. Esto se hizo con la intención de garantizar la estabilidad de los enlaces en el tiempo. Para el uso se puede cambiar esto pues los archivos no tienen ninguna modificación en particular.

### Contenido del Repositorio

En construcción...

## Créditos

**Daniel Matías Lara** (dmlaran@alephsub0.org)

[![LinkedIn][linkedin-shield]][linkedin-url-dmln]

## Licencia

Distribuido bajo la licencia MIT.

[![MIT License][license-shield]][license-url]

<!-- MARKDOWN LINKS & IMAGES -->

[contributors-shield]: https://img.shields.io/github/contributors/daniel-lara-ec/Auto-Az-Spark.svg?style=for-the-badge
[contributors-url]: https://github.com/daniel-lara-ec/Auto-Az-Spark/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/daniel-lara-ec/Auto-Az-Spark.svg?style=for-the-badge
[forks-url]: https://github.com/daniel-lara-ec/Auto-Az-Spark/forks
[stars-shield]: https://img.shields.io/github/stars/daniel-lara-ec/Auto-Az-Spark?style=for-the-badge
[stars-url]: https://github.com/daniel-lara-ec/Auto-Az-Spark/stargazers
[issues-shield]: https://img.shields.io/github/issues/daniel-lara-ec/Auto-Az-Spark.svg?style=for-the-badge
[issues-url]: https://github.com/daniel-lara-ec/Auto-Az-Spark/issues
[license-shield]: https://img.shields.io/github/license/daniel-lara-ec/Auto-Az-Spark.svg?style=for-the-badge
[license-url]: https://es.wikipedia.org/wiki/Licencia_MIT
[linkedin-shield]: https://img.shields.io/badge/linkedin-%230077B5.svg?style=for-the-badge&logo=linkedin&logoColor=white
[linkedin-url-dmln]: https://www.linkedin.com/in/mat-daniel-lara/
