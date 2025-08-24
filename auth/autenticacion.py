import logging

# Obtiene el logger para este módulo
logger = logging.getLogger(__name__)


class ClienteAzure:
    """
    Una clase para gestionar un cliente de Azure.

    Args:
        credencial (object): La credencial de autenticación de Azure.
        id_suscripcion (str): El ID de la suscripción de Azure.
    """

    def __init__(self, credencial, id_suscripcion):
        self.credencial = credencial
        self.id_suscripcion = id_suscripcion
