import logging

# Obtiene el logger para este módulo
logger = logging.getLogger(__name__)


def create_or_update_dns_record(
    cf,
    nombre_zona,
    id_zona,
    record_type,
    record_name,
    record_content,
    proxied=False,
    ttl=120,
    comment="SparkClusterSdk",
):
    """
    Crea o actualiza un registro DNS en Cloudflare.
    """

    existing_records = cf.dns.records.list(
        zone_id=id_zona, name=record_name, type=record_type
    )

    if existing_records.result:
        # Ya existe → actualizar
        record_id = existing_records.result[0].id
        updated = cf.dns.records.update(
            zone_id=id_zona,
            dns_record_id=record_id,
            content=record_content,
            type=record_type,
            name=record_name,
        )
        logger.info(f"✅ Registro actualizado: {updated}")
        return updated
    else:
        # No existe → crear
        created = cf.dns.records.create(
            zone_id=id_zona,
            name=record_name,
            type=record_type,
            content=record_content,
            proxied=proxied,
            ttl=ttl,
            comment=comment,
        )
        logger.info(f"🆕 Registro creado: {created}")
        return created
