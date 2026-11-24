"""Optional cloud help (owner: AI-3, P6). Spec: thinking/08-modellek-es-utvonalvalasztas/03-felhos-segitseg-opcionalis.md.

    from auri_core.cloud import CloudClient, prepare_payload
    client = CloudClient(cfg, store)
    ans = await client.chat(messages, purpose="L4 fallback", interactive=True, user_id=uid)  # CloudAnswer | CloudRefusal

Off by default; never for background work or guests; personal data / secrets → not sent at all.
"""

from .client import CloudAnswer, CloudClient, CloudPayload, CloudRefusal, prepare_payload

__all__ = ["CloudAnswer", "CloudClient", "CloudPayload", "CloudRefusal", "prepare_payload"]
