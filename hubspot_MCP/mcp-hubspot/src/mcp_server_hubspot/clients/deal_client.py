"""
Client for HubSpot deal-related operations.
"""
import json
import logging 
from typing import Any, Dict, List, Optional

from hubspot import HubSpot
from hubspot.crm.deals import (
    PublicObjectSearchRequest,
    SimplePublicObjectInputForCreate
)
from hubspot.crm.contacts.exceptions import ApiException

from ..core.formatters import convert_datetime_fields
from ..core.error_handler import handle_hubspot_errors

logger = logging.getLogger('mcp_hubspot_client.deal')

class DealClient:
    """Client for HubSpot deal-related operations."""
    
    def __init__(self, hubspot_client: HubSpot, access_token: str):
        self.client = hubspot_client
        self.access_token = access_token
    
    @handle_hubspot_errors
    def create_deal(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        # Check if deal already exists if possible (based on dealname or other unique property)
        # This would require a search implementation similar to contact/company creation
        # For now, just create the deal without existence check
        
        # Create deal
        simple_public_object_input = SimplePublicObjectInputForCreate(
            properties=properties
        )
        
        api_response = self.client.crm.deals.basic_api.create(
            simple_public_object_input_for_create=simple_public_object_input
        )
        
        return api_response.to_dict()
    
    @handle_hubspot_errors
    def get_recent_deals(self, limit: int = 10) -> str:
        search_request = self._create_deal_search_request(limit)
        search_response = self.client.crm.deals.search_api.do_search(
            public_object_search_request=search_request
        )
        
        deals_dict = [deal.to_dict() for deal in search_response.results]
        converted_deals = convert_datetime_fields(deals_dict)
        return json.dumps(converted_deals)
    
    def _create_deal_search_request(self, limit: int) -> PublicObjectSearchRequest:
        return PublicObjectSearchRequest(
            sorts=[{
                "propertyName": "lastmodifieddate",
                "direction": "DESCENDING"
            }],
            limit=limit,
            properties=["dealname", "amount", "closedate", "dealstage", "pipeline", "hs_lastmodifieddate"]
        )
    
    @handle_hubspot_errors
    def get_deal(self, deal_id: str) -> Dict[str, Any]:
        api_response = self.client.crm.deals.basic_api.get_by_id(deal_id)
        return api_response.to_dict()
    
    @handle_hubspot_errors
    def get_deals_by_company_id(self, company_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get deals associated with a specific company."""
        try:
            # Get deals associated with the company
            associated_deals = self.client.crm.associations.v4.basic_api.get_page(
                object_type="companies",
                object_id=company_id,
                to_object_type="deals",
                limit=limit
            )

            deal_ids = [association.to_object_id for association in associated_deals.results]

            if not deal_ids:
                logger.info(f"No deals found for company {company_id}")
                return []

            # Fetch deal details
            deals = []
            for deal_id in deal_ids:
                deal = self.client.crm.deals.basic_api.get_by_id(deal_id)
                deals.append(deal.to_dict())

            # Convert datetime fields
            converted_deals = convert_datetime_fields(deals)
            return converted_deals

        except Exception as e:
            logger.error(f"Error retrieving deals for company {company_id}: {str(e)}")
            return []

    @handle_hubspot_errors
    def get_deals_by_contact_id(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get deals associated with a specific contact."""
        try:
            # Get deals associated with the contact
            associated_deals = self.client.crm.associations.v4.basic_api.get_page(
                object_type="contacts",
                object_id=contact_id,
                to_object_type="deals",
                limit=limit
            )

            deal_ids = [association.to_object_id for association in associated_deals.results]

            if not deal_ids:
                logger.info(f"No deals found for contact {contact_id}")
                return []

            # Fetch deal details
            deals = []
            for deal_id in deal_ids:
                deal = self.client.crm.deals.basic_api.get_by_id(deal_id)
                deals.append(deal.to_dict())

            # Convert datetime fields
            converted_deals = convert_datetime_fields(deals)
            return converted_deals

        except Exception as e:
            logger.error(f"Error retrieving deals for contact {contact_id}: {str(e)}")
            return []