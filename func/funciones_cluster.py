import logging
import os
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
import pandas as pd
from func.funciones_vm import (
    crear_vm,
    crear_grupo_seguridad,
    eliminar_grupo_seguridad,
    eliminar_vm,
    instalar_dependencias_vm,
    iniciar_master,
    iniciar_worker,
    obtener_ip_privada_vm,
    copiar_clave_privada_devops,
)
from func.funciones_dns import create_or_update_dns_record
from pathlib import Path

# Obtiene el logger para este módulo
logger = logging.getLogger(__name__)


def crear_cluster(
    cliente_azure,
    nombre_base,
    cantidad_nodos,
    tamanio_instancia_driver,
    grupo_recursos,
    nombre_red_virtual,
    nombre_subred,
    nombre_clave_ssh,
    region,
    username_driver,
    ip_publica,
    reglas_cortafuegos=None,
    grupo_seguridad_driver=None,
    grupo_seguridad_worker=None,
    grupo_recursos_vnet=None,
    sistema_operativo=None,
    username_worker=None,
    tamanio_instancia_worker=None,
):
    """
    Crea un cluster en Azure.
    """

    if grupo_recursos_vnet is None:
        grupo_recursos_vnet = grupo_recursos

    if username_worker is None:
        username_worker = username_driver

    if tamanio_instancia_worker is None:
        tamanio_instancia_worker = tamanio_instancia_driver

    if sistema_operativo is None:
        sistema_operativo = {
            "publisher": "canonical",
            "offer": "0001-com-ubuntu-server-jammy",
            "sku": "22_04-lts-gen2",
            "version": "latest",
        }

    if grupo_seguridad_driver is None and grupo_seguridad_worker is None:

        if reglas_cortafuegos is None:

            reglas_cortafuegos_ssh = [
                {
                    "protocolo": "Tcp",
                    "puerto_origen": "*",
                    "puerto_destino": "22",
                    "direccion_origen": str(ip_publica),
                    "direccion_destino": "*",
                    "acceso": "Allow",
                    "direccion": "Inbound",
                    "prioridad": 200,
                    "nombre": "PermitirSSH",
                }
            ]

            reglas_cortafuegos_http = [
                {
                    "protocolo": "Tcp",
                    "puerto_origen": "*",
                    "puerto_destino": "8080",
                    "direccion_origen": str(ip_publica),
                    "direccion_destino": "*",
                    "acceso": "Allow",
                    "direccion": "Inbound",
                    "prioridad": 210,
                    "nombre": "PermitirSparkClusterUI",
                },
                {
                    "protocolo": "Tcp",
                    "puerto_origen": "*",
                    "puerto_destino": "4040",
                    "direccion_origen": str(ip_publica),
                    "direccion_destino": "*",
                    "acceso": "Allow",
                    "direccion": "Inbound",
                    "prioridad": 230,
                    "nombre": "PermitirSparkAppUI",
                },
            ]

            reglas_cortafuegos_http_worker = [
                {
                    "protocolo": "Tcp",
                    "puerto_origen": "*",
                    "puerto_destino": "8081",
                    "direccion_origen": str(ip_publica),
                    "direccion_destino": "*",
                    "acceso": "Allow",
                    "direccion": "Inbound",
                    "prioridad": 220,
                    "nombre": "PermitirSparkClusterUIWorker",
                }
            ]
        else:
            reglas_cortafuegos_ssh = []
            reglas_cortafuegos_http = []
            reglas_cortafuegos_http_worker = []

        # crear grupos de seguridad
        crear_grupo_seguridad(
            cliente_azure=cliente_azure,
            nombre_nsg=nombre_base + "-nsg-driver",
            region=region,
            grupo_recursos=grupo_recursos,
            reglas_cortafuegos=reglas_cortafuegos_ssh + reglas_cortafuegos_http,
        )

        crear_grupo_seguridad(
            cliente_azure=cliente_azure,
            nombre_nsg=nombre_base + "-nsg-worker",
            region=region,
            grupo_recursos=grupo_recursos,
            reglas_cortafuegos=reglas_cortafuegos_ssh + reglas_cortafuegos_http_worker,
        )

        grupo_seguridad_driver = nombre_base + "-nsg-driver"
        grupo_seguridad_worker = nombre_base + "-nsg-worker"

    elif grupo_seguridad_driver is None or grupo_seguridad_worker is None:
        raise ValueError(
            "Es necesario especificar grupos de seguridad para el driver y el worker."
        )

    # Lógica para crear un clúster de Spark

    nombre_master, ip_master = crear_master(
        cliente_azure=cliente_azure,
        nombre_base=nombre_base,
        tamanio_instancia=tamanio_instancia_driver,
        grupo_recursos=grupo_recursos,
        nombre_red_virtual=nombre_red_virtual,
        nombre_subred=nombre_subred,
        nombre_clave_ssh=nombre_clave_ssh,
        sistema_operativo=sistema_operativo,
        region=region,
        username=username_driver,
        grupo_seguridad=grupo_seguridad_driver,
        grupo_recursos_vnet=grupo_recursos_vnet,
    )

    listado_workers = crear_worker(
        cliente_azure=cliente_azure,
        nombre_base=nombre_base,
        cantidad_nodos=cantidad_nodos,
        tamanio_instancia=tamanio_instancia_worker,
        grupo_recursos=grupo_recursos,
        nombre_red_virtual=nombre_red_virtual,
        nombre_subred=nombre_subred,
        nombre_clave_ssh=nombre_clave_ssh,
        sistema_operativo=sistema_operativo,
        region=region,
        username=username_worker,
        grupo_seguridad=grupo_seguridad_worker,
        grupo_recursos_vnet=grupo_recursos_vnet,
    )

    # guardamos los datos en un archivo csv

    if listado_workers is None:
        listado_workers = []

    df = pd.DataFrame(
        {
            "Nombre": [nombre_master]
            + [worker["nombre"] for worker in listado_workers],
            "IP": [ip_master] + [worker["ip"] for worker in listado_workers],
            "Usuario": [username_driver]
            + [worker["usuario"] for worker in listado_workers],
            "TipoNodo": ["Master"] + ["Worker"] * len(listado_workers),
        }
    )

    df.to_csv("datos_cluster.csv", index=False)

    df_grupos_seguridad = pd.DataFrame(
        {
            "Nombre": [grupo_seguridad_driver, grupo_seguridad_worker],
        }
    )

    df_grupos_seguridad.to_csv("datos_grupos_seguridad.csv", index=False)


def crear_master(
    cliente_azure,
    nombre_base,
    tamanio_instancia,
    grupo_recursos,
    nombre_red_virtual,
    nombre_subred,
    nombre_clave_ssh,
    sistema_operativo,
    region,
    username,
    grupo_seguridad,
    grupo_recursos_vnet,
):
    """
    Crea un nodo maestro para el clúster de Spark.
    """

    nombre_master = nombre_base + "-master"

    (resultado, nombre, ip) = crear_vm(
        cliente_azure=cliente_azure,
        tamanio_instancia=tamanio_instancia,
        nombre_base=nombre_master,
        grupo_recursos=grupo_recursos,
        nombre_red_virtual=nombre_red_virtual,
        nombre_subred=nombre_subred,
        nombre_clave_ssh=nombre_clave_ssh,
        sistema_operativo=sistema_operativo,
        region=region,
        username=username,
        grupo_recursos_vnet=grupo_recursos_vnet,
        grupo_seguridad=grupo_seguridad,
    )

    if resultado:
        logger.info("Máquina virtual creada: %s (%s)", nombre, ip)
        return nombre, ip

    logger.error("Error al crear la máquina virtual: %s", nombre)
    return None, None


def crear_worker(
    cliente_azure,
    nombre_base,
    cantidad_nodos: int,
    tamanio_instancia,
    grupo_recursos,
    nombre_red_virtual,
    nombre_subred,
    nombre_clave_ssh,
    sistema_operativo,
    region,
    username,
    grupo_recursos_vnet,
    grupo_seguridad,
):
    """
    Crea un grupo de nodos trabajadores para el clúster de Spark.
    """

    nombre_worker = nombre_base + "-worker"

    listado_resultados = []

    listado_nombres_workers = [nombre_worker + f"-{i+1}" for i in range(cantidad_nodos)]

    for nombre_worker in listado_nombres_workers:
        (resultado, nombre, ip) = crear_vm(
            cliente_azure=cliente_azure,
            tamanio_instancia=tamanio_instancia,
            nombre_base=nombre_worker,
            grupo_recursos=grupo_recursos,
            nombre_red_virtual=nombre_red_virtual,
            nombre_subred=nombre_subred,
            nombre_clave_ssh=nombre_clave_ssh,
            sistema_operativo=sistema_operativo,
            region=region,
            username=username,
            grupo_recursos_vnet=grupo_recursos_vnet,
            grupo_seguridad=grupo_seguridad,
        )

        listado_resultados.append(
            {"resultado": resultado, "nombre": nombre, "ip": ip, "usuario": username}
        )

    if all(item["resultado"] for item in listado_resultados):
        logger.info(
            "Máquina virtual creada: %s (%s)",
            listado_resultados[0]["nombre"],
            listado_resultados[0]["ip"],
        )
        return listado_resultados

    logger.error("Error al crear los nodos: %s", listado_nombres_workers)
    return None


def eliminar_cluster(cliente_azure, grupo_recursos):
    """
    Elimina los recursos del clúster de Spark.
    """
    try:
        df_recursos_cluster = pd.read_csv("datos_cluster.csv")

        for _, row in df_recursos_cluster.iterrows():
            logger.info("Eliminando recurso: %s", row["Nombre"])
            eliminar_vm(cliente_azure, grupo_recursos, row["Nombre"])

    except Exception as e:
        logger.error("Error al eliminar el clúster: %s", e)

    try:

        df_grupos_seguridad = pd.read_csv("datos_grupos_seguridad.csv")

        for _, row in df_grupos_seguridad.iterrows():
            logger.info("Eliminando grupo de seguridad: %s", row["Nombre"])
            eliminar_grupo_seguridad(cliente_azure, grupo_recursos, row["Nombre"])
    except Exception as e:
        logger.error("Error al eliminar los grupos de seguridad: %s", e)

    # Eliminamos los archivos .csv verificando si existen
    if os.path.exists("datos_cluster.csv"):
        os.remove("datos_cluster.csv")
    if os.path.exists("datos_grupos_seguridad.csv"):
        os.remove("datos_grupos_seguridad.csv")


def instalar_dependencias_cluster(
    cliente_azure, ruta_scripts, clave_publica, zona_dns, patron_dns, grupo_recursos
):
    """
    Instala las dependencias en los nodos del clúster.
    """
    try:
        logger.info("Instalando dependencias en el cluster")
        df_recursos_cluster = pd.read_csv("datos_cluster.csv")

        for _, row in df_recursos_cluster.iterrows():
            logger.info("Instalando dependencias en: %s", row["Nombre"])
            instalar_dependencias_vm(
                cliente_azure,
                row["IP"],
                clave_publica,
                row["Usuario"],
                ruta_scripts=ruta_scripts,
                nombre_nodo=row["Nombre"],
                tipo_nodo=row["TipoNodo"],
                grupo_recursos=grupo_recursos,
                zona_dns=zona_dns,
                patron_dns=patron_dns,
            )
    except Exception as e:
        logger.error("Error al instalar dependencias en el cluster: %s", e)


def iniciar_nodos_cluster(cliente_azure, clave_publica, grupo_recursos):
    """
    Inicia el cluster
    """
    try:
        logger.info("Iniciando el cluster")
        df_recursos_cluster = pd.read_csv("datos_cluster.csv")

        nombre_vm = df_recursos_cluster[df_recursos_cluster["TipoNodo"] == "Master"][
            "Nombre"
        ].values[0]

        _, ip_privada = obtener_ip_privada_vm(cliente_azure, grupo_recursos, nombre_vm)

        if ip_privada:
            logger.info("IP privada del nodo master: %s", ip_privada)
        else:
            logger.error("No se pudo obtener la IP privada del nodo master")
            raise ValueError("No se pudo obtener la IP privada del nodo master")

        for _, row in df_recursos_cluster.iterrows():
            logger.info("Iniciando nodo: %s", row["Nombre"])

            if row["TipoNodo"] == "Master":

                iniciar_master(
                    nombre_host=row["IP"],
                    usuario=row["Usuario"],
                    clave_publica=clave_publica,
                )
            elif row["TipoNodo"] == "Worker":
                iniciar_worker(
                    nombre_host=row["IP"],
                    usuario=row["Usuario"],
                    clave_publica=clave_publica,
                    nombre_host_master=ip_privada,
                )

    except Exception as e:
        logger.error("Error al instalar dependencias en el cluster: %s", e)


def actualizar_dns(cf, zona, zona_id, patron_dns="cluster.spark"):

    # Cargamos los datos de los nodos

    logger.debug("Cargando datos del cluster")
    df_recursos_cluster = pd.read_csv("datos_cluster.csv")

    datos_nodo_driver = (
        df_recursos_cluster[df_recursos_cluster["TipoNodo"] == "Master"]
        .iloc[0]
        .to_dict()
    )

    logger.info("Creando registro DNS para el nodo driver")
    create_or_update_dns_record(
        cf,
        nombre_zona=zona,
        id_zona=zona_id,
        record_type="A",
        record_name=patron_dns + ".driver." + zona,
        record_content=datos_nodo_driver["IP"],
        proxied=False,
    )
    logger.info(
        "Registro DNS creado para el nodo driver: %s",
        patron_dns + ".driver." + zona,
    )

    df_workers = df_recursos_cluster[df_recursos_cluster["TipoNodo"] == "Worker"].copy()
    df_workers["id"] = df_workers["Nombre"].str.split("-").str[-1]

    lista_datos_nodos = df_workers[["id", "IP"]].values.tolist()

    for id, ip in lista_datos_nodos:
        logger.info("Creando registro DNS para el nodo worker %s", id)
        create_or_update_dns_record(
            cf,
            nombre_zona=zona,
            id_zona=zona_id,
            record_type="A",
            record_name=f"{patron_dns}.worker.{id}.{zona}",
            record_content=ip,
            proxied=False,
        )
        logger.info("Registro DNS creado para el nodo worker %s", id)


def configurar_driver_devops(clave_publica, clave_devops):
    """
    Configura el nodo driver para DevOps
    """
    df_recursos_cluster = pd.read_csv("datos_cluster.csv")

    # filtramos los datos del nodo master
    datos_master = df_recursos_cluster[
        df_recursos_cluster["TipoNodo"] == "Master"
    ].to_dict(orient="records")[0]

    ruta_clave_devops = Path(clave_devops)

    if ruta_clave_devops.exists():
        logger.info("La ruta de la clave de DevOps existe: %s", ruta_clave_devops)
        with open(ruta_clave_devops, "r", encoding="utf8") as file:
            contenido_clave_devops = file.read()
    else:
        logger.error("La ruta de la clave de DevOps no existe: %s", ruta_clave_devops)
        raise FileNotFoundError("La ruta de la clave de DevOps no existe")

    copiar_clave_privada_devops(
        nombre_vm=datos_master["Nombre"],
        clave_publica=clave_publica,
        ip_nodo=datos_master["IP"],
        usuario=datos_master["Usuario"],
        contenido_clave_devops=contenido_clave_devops,
    )
