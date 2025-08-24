import argparse
import logging
import sys
import time

from azure.identity import DefaultAzureCredential
from cloudflare import Cloudflare

from auth.autenticacion import ClienteAzure
from config.configuraciones import (
    GRUPO_RECURSOS,
    GRUPO_RECURSOS_VNET,
    ID_SUSRCIPCION,
    IP_PUBLICA,
    NOMBRE_CLAVE_SSH,
    NOMBRE_CLUSTER,
    NOMBRE_RED_VIRTUAL,
    NOMBRE_SUBRED,
    NUMERO_NODOS,
    REGION,
    TAMANIO_INSTANCIA_DRIVER,
    TAMANIO_INSTANCIA_WORKER,
    USERNAME,
    RUTA_SCRIPTS_DEPENDENCIAS,
    CLOUDFLARE_TOKEN,
    ZONA_DNS,
    PATRON_DNS,
    ZONA_DNS_ID,
    CLAVE_PRIVADA_DEVOPS,
)
from config.registros import setup_logging
from func.funciones_cluster import (
    crear_cluster,
    eliminar_cluster,
    instalar_dependencias_cluster,
    iniciar_nodos_cluster,
    actualizar_dns,
    configurar_driver_devops,
)

setup_logging()

logger = logging.getLogger(__name__)


def crear_recurso():
    """
    Crea un cluster según las configuraciones definidas en .env
    """

    logger.info("Creando cluster")
    cred = DefaultAzureCredential()
    cliente_azure = ClienteAzure(credencial=cred, id_suscripcion=ID_SUSRCIPCION)

    crear_cluster(
        cliente_azure=cliente_azure,
        nombre_base=NOMBRE_CLUSTER,
        cantidad_nodos=NUMERO_NODOS,
        tamanio_instancia_driver=TAMANIO_INSTANCIA_DRIVER,
        grupo_recursos=GRUPO_RECURSOS,
        nombre_red_virtual=NOMBRE_RED_VIRTUAL,
        nombre_subred=NOMBRE_SUBRED,
        nombre_clave_ssh=NOMBRE_CLAVE_SSH,
        region=REGION,
        username_driver=USERNAME,
        grupo_recursos_vnet=GRUPO_RECURSOS_VNET,
        tamanio_instancia_worker=TAMANIO_INSTANCIA_WORKER,
        ip_publica=IP_PUBLICA,
    )


def eliminar_recurso():
    """
    Elimina un cluster según las configuraciones definidas en los archivos .csv
    """
    logger.info("Eliminando cluster")
    cred = DefaultAzureCredential()
    cliente_azure = ClienteAzure(credencial=cred, id_suscripcion=ID_SUSRCIPCION)
    eliminar_cluster(cliente_azure=cliente_azure, grupo_recursos=GRUPO_RECURSOS)


def instalar_dependencias():
    """
    Instala las dependencias en los nodos del clúster.
    """
    logger.info("Instalando dependencias en el cluster")
    logger.info(RUTA_SCRIPTS_DEPENDENCIAS)
    cred = DefaultAzureCredential()
    cliente_azure = ClienteAzure(credencial=cred, id_suscripcion=ID_SUSRCIPCION)
    instalar_dependencias_cluster(
        cliente_azure,
        RUTA_SCRIPTS_DEPENDENCIAS,
        NOMBRE_CLAVE_SSH,
        ZONA_DNS,
        PATRON_DNS,
        GRUPO_RECURSOS,
    )


def iniciar_cluster():
    """
    Inicia el clúster.
    """
    logger.info("Iniciando el cluster")
    cred = DefaultAzureCredential()
    cliente_azure = ClienteAzure(credencial=cred, id_suscripcion=ID_SUSRCIPCION)
    iniciar_nodos_cluster(cliente_azure, NOMBRE_CLAVE_SSH, GRUPO_RECURSOS)


def configurar_dns():
    """
    Configura los registros DNS para el clúster.
    """
    logger.info("Configurando DNS para el cluster")
    cf = Cloudflare(api_token=CLOUDFLARE_TOKEN)
    cf.dns.records.list
    actualizar_dns(cf, ZONA_DNS, ZONA_DNS_ID, PATRON_DNS)


def configurar_devops():
    """
    Configura el entorno de DevOps para el clúster.
    """
    logger.info("Configurando DevOps para el cluster")
    configurar_driver_devops(NOMBRE_CLAVE_SSH, CLAVE_PRIVADA_DEVOPS)


def orquestador_cluster():
    """
    Orquesta las acciones a realizar sobre el clúster.
    """
    crear_recurso()
    time.sleep(60)
    instalar_dependencias()
    time.sleep(15)
    iniciar_cluster()
    time.sleep(15)
    configurar_dns()
    time.sleep(15)
    configurar_devops()


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Script para gestionar recursos (crear/eliminar)."
    )

    parser.add_argument(
        "--crear",
        action="store_true",
        help="Crea un nuevo recurso.",
    )
    parser.add_argument(
        "--eliminar",
        action="store_true",
        help="Elimina un recurso existente.",
    )
    parser.add_argument(
        "--dependencias",
        action="store_true",
        help="Instala las dependencias en el clúster.",
    )
    parser.add_argument(
        "--iniciar",
        action="store_true",
        help="Inicia los nodos del clúster.",
    )
    parser.add_argument(
        "--configurar-dns",
        action="store_true",
        help="Configura los registros DNS para el clúster.",
    )
    parser.add_argument(
        "--configurar-devops",
        action="store_true",
        help="Configura el entorno de DevOps para el clúster.",
    )
    parser.add_argument(
        "--orquestar",
        action="store_true",
        help="Orquesta las acciones a realizar sobre el clúster.",
    )

    args = parser.parse_args()

    if args.crear and args.eliminar:
        logger.error("Error: No puedes usar --crear y --eliminar al mismo tiempo.")
        sys.exit(1)
    elif args.crear:
        crear_recurso()
    elif args.eliminar:
        eliminar_recurso()
    elif args.dependencias:
        instalar_dependencias()
    elif args.iniciar:
        iniciar_cluster()
    elif args.configurar_dns:
        configurar_dns()
    elif args.configurar_devops:
        configurar_devops()
    elif args.orquestar:
        orquestador_cluster()
    else:
        logger.warning("No se especificó ninguna acción. Usa --crear o --eliminar.")
        parser.print_help()


if __name__ == "__main__":
    main()
