import logging
import os
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import (
    NetworkSecurityGroup,
    SecurityRule,
    NetworkInterface,
    NetworkInterfaceIPConfiguration,
    Subnet,
    PublicIPAddress,
)
from func.inicializar_vm import ejecutar_script_remoto
from pathlib import Path
import paramiko

# Obtiene el logger para este módulo
logger = logging.getLogger(__name__)


def crear_vm(
    cliente_azure,
    tamanio_instancia,
    nombre_base,
    grupo_recursos,
    nombre_red_virtual,
    nombre_subred,
    nombre_clave_ssh,
    sistema_operativo,
    region="eastus",
    username="azureuser",
    grupo_seguridad=None,
    reglas_cortafuegos=None,
    grupo_recursos_vnet=None,
):
    """
    Crea una máquina virtual en Azure.
    """

    logger.info(
        "Iniciando la creación de la máquina virtual con nombre: %s", nombre_base
    )

    nombre_nsg = f"{nombre_base}-nsg"
    nic_name = f"{nombre_base}-nic"
    nombre_ip_publica = f"{nombre_base}-ip"

    try:

        if grupo_recursos_vnet is None:
            logger.debug(
                "No se proporcionó un grupo de recursos para la VNet, usando el grupo de recursos principal."
            )
            grupo_recursos_vnet = grupo_recursos

        network_client = NetworkManagementClient(
            cliente_azure.credencial, cliente_azure.id_suscripcion
        )
        compute_client = ComputeManagementClient(
            cliente_azure.credencial, cliente_azure.id_suscripcion
        )

        if grupo_seguridad is None:
            logger.debug("No se proporcionó un grupo de seguridad, creando uno nuevo.")
            nsg_params = NetworkSecurityGroup(location=region)
            nsg = network_client.network_security_groups.begin_create_or_update(
                grupo_recursos, nombre_nsg, nsg_params
            ).result()

            logger.info(
                "Se ha creado el grupo de seguridad: %s con nombre: %s",
                nsg.id,
                nombre_nsg,
            )
        elif grupo_seguridad is not None and isinstance(grupo_seguridad, str):
            logger.debug(
                "Se ha proporcionado un grupo de seguridad existente: %s",
                grupo_seguridad,
            )
            nsg = network_client.network_security_groups.get(
                grupo_recursos, grupo_seguridad
            )
            nombre_nsg = grupo_seguridad
        else:
            raise ValueError(
                "El grupo de seguridad debe ser un nombre de grupo existente o None."
            )

        if reglas_cortafuegos is not None and isinstance(reglas_cortafuegos, list):
            logger.debug("Se han proporcionado reglas de cortafuegos personalizadas.")

            for regla in reglas_cortafuegos:
                try:

                    regla_configuraciones_cortafuego = SecurityRule(
                        protocol=regla["protocolo"],
                        source_port_range=regla["puerto_origen"],
                        destination_port_range=regla["puerto_destino"],
                        source_address_prefix=regla["direccion_origen"],
                        destination_address_prefix=regla["direccion_destino"],
                        access=regla["acceso"],
                        direction=regla["direccion"],
                        priority=regla["prioridad"],
                        name=regla["nombre"],
                    )

                    resultado_regla = (
                        network_client.security_rules.begin_create_or_update(
                            grupo_recursos,
                            nombre_nsg,
                            regla["nombre"],
                            regla_configuraciones_cortafuego,
                        ).result()
                    )

                    logger.info(
                        "Se ha creado la regla de cortafuegos: %s",
                        resultado_regla.id,
                    )

                except Exception as e:
                    logger.error("Error al crear la regla de cortafuegos: %s", e)

        ## Subred

        subnet = network_client.subnets.get(
            grupo_recursos_vnet, nombre_red_virtual, nombre_subred
        )

        logger.info(
            "La VM se va a asociar a la subred: %s con nombre: %s",
            subnet.id,
            nombre_subred,
        )

        # Ip Publica
        resultado_ip = public_ip = (
            network_client.public_ip_addresses.begin_create_or_update(
                grupo_recursos,
                nombre_ip_publica,
                {
                    "location": region,
                    "sku": {"name": "Standard"},
                    "public_ip_allocation_method": "Static",
                },
            ).result()
        )

        logger.info(
            "Se ha creado la IP pública: %s",
            resultado_ip.id,
        )

        # Interface de red
        nic_params = NetworkInterface(
            location=region,
            ip_configurations=[
                NetworkInterfaceIPConfiguration(
                    name="default",
                    subnet=Subnet(id=subnet.id),
                    public_ip_address=PublicIPAddress(id=public_ip.id),
                )
            ],
            network_security_group=nsg,
        )

        nic = network_client.network_interfaces.begin_create_or_update(
            grupo_recursos, nic_name, nic_params
        ).result()

        logger.info(
            "Se ha creado la interfaz de red: %s",
            nic.id,
        )

        # Clave ssh
        ssh_key = compute_client.ssh_public_keys.get(
            resource_group_name=grupo_recursos, ssh_public_key_name=nombre_clave_ssh
        )

        logger.info(
            "Se ha obtenido la clave SSH: %s",
            ssh_key.id,
        )

        ssh_key_data = ssh_key.public_key

        # Maquina virtual

        # ⚡ 4. Crear la VM
        parametros_vm = {
            "location": region,
            "hardware_profile": {"vm_size": tamanio_instancia},
            "storage_profile": {"image_reference": sistema_operativo},
            "os_profile": {
                "computer_name": nombre_base,
                "admin_username": username,
                "linux_configuration": {
                    "disable_password_authentication": True,
                    "ssh": {
                        "public_keys": [
                            {
                                "path": f"/home/{username}/.ssh/authorized_keys",
                                "key_data": ssh_key_data,
                            }
                        ]
                    },
                },
            },
            "network_profile": {
                "network_interfaces": [{"id": nic.id, "primary": True}]
            },
            "os_disk": {
                "name": nombre_base + "disk",
                "create_option": "FromImage",
                "disk_size_gb": 32,
                "managed_disk": {"storage_account_type": "StandardSSD_LRS"},
            },
        }

        compute_client.virtual_machines.begin_create_or_update(
            grupo_recursos, nombre_base, parametros_vm
        ).result()

        logger.info(
            "✅ VM '%s' creada con IP estática %s",
            nombre_base,
            public_ip.ip_address,
        )

        return True, nombre_base, public_ip.ip_address

    except Exception as e:
        logger.error(
            "Error al crear la VM: %s",
            e,
        )
        return False, None, None


def eliminar_vm(cliente_azure, nombre_vm, grupo_recursos):
    """
    Elimina una máquina virtual de Azure.

    Args:
        cliente_azure (ClienteAzure): Cliente de Azure.
        nombre_vm (str): Nombre de la máquina virtual a eliminar.
        grupo_recursos (str): Nombre del grupo de recursos donde se encuentra la VM.
    """
    logger.info("Iniciando la eliminación de la VM: %s", nombre_vm)
    # Cliente de Compute
    compute_client = ComputeManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )

    # Cliente de Red
    network_client = NetworkManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )

    try:
        # Obtener la VM (antes de borrarla)

        vm = compute_client.virtual_machines.get(grupo_recursos, nombre_vm)
        logger.debug("VM obtenida: %s", vm.id)

        # Nombre del disco del sistema operativo
        nombre_disco_duro = vm.storage_profile.os_disk.name
        logger.debug("Disco duro asociado: %s", nombre_disco_duro)

        nic_id = vm.network_profile.network_interfaces[0].id
        nic_name = nic_id.split("/")[-1]
        logger.debug("NIC asociada: %s", nic_name)

        # NIC asociada
        nic = network_client.network_interfaces.get(grupo_recursos, nic_name)
        ip_config = nic.ip_configurations[0]
        public_ip_id = (
            ip_config.public_ip_address.id if ip_config.public_ip_address else None
        )
        public_ip_name = public_ip_id.split("/")[-1] if public_ip_id else None
        logger.debug("IP pública asociada: %s", public_ip_name)

        # Eliminar la VM
        compute_client.virtual_machines.begin_delete(grupo_recursos, nombre_vm).result()
        logger.info("VM '%s' eliminada.", nombre_vm)

        # Eliminar NIC
        network_client.network_interfaces.begin_delete(
            grupo_recursos, nic_name
        ).result()
        logger.info("NIC '%s' eliminada.", nic_name)

        # Eliminar disco
        compute_client.disks.begin_delete(grupo_recursos, nombre_disco_duro).result()
        logger.info("Disco '%s' eliminado.", nombre_disco_duro)

        # 6. Eliminar la IP pública (si tenía)

        if public_ip_name:
            network_client.public_ip_addresses.begin_delete(
                grupo_recursos, public_ip_name
            ).result()
            logger.info("IP pública '%s' eliminada.", public_ip_name)

        if nic.network_security_group:
            nsg_id = nic.network_security_group.id
            nsg_name = nsg_id.split("/")[-1]
            logger.info("La VM '%s' tiene asignado el NSG: %s", nombre_vm, nsg_name)

            network_client.network_security_groups.begin_delete(
                grupo_recursos, nsg_name
            ).result()
            logger.info("NSG '%s' eliminado.", nsg_name)
        else:
            logger.info("La VM '%s' no tiene NSG asignado", nombre_vm)

        return True, nombre_vm

    except Exception as e:
        logger.error("Error al eliminar la VM '%s': %s", nombre_vm, e)
        return False, None


def crear_grupo_seguridad(
    cliente_azure, nombre_nsg, region, grupo_recursos, reglas_cortafuegos=None
):

    network_client = NetworkManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )

    try:

        nsg_params = NetworkSecurityGroup(location=region)
        nsg = network_client.network_security_groups.begin_create_or_update(
            grupo_recursos, nombre_nsg, nsg_params
        ).result()

        logger.info(
            "Se ha creado el grupo de seguridad: %s",
            nsg.id,
        )

        if reglas_cortafuegos is not None and isinstance(reglas_cortafuegos, list):
            logger.debug("Se han proporcionado reglas de cortafuegos personalizadas.")

            for regla in reglas_cortafuegos:
                try:

                    regla_configuraciones_cortafuego = SecurityRule(
                        protocol=regla["protocolo"],
                        source_port_range=regla["puerto_origen"],
                        destination_port_range=regla["puerto_destino"],
                        source_address_prefix=regla["direccion_origen"],
                        destination_address_prefix=regla["direccion_destino"],
                        access=regla["acceso"],
                        direction=regla["direccion"],
                        priority=regla["prioridad"],
                        name=regla["nombre"],
                    )

                    resultado_regla = (
                        network_client.security_rules.begin_create_or_update(
                            grupo_recursos,
                            nombre_nsg,
                            regla["nombre"],
                            regla_configuraciones_cortafuego,
                        ).result()
                    )

                    logger.info(
                        "Se ha creado la regla de cortafuegos: %s",
                        resultado_regla.id,
                    )

                except Exception as e:
                    logger.error("Error al crear la regla de cortafuegos: %s", e)

        return True

    except Exception as e:
        logger.error("Error al crear el grupo de seguridad: %s", e)
        return False


def eliminar_vm(cliente_azure, grupo_recursos, nombre_vm):
    """
    Elimina una máquina virtual en Azure.
    """

    compute_client = ComputeManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )

    try:
        # 1. Detener la VM
        compute_client.virtual_machines.begin_power_off(
            grupo_recursos, nombre_vm
        ).result()
        logger.info("VM '%s' detenida.", nombre_vm)

        # 2. Eliminar la VM
        compute_client.virtual_machines.begin_delete(grupo_recursos, nombre_vm).result()
        logger.info("VM '%s' eliminada.", nombre_vm)

        # Eliminar NIC
        network_client.network_interfaces.begin_delete(
            grupo_recursos, nic_name
        ).result()
        logger.info("NIC '%s' eliminada.", nic_name)

        # Eliminar disco
        compute_client.disks.begin_delete(grupo_recursos, nombre_disco_duro).result()
        logger.info("Disco '%s' eliminado.", nombre_disco_duro)

        # 6. Eliminar la IP pública (si tenía)

        if public_ip_name:
            network_client.public_ip_addresses.begin_delete(
                grupo_recursos, public_ip_name
            ).result()
            logger.info("IP pública '%s' eliminada.", public_ip_name)

        if nic.network_security_group:
            nsg_id = nic.network_security_group.id
            nsg_name = nsg_id.split("/")[-1]
            logger.info("La VM '%s' tiene asignado el NSG: %s", nombre_vm, nsg_name)

            network_client.network_security_groups.begin_delete(
                grupo_recursos, nsg_name
            ).result()
            logger.info("NSG '%s' eliminado.", nsg_name)
        else:
            logger.info("La VM '%s' no tiene NSG asignado", nombre_vm)

        return True, nombre_vm

    except Exception as e:
        logger.error("Error al eliminar la VM '%s': %s", nombre_vm, e)
        return False, None


def crear_grupo_seguridad(
    cliente_azure, nombre_nsg, region, grupo_recursos, reglas_cortafuegos=None
):

    network_client = NetworkManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )

    try:

        nsg_params = NetworkSecurityGroup(location=region)
        nsg = network_client.network_security_groups.begin_create_or_update(
            grupo_recursos, nombre_nsg, nsg_params
        ).result()

        logger.info(
            "Se ha creado el grupo de seguridad: %s",
            nsg.id,
        )

        if reglas_cortafuegos is not None and isinstance(reglas_cortafuegos, list):
            logger.debug("Se han proporcionado reglas de cortafuegos personalizadas.")

            for regla in reglas_cortafuegos:
                try:

                    regla_configuraciones_cortafuego = SecurityRule(
                        protocol=regla["protocolo"],
                        source_port_range=regla["puerto_origen"],
                        destination_port_range=regla["puerto_destino"],
                        source_address_prefix=regla["direccion_origen"],
                        destination_address_prefix=regla["direccion_destino"],
                        access=regla["acceso"],
                        direction=regla["direccion"],
                        priority=regla["prioridad"],
                        name=regla["nombre"],
                    )

                    resultado_regla = (
                        network_client.security_rules.begin_create_or_update(
                            grupo_recursos,
                            nombre_nsg,
                            regla["nombre"],
                            regla_configuraciones_cortafuego,
                        ).result()
                    )

                    logger.info(
                        "Se ha creado la regla de cortafuegos: %s",
                        resultado_regla.id,
                    )

                except Exception as e:
                    logger.error("Error al crear la regla de cortafuegos: %s", e)

        return True

    except Exception as e:
        logger.error("Error al crear el grupo de seguridad: %s", e)
        return False


def eliminar_vm(cliente_azure, grupo_recursos, nombre_vm):
    """
    Elimina una máquina virtual de Azure.
    """

    # Cliente de Compute
    compute_client = ComputeManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )

    # Cliente de Red
    network_client = NetworkManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )

    try:

        logger.info("Iniciando la eliminación de la VM: %s", nombre_vm)

        # Obtener la VM (antes de borrarla)
        vm = compute_client.virtual_machines.get(grupo_recursos, nombre_vm)
        logger.debug("Se ha obtenido la VM: %s", vm.id)

        # Nombre del disco del sistema operativo
        os_disk_name = vm.storage_profile.os_disk.name
        logger.debug("Disco duro asociado: %s", os_disk_name)

        nic_id = vm.network_profile.network_interfaces[0].id
        logger.debug("NIC ID: %s", nic_id)

        nic_name = nic_id.split("/")[-1]
        logger.debug("NIC asociada: %s", nic_name)

        # NIC asociada
        nic = network_client.network_interfaces.get(grupo_recursos, nic_name)
        ip_config = nic.ip_configurations[0]
        public_ip_id = (
            ip_config.public_ip_address.id if ip_config.public_ip_address else None
        )
        public_ip_name = public_ip_id.split("/")[-1] if public_ip_id else None

        # Eliminar la VM
        compute_client.virtual_machines.begin_delete(grupo_recursos, nombre_vm).result()
        logger.info("VM %s eliminada.", nombre_vm)

        # Eliminar NIC
        network_client.network_interfaces.begin_delete(
            grupo_recursos, nic_name
        ).result()
        logger.info("NIC %s eliminada.", nic_name)

        # Eliminar disco
        compute_client.disks.begin_delete(grupo_recursos, os_disk_name).result()
        logger.info("Disco %s eliminado.", os_disk_name)

        # 6. Eliminar la IP pública (si tenía)

        if public_ip_name:
            network_client.public_ip_addresses.begin_delete(
                grupo_recursos, public_ip_name
            ).result()
            logger.info("IP pública %s eliminada.", public_ip_name)

        return True

    except Exception as e:
        logger.error("Error al eliminar la VM %s: %s", nombre_vm, e)
        return False


def eliminar_grupo_seguridad(cliente_azure, grupo_recursos, nombre_nsg):

    network_client = NetworkManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )
    try:
        network_client.network_security_groups.begin_delete(
            grupo_recursos, nombre_nsg
        ).result()
        logger.info("NSG '%s' eliminado.", nombre_nsg)

    except Exception as e:
        logger.error("Error al eliminar el NSG '%s': %s", nombre_nsg, e)
        return False


def instalar_dependencias_vm(
    cliente_azure,
    nombre_host,
    clave_publica,
    usuario,
    ruta_scripts,
    nombre_nodo,
    tipo_nodo,
    grupo_recursos,
    zona_dns,
    patron_dns,
):
    """
    Inicializa la máquina virtual.
    """

    logger.info("Iniciando la instalación de dependencias en la VM: %s", nombre_host)

    _, ip_privada_vm = obtener_ip_privada_vm(cliente_azure, grupo_recursos, nombre_nodo)

    logger.info("IP privada de la VM %s: %s", nombre_nodo, ip_privada_vm)

    # leemos todos los archivos de la carpeta de scripts
    scripts = [f for f in os.listdir(ruta_scripts) if f.endswith(".sh")]

    for script in scripts:

        ruta_script_local = Path(ruta_scripts) / script

        if ruta_script_local.exists():

            logger.info("Se ha encontrado el script '%s'.", ruta_script_local)
            with ruta_script_local.open("r", encoding="utf-8") as f:
                script_content = f.read()

            script_content = script_content.replace("{{{USUARIO}}}", usuario)
            if tipo_nodo == "Master":
                script_content = script_content.replace(
                    "{{{LINEA_CONFIG_1}}}", "export SPARK_DRIVER_BIND_ADDRESS=0.0.0.0"
                )
                script_content = script_content.replace(
                    "{{{LINEA_CONFIG_2}}}", f"export SPARK_DRIVER_HOST={ip_privada_vm}"
                )
                script_content = script_content.replace(
                    "{{{LINEA_CONFIG_3}}}",
                    f"SPARK_PUBLIC_DNS={patron_dns}.driver.{zona_dns}",
                )
            elif tipo_nodo == "Worker":

                numero_nodo = nombre_nodo.split("-")[-1]

                script_content = script_content.replace(
                    "{{{LINEA_CONFIG_1}}}", f"export SPARK_LOCAL_IP={ip_privada_vm}"
                )
                script_content = script_content.replace(
                    "{{{LINEA_CONFIG_2}}}",
                    f"export SPARK_PUBLIC_DNS={patron_dns}.worker.{numero_nodo}.{zona_dns}",
                )
                script_content = script_content.replace(
                    "{{{LINEA_CONFIG_3}}}",
                    "",
                )
            else:
                raise ValueError("Tipo de nodo desconocido.")

            # Ejecutamos el script de instalación de Hadoop
            ejecutar_script_remoto(
                nombre_host=nombre_host,
                clave_publica=clave_publica,
                usuario=usuario,
                script_content=script_content,
                ruta_script_remota=f"~/{script}",
            )


def iniciar_master(nombre_host, usuario, clave_publica, port=22):
    """
    Se conecta al servidor remoto, copia un script y lo ejecuta.
    """
    ssh_client = None
    sftp_client = None

    try:

        # --- 1. Conexión SSH ---
        logger.info("Intentando conectar al servidor: %s", nombre_host)

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_client.connect(
            hostname=nombre_host,
            port=port,
            username=usuario,
            key_filename=clave_publica + ".pem",
        )

        logger.info("Conexión establecida con éxito.")

        _, stdout, stderr = ssh_client.exec_command("/opt/spark/sbin/start-master.sh")

        logger.info("Nodo maestro iniciado.")
        logger.info("Salida del comando: %s", stdout.read().decode())

    except paramiko.AuthenticationException:
        logger.error(
            "Error de autenticación. Verifica el usuario, la contraseña o la clave SSH."
        )
    except paramiko.SSHException as e:
        logger.error("Error en la conexión SSH: %s", e)
    except Exception as e:
        logger.error("Ocurrió un error inesperado: %s", e)
        exit(1)
    finally:
        if sftp_client:
            sftp_client.close()
        if ssh_client:
            ssh_client.close()
            print("Conexión SSH cerrada.")


def iniciar_worker(nombre_host, usuario, nombre_host_master, clave_publica, port=22):
    """
    Se conecta al servidor remoto, copia un script y lo ejecuta.
    """
    ssh_client = None
    sftp_client = None

    try:

        # --- 1. Conexión SSH ---
        logger.info("Intentando conectar al servidor: %s", nombre_host)

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_client.connect(
            hostname=nombre_host,
            port=port,
            username=usuario,
            key_filename=clave_publica + ".pem",
        )

        logger.info("Conexión establecida con éxito.")

        _, stdout, stderr = ssh_client.exec_command(
            "/opt/spark/sbin/start-worker.sh spark://" + nombre_host_master + ":7077"
        )

        logger.info("Nodo trabajador iniciado.")
        logger.info("Salida del comando: %s", stdout.read().decode())
        logger.error("Error del comando: %s", stderr.read().decode())

    except paramiko.AuthenticationException:
        logger.error(
            "Error de autenticación. Verifica el usuario, la contraseña o la clave SSH."
        )
    except paramiko.SSHException as e:
        logger.error("Error en la conexión SSH: %s", e)
    except Exception as e:
        logger.error("Ocurrió un error inesperado: %s", e)
        exit(1)
    finally:
        if sftp_client:
            sftp_client.close()
        if ssh_client:
            ssh_client.close()
            logger.info("Conexión SSH cerrada.")


def obtener_ip_privada_vm(cliente_azure, grupo_recursos, nombre_vm):
    """
    Obtiene la ip privada de la vm
    """

    compute_client = ComputeManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )
    network_client = NetworkManagementClient(
        cliente_azure.credencial, cliente_azure.id_suscripcion
    )

    vm = compute_client.virtual_machines.get(grupo_recursos, nombre_vm)
    logger.info("Buscando IP privada para la VM: %s", vm.name)

    for nic_reference in vm.network_profile.network_interfaces:

        nic_id = nic_reference.id
        nic_resource_group = nic_id.split("/")[4]
        nic_name = nic_id.split("/")[-1]

        nic = network_client.network_interfaces.get(nic_resource_group, nic_name)

        # 4. Iterar a través de las configuraciones de IP de la NIC
        for ip_config in nic.ip_configurations:

            private_ip_address = ip_config.private_ip_address
            if private_ip_address:
                logger.info(
                    "Dirección IP privada de la NIC '%s': %s",
                    nic_name,
                    private_ip_address,
                )
                return True, private_ip_address
            else:
                logger.warning(
                    "No se encontró una dirección IP privada para la configuración de IP '%s'.",
                    ip_config.name,
                )
        return False, None


def copiar_clave_privada_devops(
    nombre_vm, clave_publica, ip_nodo, usuario, contenido_clave_devops
):
    """
    Copia la clave privada de DevOps a la VM especificada.
    """

    ssh_client = None
    sftp_client = None

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=ip_nodo,
            username=usuario,
            key_filename=clave_publica + ".pem",
        )

        command = f"""
    cat <<'SCRIPT_END' | tee /home/{usuario}/.ssh/id_rsa > /dev/null
{contenido_clave_devops}
SCRIPT_END
"""
        logger.info("Creando el script en el servidor...")
        _, stdout, _ = ssh_client.exec_command(command)

        logger.info("Clave privada de DevOps copiada a la VM %s", nombre_vm)

        ssh_client.exec_command(f"sudo chmod 400 /home/{usuario}/.ssh/id_rsa")

        ssh_client.exec_command(f"mkdir -p /home/{usuario}/Proyectos")

    except paramiko.AuthenticationException:
        logger.error("Error de autenticación al conectar a la VM %s", nombre_vm)
    except paramiko.SSHException as e:
        logger.error("Error en la conexión SSH: %s", e)
    finally:
        if sftp_client:
            sftp_client.close()
        if ssh_client:
            ssh_client.close()
