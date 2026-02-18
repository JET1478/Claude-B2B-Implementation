"""CRM adapter - HubSpot API + generic webhook fallback."""

import httpx
import structlog

from app.services.crypto import decrypt_value

logger = structlog.get_logger()

HUBSPOT_BASE_URL = "https://api.hubapi.com"


class CRMAdapter:
    """Adapter for CRM operations. Supports HubSpot and generic webhook."""

    def __init__(self, hubspot_key_encrypted: str | None = None, webhook_url: str | None = None):
        self._hubspot_key = None
        self._webhook_url = webhook_url
        if hubspot_key_encrypted:
            try:
                self._hubspot_key = decrypt_value(hubspot_key_encrypted)
            except Exception:
                logger.error("failed_to_decrypt_hubspot_key")

    @property
    def is_configured(self) -> bool:
        return bool(self._hubspot_key or self._webhook_url)

    async def create_contact(self, data: dict) -> dict | None:
        """Create or update a contact in CRM."""
        if self._hubspot_key:
            return await self._hubspot_create_contact(data)
        if self._webhook_url:
            return await self._webhook_send("contact_created", data)
        logger.info("crm_not_configured_skipping")
        return None

    async def create_deal(self, data: dict, contact_id: str | None = None) -> dict | None:
        """Create a deal/opportunity in CRM."""
        if self._hubspot_key:
            return await self._hubspot_create_deal(data, contact_id)
        if self._webhook_url:
            return await self._webhook_send("deal_created", {**data, "contact_id": contact_id})
        return None

    async def _hubspot_create_contact(self, data: dict) -> dict | None:
        """Create contact via HubSpot API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts",
                    headers={
                        "Authorization": f"Bearer {self._hubspot_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "properties": {
                            "email": data.get("email", ""),
                            "firstname": data.get("name", "").split()[0] if data.get("name") else "",
                            "lastname": " ".join(data.get("name", "").split()[1:]) if data.get("name") else "",
                            "company": data.get("company", ""),
                            "phone": data.get("phone", ""),
                            "hs_lead_status": "NEW",
                        }
                    },
                )
                if resp.status_code == 409:
                    # Contact exists, try to find and update
                    logger.info("hubspot_contact_exists", email=data.get("email"))
                    return await self._hubspot_find_contact(data.get("email", ""))
                resp.raise_for_status()
                result = resp.json()
                logger.info("hubspot_contact_created", contact_id=result.get("id"))
                return result
        except Exception as e:
            logger.error("hubspot_create_contact_failed", error=str(e))
            return None

    async def _hubspot_find_contact(self, email: str) -> dict | None:
        """Find a contact by email in HubSpot."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/search",
                    headers={
                        "Authorization": f"Bearer {self._hubspot_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email,
                            }]
                        }]
                    },
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                return results[0] if results else None
        except Exception as e:
            logger.error("hubspot_find_contact_failed", error=str(e))
            return None

    async def _hubspot_create_deal(self, data: dict, contact_id: str | None) -> dict | None:
        """Create deal via HubSpot API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                deal_data = {
                    "properties": {
                        "dealname": data.get("deal_name", f"Lead: {data.get('company', 'Unknown')}"),
                        "pipeline": "default",
                        "dealstage": data.get("stage", "qualifiedtobuy"),
                        "description": data.get("summary", ""),
                    }
                }
                if contact_id:
                    deal_data["associations"] = [{
                        "to": {"id": contact_id},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}]
                    }]

                resp = await client.post(
                    f"{HUBSPOT_BASE_URL}/crm/v3/objects/deals",
                    headers={
                        "Authorization": f"Bearer {self._hubspot_key}",
                        "Content-Type": "application/json",
                    },
                    json=deal_data,
                )
                resp.raise_for_status()
                result = resp.json()
                logger.info("hubspot_deal_created", deal_id=result.get("id"))
                return result
        except Exception as e:
            logger.error("hubspot_create_deal_failed", error=str(e))
            return None

    async def _webhook_send(self, event: str, data: dict) -> dict | None:
        """Send event to generic CRM webhook."""
        if not self._webhook_url:
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self._webhook_url,
                    json={"event": event, "data": data},
                )
                resp.raise_for_status()
                logger.info("crm_webhook_sent", event=event)
                return resp.json()
        except Exception as e:
            logger.error("crm_webhook_failed", error=str(e), event=event)
            return None
