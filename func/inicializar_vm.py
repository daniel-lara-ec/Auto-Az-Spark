import paramiko
import os
import logging
from traceback import format_exc

# Obtiene el logger para este módulo
logger = logging.getLogger(__name__)


def ejecutar_script_remoto(
    nombre_host, clave_publica, usuario, script_content, ruta_script_remota, port=22
):
    """
    Se conecta al servidor remoto, copia un script y lo ejecuta.
    """
    ssh_client = None
    sftp_client = None

    try:

        # --- 1. Conexión SSH ---
        logger.info("Intentando conectar al servidor...")

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_client.connect(
            hostname=nombre_host,
            port=port,
            username=usuario,
            key_filename=clave_publica + ".pem",
        )

        logger.info("Conexión establecida con éxito.")

        # --- 2. Eliminamos el archivo remoto si existe
        ssh_client.exec_command(f"rm -f {ruta_script_remota}")

        # --- 3. Crear el archivo remoto con el heredoc ---
        # El comando utiliza 'sudo tee' para escribir el contenido en el archivo remoto
        command = f"""
    cat <<'SCRIPT_END' | sudo tee {ruta_script_remota} > /dev/null
{script_content}
SCRIPT_END
"""
        logger.info("Creando el script en el servidor...")
        _, stdout, _ = ssh_client.exec_command(command)

        ssh_client.exec_command(f"sudo chmod 777 {ruta_script_remota}")

        # # --- 3. Ejecución remota del script ---
        logger.info("Ejecutando el script '%s' en el servidor...", ruta_script_remota)
        _, stdout, _ = ssh_client.exec_command(f"sudo {ruta_script_remota}")

        # Lee y muestra la salida del script en tiempo real
        for line in stdout:
            logger.info("STDOUT: %s", line)

        logger.info("Ejecución del script completada.")

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
