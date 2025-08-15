"""
Storage handling for HubSpot conversation threads.
"""
import json
import logging
import pathlib
from typing import Any, Dict, Union

logger = logging.getLogger('mcp_hubspot_client.storage')

class ThreadStorage:
    """Storage handler for conversation threads."""
    
    def __init__(self, storage_dir: Union[str, pathlib.Path]):
        # Ensure storage directory exists
        self.storage_dir = pathlib.Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Where we’ll write our thread cache
        self.threads_file = self.storage_dir / "threads.json"

        # Load any existing cache into memory
        self.threads_cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """Load conversation threads from cache file if it exists."""
        try:
            if self.threads_file.exists():
                with open(self.threads_file, "r") as f:
                    return json.load(f)
            return {"results": [], "paging": {"next": {"after": None}}}
        except Exception as e:
            logger.error(f"Error loading threads cache: {str(e)}")
            return {"results": [], "paging": {"next": {"after": None}}}

    def save_cache(self, threads_data: Dict[str, Any]) -> None:
        """Save conversation threads to cache file."""
        try:
            with open(self.threads_file, "w") as f:
                json.dump(threads_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving threads cache: {str(e)}")

    def get_cached_threads(self) -> Dict[str, Any]:
        """Get the current cached threads."""
        return self.threads_cache

    def update_cache(self, threads_data: Dict[str, Any]) -> None:
        """Update the cache with new thread data."""
        self.threads_cache = threads_data
        self.save_cache(threads_data)

class HubSpotClient:
    def __init__(self, access_token: str, storage_dir: str):
        self.client = HubSpot(access_token=access_token)
        self.deals = DealClient(self.client, access_token)
        self.conversations = ConversationClient(
            hubspot_client=self.client,
            access_token=access_token,
            thread_storage=ThreadStorage(storage_dir=pathlib.Path(storage_dir)))  # Pass storage_dir
        
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load conversation threads from cache file if it exists.
        
        Returns:
            Thread data or empty structure
        """
        try:
            if self.threads_file.exists():
                with open(self.threads_file, "r") as f:
                    return json.load(f)
            return {"results": [], "paging": {"next": {"after": None}}}
        except Exception as e:
            logger.error(f"Error loading threads cache: {str(e)}")
            return {"results": [], "paging": {"next": {"after": None}}}
    
    def save_cache(self, threads_data: Dict[str, Any]) -> None:
        """Save conversation threads to cache file.
        
        Args:
            threads_data: Thread data to save
        """
        try:
            with open(self.threads_file, "w") as f:
                json.dump(threads_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving threads cache: {str(e)}")
    
    def get_cached_threads(self) -> Dict[str, Any]:
        """Get the current cached threads.
        
        Returns:
            Cached thread data
        """
        return self.threads_cache
    
    def update_cache(self, threads_data: Dict[str, Any]) -> None:
        """Update the cache with new thread data.
        
        Args:
            threads_data: New thread data
        """
        self.threads_cache = threads_data
        self.save_cache(threads_data)
