import asyncio
import logging
import os
import json
from typing import Any
import datetime # 1. Add this new import

from dotenv import load_dotenv
import mcp.server.stdio as stdio
from mcp.server import Server
import mcp.types as types
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions

from hubspot_clients import HubSpotClient

# Basic logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 2. Add this helper function to handle datetime objects
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


async def main():
    """Initializes clients and runs the MCP server with all tools."""
    load_dotenv()
    logging.info("Starting HubSpot MCP server with full toolset...")

    hubspot = HubSpotClient()
    server = Server("hubspot-mcp")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        # Schemas for all tools
        return [
            # Company Tools
            types.Tool(name="hubspot_get_active_companies", description="Get most recently active companies.",
                       inputSchema={"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}),
            # Contact Tools
            types.Tool(name="hubspot_get_active_contacts", description="Get most recently active contacts.",
                       inputSchema={"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}),
            types.Tool(name="hubspot_create_contact", description="Create a new contact.",
                       inputSchema={"type": "object", "properties": {
                           "firstname": {"type": "string"}, "lastname": {"type": "string"}, "email": {"type": "string"}
                       }, "required": ["firstname", "lastname"]}),
            # Deal Tools
            types.Tool(name="hubspot_get_recent_deals", description="Get most recently created or modified deals.",
                       inputSchema={"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}),
            types.Tool(name="hubspot_create_deal", description="Create a new deal.",
                       inputSchema={"type": "object", "properties": {
                           "dealname": {"type": "string"}, "amount": {"type": "string"}
                       }, "required": ["dealname", "amount"]}),
            # Ticket Tools
            types.Tool(name="hubspot_get_tickets", description="Get tickets based on criteria.",
                       inputSchema={"type": "object", "properties": {
                           "criteria": {"type": "string", "enum": ["default", "Closed"], "default": "default"},
                           "limit": {"type": "integer", "default": 50}
                       }}),
            # Conversation Tools
            types.Tool(name="hubspot_get_recent_conversations", description="Get recent conversation threads.",
                       inputSchema={"type": "object", "properties": {"limit": {"type": "integer", "default": 10}}}),
            types.Tool(name="hubspot_reply_to_thread", description="Reply to a conversation thread.",
                       inputSchema={"type": "object", "properties": {
                           "thread_id": {"type": "string"}, "message": {"type": "string"}
                       }, "required": ["thread_id", "message"]}),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        logging.info(f"Tool called: {name} with args: {arguments}")
        try:
            # Routing for all tools
            if name == "hubspot_get_active_companies":
                result = hubspot.companies.get_recent(**arguments)
            elif name == "hubspot_get_active_contacts":
                result = hubspot.contacts.get_recent(**arguments)
            elif name == "hubspot_create_contact":
                result = hubspot.contacts.create_contact(properties=arguments)
            elif name == "hubspot_get_recent_deals":
                result = hubspot.deals.get_recent(**arguments)
            elif name == "hubspot_create_deal":
                result = hubspot.deals.create_deal(properties=arguments)
            elif name == "hubspot_get_tickets":
                result = hubspot.tickets.get_tickets(**arguments)
            elif name == "hubspot_get_recent_conversations":
                result = hubspot.conversations.get_recent_conversations(**arguments)
            elif name == "hubspot_reply_to_thread":
                result = hubspot.conversations.reply_to_thread(**arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

            # 3. Use the helper function in json.dumps
            json_string = json.dumps(result, indent=2, default=json_serial)
            return [types.TextContent(type="text", text=json_string)]

        except Exception as e:
            logging.error(f"Error calling tool {name}: {e}", exc_info=True)
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    initialization_options = InitializationOptions(
        server_name="hubspot-mcp",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={}
        )
    )

    async with stdio.stdio_server() as (reader, writer):
        await server.run(reader, writer, initialization_options)

if __name__ == "__main__":
    asyncio.run(main())