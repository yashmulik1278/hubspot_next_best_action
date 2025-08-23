import logging
import os
import json
import requests
from typing import Any, Dict, List, Optional, Literal

from hubspot import HubSpot
from hubspot.crm.tickets import PublicObjectSearchRequest as TicketSearchRequest
from hubspot.crm.contacts import PublicObjectSearchRequest as ContactSearchRequest, SimplePublicObjectInputForCreate as ContactCreateInput
from hubspot.crm.companies import PublicObjectSearchRequest as CompanySearchRequest
from hubspot.crm.deals import PublicObjectSearchRequest as DealSearchRequest, SimplePublicObjectInputForCreate as DealCreateInput
from hubspot.crm.contacts.exceptions import ApiException

logger = logging.getLogger(__name__)

# --- Individual Clients ---

class CompanyClient:
    def __init__(self, hubspot_client: HubSpot):
        self.client = hubspot_client.crm.companies

    def get_recent(self, limit: int = 10) -> List[Dict]:
        search_req = CompanySearchRequest(sorts=[{"propertyName": "lastmodifieddate", "direction": "DESCENDING"}], limit=limit)
        response = self.client.search_api.do_search(public_object_search_request=search_req)
        return [c.to_dict() for c in response.results]

class ContactClient:
    def __init__(self, hubspot_client: HubSpot):
        self.client = hubspot_client.crm.contacts

    def get_recent(self, limit: int = 10) -> List[Dict]:
        search_req = ContactSearchRequest(sorts=[{"propertyName": "lastmodifieddate", "direction": "DESCENDING"}], limit=limit)
        response = self.client.search_api.do_search(public_object_search_request=search_req)
        return [c.to_dict() for c in response.results]
    
    def create_contact(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        create_input = ContactCreateInput(properties=properties)
        response = self.client.basic_api.create(simple_public_object_input_for_create=create_input)
        return response.to_dict()

class DealClient:
    def __init__(self, hubspot_client: HubSpot):
        self.client = hubspot_client.crm.deals

    def get_recent(self, limit: int = 10) -> List[Dict]:
        search_req = DealSearchRequest(sorts=[{"propertyName": "lastmodifieddate", "direction": "DESCENDING"}], limit=limit)
        response = self.client.search_api.do_search(public_object_search_request=search_req)
        return [d.to_dict() for d in response.results]

    def create_deal(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        create_input = DealCreateInput(properties=properties)
        response = self.client.basic_api.create(simple_public_object_input_for_create=create_input)
        return response.to_dict()

class TicketClient:
    def __init__(self, hubspot_client: HubSpot):
        self.client = hubspot_client.crm.tickets

    def get_tickets(self, criteria: Literal["default", "Closed"] = "default", limit: int = 50) -> List[Dict]:
        filter_groups = [{"filters": [{"propertyName": "hs_pipeline_stage", "operator": "EQ", "value": "4"}]}] if criteria == "Closed" else []
        search_req = TicketSearchRequest(
            filter_groups=filter_groups,
            sorts=[{"propertyName": "hs_lastmodifieddate", "direction": "DESCENDING"}],
            limit=limit,
            properties=["subject", "content", "hs_pipeline_stage", "createdate", "closedate"]
        )
        response = self.client.search_api.do_search(public_object_search_request=search_req)
        return [t.to_dict() for t in response.results]

class ConversationClient:
    def __init__(self, access_token: str):
        self.access_token = access_token

    def get_recent_conversations(self, limit: int = 10, after: Optional[str] = None) -> Dict[str, Any]:
        url = "https://api.hubapi.com/conversations/v3/conversations/threads"
        params = {"limit": limit, "sort": "-id"}
        if after: params["after"] = after
        headers = {'authorization': f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        for thread in data.get("results", []):
            thread_id = thread.get("id")
            if thread_id:
                messages_data = self._fetch_thread_messages_by_id(thread_id)
                thread['messages'] = [msg for msg in messages_data.get("results", []) if msg.get("type") == "MESSAGE"]
        return data

    def reply_to_thread(self, thread_id: str, message: str) -> Dict[str, Any]:
        actor_id = os.getenv("HUBSPOT_ACTOR_ID")
        if not actor_id: raise ValueError("HUBSPOT_ACTOR_ID is not set.")
        
        messages_response = self._fetch_thread_messages_by_id(thread_id)
        contact_email, channel_id, channel_account_id = self._extract_reply_details(messages_response)

        url = f"https://api.hubapi.com/conversations/v3/conversations/threads/{thread_id}/messages"
        headers = {'authorization': f"Bearer {self.access_token}", 'content-type': 'application/json'}
        payload = {
            "type": "MESSAGE", "text": message,
            "recipients": [{"deliveryIdentifier": {"type": "HS_EMAIL_ADDRESS", "value": contact_email}, "recipientField": "TO"}],
            "senderActorId": actor_id, "channelId": channel_id, "channelAccountId": channel_account_id
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
        
    def _fetch_thread_messages_by_id(self, thread_id: str) -> Dict[str, Any]:
        url = f"https://api.hubapi.com/conversations/v3/conversations/threads/{thread_id}/messages"
        headers = {'authorization': f"Bearer {self.access_token}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def _extract_reply_details(self, messages_response: Dict[str, Any]):
        for msg in messages_response.get("results", []):
            if msg.get("type") == "MESSAGE":
                for sender in msg.get("senders", []):
                    if sender.get("deliveryIdentifier", {}).get("type") == "HS_EMAIL_ADDRESS":
                        return (
                            sender["deliveryIdentifier"]["value"],
                            msg.get("channelId"),
                            msg.get("channelAccountId")
                        )
        raise ValueError("Could not determine reply details from thread messages.")

# --- Main Orchestrator Client ---

class HubSpotClient:
    def __init__(self, access_token: Optional[str] = None):
        token = access_token or os.getenv("HUBSPOT_ACCESS_TOKEN")
        if not token:
            raise ValueError("HUBSPOT_ACCESS_TOKEN is required.")
        
        self.hubspot = HubSpot(access_token=token)
        self.companies = CompanyClient(self.hubspot)
        self.contacts = ContactClient(self.hubspot)
        self.deals = DealClient(self.hubspot)
        self.tickets = TicketClient(self.hubspot)
        self.conversations = ConversationClient(token)