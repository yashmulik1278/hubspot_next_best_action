"""
Handler for deal-related HubSpot operations.
"""
from typing import Any, Dict, List, Optional
import json
import datetime 

import mcp.types as types

from .base_handler import BaseHandler

class DealsHandler(BaseHandler):
    """Handler for deal-related HubSpot tools."""
    
    def __init__(self, hubspot_client, faiss_manager, embedding_model):
        """Initialize the deal handler.
        
        Args:
            hubspot_client: HubSpot client
            faiss_manager: FAISS vector store manager
            embedding_model: Sentence transformer model
        """
        super().__init__(hubspot_client, faiss_manager, embedding_model, "deals_handler")
    
    def get_create_deal_schema(self) -> Dict[str, Any]:
        """Get the input schema for creating a deal.
        
        Returns:
            Schema definition dictionary
        """
        return {
            "type": "object",
            "properties": {
                "dealname": {"type": "string", "description": "Deal name"},
                "amount": {"type": "number", "description": "Deal amount"},
                "properties": {"type": "object", "description": "Additional deal properties"}
            },
            "required": ["dealname", "amount"]
        }
    
    def get_deals_schema(self) -> Dict[str, Any]:
        """Get the input schema for fetching deals.
        
        Returns:
            Schema definition dictionary
        """
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of deals to return (default: 10)"},
                "properties": {"type": "array", "items": {"type": "string"}, "description": "List of properties to include in results"}
            }
        }
    
    def get_deals_by_company_schema(self) -> Dict[str, Any]:
        """Get the input schema for finding deals by company."""
        return {
            "type": "object",
            "properties": {
                "company_id": {"type": "string", "description": "HubSpot company ID"},
                "limit": {"type": "integer", "description": "Maximum number of deals to return (default: 10)"}
            },
            "required": ["company_id"]
        }

    def get_deals_by_contact_schema(self) -> Dict[str, Any]:
        """Get the input schema for finding deals by contact."""
        return {
            "type": "object",
            "properties": {
                "contact_id": {"type": "string", "description": "HubSpot contact ID"},
                "limit": {"type": "integer", "description": "Maximum number of deals to return (default: 10)"}
            },
            "required": ["contact_id"]
        }

    def get_deals_by_company(self, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent]:
        self.validate_required_arguments(arguments, ["company_id"])
        company_id = arguments["company_id"]
        limit = self.get_argument_with_default(arguments, "limit", 10)

        try:
            # Changed from self.hubspot to self.hubspot.deals
            deals = self.hubspot.deals.get_deals_by_company_id(company_id, limit)
            return self.create_text_response(deals)
        except Exception as e:
            return self.create_text_response(f"Error: {str(e)}")

    def get_deals_by_contact(self, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent]:
        self.validate_required_arguments(arguments, ["contact_id"])
        contact_id = arguments["contact_id"]
        limit = self.get_argument_with_default(arguments, "limit", 10)

        try:
            # Changed from self.hubspot to self.hubspot.deals
            deals = self.hubspot.deals.get_deals_by_contact_id(contact_id, limit)
            return self.create_text_response(deals)
        except Exception as e:
            return self.create_text_response(f"Error: {str(e)}")
    
    def create_deal(self, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent]:
        self.validate_required_arguments(arguments, ["dealname", "amount"])
        
        try:
            from hubspot.crm.deals import PublicObjectSearchRequest
            
            dealname = arguments["dealname"]
            amount = arguments["amount"]
            
            # Search for existing deals with same name
            search_request = PublicObjectSearchRequest(
                filter_groups=[{
                    "filters": [
                        {
                            "propertyName": "dealname",
                            "operator": "EQ",
                            "value": dealname
                        }
                    ]
                }]
            )
            
            search_response = self.hubspot.client.crm.deals.search_api.do_search(
                public_object_search_request=search_request
            )
            
            if search_response.total > 0:
                # Deal already exists
                return self.create_text_response(
                    f"Deal already exists: {search_response.results[0].to_dict()}"
                )
            
            # If no existing deal found, proceed with creation
            properties = {
                "dealname": dealname,
                "amount": amount
            }
            
            # Add any additional properties
            if "properties" in arguments:
                properties.update(arguments["properties"])
            
            # Create deal using SimplePublicObjectInputForCreate
            from hubspot.crm.deals import SimplePublicObjectInputForCreate
            
            simple_public_object_input = SimplePublicObjectInputForCreate(
                properties=properties
            )
            
            api_response = self.hubspot.client.crm.deals.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input
            )
            return self.create_text_response(str(api_response.to_dict()))
                
        except Exception as e:
            return self.create_text_response(f"Error: {str(e)}")
    
    def get_deals(self, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent]:
        limit = self.get_argument_with_default(arguments, "limit", 10)
        properties = self.get_argument_with_default(arguments, "properties", None)
    
        limit = int(limit) if limit is not None else 10
    
        try:
            # Get deals from HubSpot
            deals_list = self.hubspot.client.crm.deals.get_all(
                limit=limit, 
                properties=properties
         )
    
            # Convert deals to serializable format
            def convert_datetime(obj):
                """Recursively convert datetime objects to ISO strings"""
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                elif isinstance(obj, dict):
                    return {k: convert_datetime(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_datetime(item) for item in obj]
                return obj
    
            results = [convert_datetime(deal.to_dict()) for deal in deals_list]
        
            # Store in FAISS
            metadata_extras = {"limit": limit, "properties": properties}
            self.store_in_faiss_safely(results, "deal", metadata_extras)
        
            return self.create_text_response(results)
        
        except Exception as e:
            return self.create_text_response(f"Error fetching deals: {str(e)}")