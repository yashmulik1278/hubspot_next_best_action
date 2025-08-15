"""
Handler for conversation-related HubSpot operations.
"""
from typing import Any, Dict, List, Optional
import json

import mcp.types as types

from .base_handler import BaseHandler

class ConversationHandler(BaseHandler):
    """Handler for conversation-related HubSpot tools."""
    
    def __init__(self, hubspot_client, faiss_manager, embedding_model):
        super().__init__(hubspot_client, faiss_manager, embedding_model, "conversation_handler")
    
    def get_recent_conversations_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of threads to return (default: 10)"},
                "after": {"type": "string", "description": "Pagination token"},
                "refresh_cache": {"type": "boolean", "description": "Whether to refresh the threads cache (default: false)"}
            },
        }
    
    def get_reply_to_thread_schema(self) -> Dict[str, Any]:
        """Get the input schema for replying to a conversation thread."""
        return {
            "type": "object",
            "properties": {
                "thread_id": {"type": "string", "description": "HubSpot thread ID"},
                "message": {"type": "string", "description": "Message to reply with"}
            },
            "required": ["thread_id", "message"]
        }

    def reply_to_thread(self, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent]:
        self.validate_required_arguments(arguments, ["thread_id", "message"])
        thread_id = arguments["thread_id"]
        message = arguments["message"]
    
        try:
            # Changed from self.hubspot to self.hubspot.conversations
            response = self.hubspot.conversations.reply_to_thread(thread_id, message)
            print(f"Reply payload: {json.dumps(response, indent=2)}")
            return self.create_text_response(response)
        except Exception as e:
            return self.create_text_response(f"Error: {str(e)}")
    
    def get_recent_conversations(self, arguments: Optional[Dict[str, Any]]) -> List[types.TextContent]:
        # Extract parameters with defaults if not provided
        limit = self.get_argument_with_default(arguments, "limit", 10)
        after = self.get_argument_with_default(arguments, "after", None)
        refresh_cache = self.get_argument_with_default(arguments, "refresh_cache", False)
        
        # Ensure limit is an integer
        limit = int(limit) if limit is not None else 10
        
        # Get recent conversations with pagination
        self.logger.debug(f"Getting recent conversations with limit={limit}, after={after}, refresh_cache={refresh_cache}")
        results = self.hubspot.get_recent_conversations(limit=limit, after=after, refresh_cache=refresh_cache)
        
        # Store in FAISS for future reference
        self._store_conversations_in_faiss(results, limit, after)
        
        # Truncate message text for API response (while preserving full text in FAISS)
        truncated_results = self._truncate_conversation_messages(results)
        
        # Return truncated results as JSON
        return self.create_text_response(truncated_results)
    
    def _store_conversations_in_faiss(
        self, 
        results: Dict[str, Any], 
        limit: int, 
        after: Optional[str]
    ) -> None:
        try:
            data = results.get("results", [])
            if data:
                # Store each thread individually in FAISS
                self.logger.debug(f"Preparing to store {len(data)} conversation threads in FAISS individually")
                for i, thread in enumerate(data):
                    thread_metadata = {
                        "thread_id": thread.get("id", f"unknown_{i}"),
                        "limit": limit,
                        "after": after
                    }
                    self.logger.debug(f"Storing thread {i+1}/{len(data)} with ID {thread_metadata['thread_id']}")
                    
                    # Store single thread as a list with one item to maintain format compatibility
                    self.store_in_faiss_safely(
                        data=[thread],  # Store as single-item list
                        data_type="conversation_thread",
                        metadata_extras=thread_metadata
                    )
        except Exception as e:
            self.logger.error(f"Error storing conversations in FAISS: {str(e)}", exc_info=True)
    
    def _truncate_conversation_messages(self, results: Dict[str, Any]) -> Dict[str, Any]:
        truncated_results = results.copy()
        for thread in truncated_results.get("results", []):
            for message in thread.get("messages", []):
                if "text" in message:
                    message["text"] = message["text"][:200] if message["text"] else ""
                if "rich_text" in message:
                    message["rich_text"] = message["rich_text"][:200] if message["rich_text"] else ""
        
        return truncated_results
    

