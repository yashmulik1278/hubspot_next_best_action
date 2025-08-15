"""HubSpot integration for MCP."""

import asyncio
import logging
import os
from typing import Optional
from . import server
from .hubspot_client import HubSpotClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger('mcp_hubspot')

async def main(access_token: Optional[str] = None):
    """Run the HubSpot MCP server."""
    # Set hardcoded storage directory
    os.environ["HUBSPOT_STORAGE_DIR"] = "/storage"
    
    # Call the server main function
    await server.main(access_token)

def run_main():
    """Synchronous entry point for the package."""
    import argparse
    
    # Set up command line argument parser for access token only
    parser = argparse.ArgumentParser(description="Run the HubSpot MCP server")
    parser.add_argument(
        "--access-token",
        help="HubSpot API access token (overrides HUBSPOT_ACCESS_TOKEN environment variable)",
    )
    
    args = parser.parse_args()
    
    # Run the main function through asyncio
    asyncio.run(main(access_token=args.access_token))

if __name__ == "__main__":
    run_main()

# Expose important items at package level
__all__ = ["main", "run_main", "server", "HubSpotClient"] 