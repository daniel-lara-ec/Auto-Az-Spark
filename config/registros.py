import logging


LOG_FILE = "az-sdk.log"


class FiltroAzure(logging.Filter):
    def filter(self, record):
        # Ignora los logs de los módulos externos que no quieres ver.
        # Puedes añadir más nombres de módulos aquí si es necesario.
        return not record.name.startswith(("azure", "httpx"))


def setup_logging():
    """
    Configura el logger principal para la aplicación.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    filtro_registros_azure = FiltroAzure()
    root_logger.addFilter(filtro_registros_azure)

    consola_handler = logging.StreamHandler()
    consola_handler.setLevel(logging.INFO)
    consola_handler.addFilter(filtro_registros_azure)

    archivo_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    archivo_handler.setLevel(logging.DEBUG)
    archivo_handler.addFilter(filtro_registros_azure)

    formato = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    consola_handler.setFormatter(formato)
    archivo_handler.setFormatter(formato)

    root_logger.addHandler(consola_handler)
    root_logger.addHandler(archivo_handler)
