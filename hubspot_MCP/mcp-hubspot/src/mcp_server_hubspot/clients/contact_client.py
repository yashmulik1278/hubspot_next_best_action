"""
Client for HubSpot contact-related operations.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from hubspot import HubSpot
from hubspot.crm.contacts import PublicObjectSearchRequest, SimplePublicObjectInputForCreate
from hubspot.crm.contacts.exceptions import ApiException

from ..core.formatters import convert_datetime_fields
from ..core.error_handler import handle_hubspot_errors

logger = logging.getLogger('mcp_hubspot_client.contact')

class ContactClient:
    """Client for HubSpot contact-related operations."""
    
    def __init__(self, hubspot_client: HubSpot, access_token: str):
        self.client = hubspot_client
        self.access_token = access_token
    
    @handle_hubspot_errors
    def get_recent(self, limit: int = 10) -> str:
        search_request = self._create_contact_search_request(limit)
        search_response = self.client.crm.contacts.search_api.do_search(
            public_object_search_request=search_request
        )
        
        contacts_dict = [contact.to_dict() for contact in search_response.results]
        converted_contacts = convert_datetime_fields(contacts_dict)
        return json.dumps(converted_contacts)
    
    def _create_contact_search_request(self, limit: int) -> PublicObjectSearchRequest:
        return PublicObjectSearchRequest(
            sorts=[{
                "propertyName": "lastmodifieddate",
                "direction": "DESCENDING"
            }],
            limit=limit,
            properties=["firstname", "lastname", "email", "phone", "company", 
                       "hs_lastmodifieddate", "lastmodifieddate"]
        )
    
    @handle_hubspot_errors
    def create_contact(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        # Check if contact already exists
        if "firstname" in properties and "lastname" in properties:
            existing_contact = self._find_existing_contact(
                properties["firstname"], 
                properties["lastname"],
                properties.get("company")
            )
            
            if existing_contact:
                return {"already_exists": True, "contact": existing_contact}
        
        # Create contact
        simple_public_object_input = SimplePublicObjectInputForCreate(
            properties=properties
        )
        
        api_response = self.client.crm.contacts.basic_api.create(
            simple_public_object_input_for_create=simple_public_object_input
        )
        
        return api_response.to_dict()
    
    def _find_existing_contact(
        self, 
        firstname: str, 
        lastname: str, 
        company: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        filter_group = {
            "filters": [
                {
                    "propertyName": "firstname",
                    "operator": "EQ",
                    "value": firstname
                },
                {
                    "propertyName": "lastname",
                    "operator": "EQ",
                    "value": lastname
                }
            ]
        }
        
        # Add company filter if provided
        if company:
            filter_group["filters"].append({
                "propertyName": "company",
                "operator": "EQ",
                "value": company
            })
        
        search_request = PublicObjectSearchRequest(
            filter_groups=[filter_group]
        )
        
        search_response = self.client.crm.contacts.search_api.do_search(
            public_object_search_request=search_request
        )
        
        if search_response.total > 0:
            return search_response.results[0].to_dict()
            
        return None
