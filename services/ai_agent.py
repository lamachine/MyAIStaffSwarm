"""AI Agent Service with Memory Management.

This module provides the core AI Agent functionality with:
- PostgreSQL-backed conversation memory
- Multiple LLM provider support
- Context management
- User state management
- FAISS vector store for document knowledge
"""

from typing import Dict, List, Any, Optional
import logging
import asyncio
from datetime import datetime
import uuid
import sys
from pathlib import Path
import json

# Add parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))
from services.db_service import DatabaseService
from services.llm_service import LLMService
from tools.user_state import get_user_state
from services.document_ingestion.vector_store.faiss_store import FaissVectorStore
from services.document_ingestion.types import ProcessedDocument

class AIAgent:
    """Main AI Agent class that handles interactions and memory"""
    
    def __init__(self, llm_provider: str = None):
        self.logger = logging.getLogger(__name__)
        self.db_service = DatabaseService()
        self.llm_service = LLMService(llm_provider)
        self.session_id = str(uuid.uuid4())
        self.user_state = get_user_state()
        
        # Initialize vector store with standard embedding dimension
        self.vector_store = None  # Will initialize after getting embedding dimension
        
    async def initialize(self) -> bool:
        """Initialize the agent and its services"""
        try:
            # Initialize database service
            self.logger.debug("Initializing database service...")
            if not await self.db_service.initialize():
                self.logger.error("Failed to initialize database service")
                return False
                
            # Initialize user state
            self.logger.debug("Loading user state...")
            await self.user_state.load_state(self.session_id)
            
            # Get embedding dimension by testing with a sample text
            self.logger.debug("Getting embedding dimension...")
            test_embedding = await self.llm_service.get_embedding("test")
            embedding_dim = len(test_embedding)
            self.logger.info(f"Using embedding dimension: {embedding_dim}")
            
            # Initialize vector store with correct dimension
            self.vector_store = FaissVectorStore({
                "dimension": embedding_dim,
                "index_type": "Flat",
                "use_gpu": True
            })
            
            # Initialize vector store
            self.logger.debug("Connecting to vector store...")
            await self.vector_store.connect()
            
            self.logger.info("AI Agent initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Agent: {str(e)}")
            return False
            
    async def search_relevant_documents(self, query: str, num_results: int = 3) -> List[Dict[str, Any]]:
        """Search for documents relevant to the query."""
        try:
            # Get query embedding from LLM service
            query_embedding = await self.llm_service.get_embedding(query)
            
            # Search vector store
            results = await self.vector_store.search_similar(
                query=query_embedding,
                num_results=num_results
            )
            
            # Get full documents from database
            documents = []
            for result in results:
                doc = await self.db_service.get_document(result["doc_id"])
                if doc:
                    documents.append({
                        **doc,
                        "relevance_score": result["score"]
                    })
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Error searching documents: {str(e)}")
            return []
    
    async def process_message(self, 
                            message: str, 
                            metadata: Optional[Dict[str, Any]] = None,
                            system_prompt: Optional[str] = None,
                            user_info: Optional[str] = None) -> Dict[str, Any]:
        """Process a user message and return a response"""
        try:
            # Update user state if user_info provided
            if user_info:
                self.logger.debug("Updating user state from prompt...")
                await self.user_state.update_from_prompt(self.session_id, user_info)
            
            # Get current user state
            state = await self.user_state.load_state(self.session_id)
            
            # Add user state to metadata
            if metadata is None:
                metadata = {}
            metadata["user_state"] = state
            
            # Search for relevant documents
            self.logger.debug("Searching for relevant documents...")
            relevant_docs = await self.search_relevant_documents(message)
            
            # Format document context
            doc_context = ""
            if relevant_docs:
                doc_context = "\nRelevant information from knowledge base:\n"
                for doc in relevant_docs:
                    doc_context += f"- {doc['content']}\n"
                    doc_context += f"  (Source: {doc['metadata'].get('source', 'Unknown')}, "
                    doc_context += f"Relevance: {doc['relevance_score']:.2f})\n"
            
            # Store user message
            await self.db_service.store_message(
                role="user",
                content=message,
                metadata=metadata,
                session_id=self.session_id
            )
            
            # Get conversation history
            history = await self.db_service.get_recent_messages(limit=10)
            
            # Generate response using LLM
            llm_response = await self.llm_service.generate_response(
                prompt=message,
                history=history,
                system_prompt=system_prompt,
                additional_context=doc_context if doc_context else None
            )
            
            if "error" in llm_response:
                raise Exception(llm_response["error"])
            
            # Prepare response with metadata
            response = {
                "content": llm_response["content"],
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "model": llm_response["model"],
                    "provider": llm_response["provider"],
                    "user_state": state,
                    "relevant_docs": [
                        {
                            "id": doc["id"],
                            "title": doc["title"],
                            "relevance": doc["relevance_score"]
                        } for doc in relevant_docs
                    ] if relevant_docs else []
                }
            }
            
            # Store assistant response
            await self.db_service.store_message(
                role="assistant",
                content=response["content"],
                metadata=response["metadata"],
                session_id=self.session_id
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return {
                "error": str(e),
                "metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id
                }
            }
    
    async def get_session_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history for the current session"""
        try:
            return await self.db_service.get_recent_messages()
        except Exception as e:
            self.logger.error(f"Error retrieving session history: {str(e)}")
            return []
            
    async def update_user_state(self, field: str, value: Any) -> str:
        """Update a field in the user state"""
        try:
            return await self.user_state.update_field(self.session_id, field, value)
        except Exception as e:
            self.logger.error(f"Error updating user state: {str(e)}")
            return f"Failed to update {field}: {str(e)}"

# Direct testing
if __name__ == "__main__":
    async def run_tests():
        print("\nTesting AI Agent with Multiple Providers:")
        
        # Test each provider
        providers = ['ollama']  # Start with Ollama since we have it working
        
        # Example user info from prompt
        user_info = """
        The user's OS version is win32 10.0.22631. 
        The absolute path of the user's workspace is /c%3A/Users/Owner/Documents/GitHub/cursor_test/LTB2/Email_Assist/Email_assist_current. 
        The user's shell is C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe.
        """
        
        # Test document for knowledge base
        test_doc = {
            "id": "test123",
            "title": "Python Installation Guide",
            "content": """
            Installing Python on Windows:
            1. Download Python from python.org
            2. Run the installer with 'Add to PATH' checked
            3. Verify installation with 'python --version'
            4. Install pip if not included
            5. Create virtual environments using 'python -m venv venv'
            """,
            "metadata": {
                "source": "test_docs",
                "type": "guide"
            }
        }
        
        for provider in providers:
            print(f"\n{'='*20} Testing {provider.upper()} {'='*20}")
            agent = None
            
            try:
                # Initialize agent
                print(f"\n1. Testing {provider} initialization...")
                agent = AIAgent(llm_provider=provider)
                initialized = await agent.initialize()
                if not initialized:
                    print(f"❌ {provider} initialization failed")
                    continue
                print(f"✓ {provider} initialized successfully")
                
                # Store test document
                print("\n2. Testing document storage...")
                doc_embedding = await agent.llm_service.get_embedding(test_doc["content"])
                
                processed_doc = ProcessedDocument(
                    doc_id=test_doc["id"],
                    chunks=[test_doc["content"]],
                    embeddings=[doc_embedding],
                    metadata=test_doc["metadata"]
                )
                
                await agent.vector_store.store_document(processed_doc)
                print("✓ Test document stored")
                
                # Test document-aware response
                print("\n3. Testing document-aware response...")
                test_query = "How do I verify my Python installation?"
                response = await agent.process_message(
                    message=test_query,
                    metadata={"test": True, "provider": provider},
                    system_prompt="You are a helpful assistant. Use the provided context to answer questions accurately.",
                    user_info=user_info
                )
                
                if "error" in response:
                    print(f"❌ Document-aware response failed: {response['error']}")
                else:
                    print("✓ Document-aware response generated")
                    print("\nQuery:", test_query)
                    print("\nResponse:", response["content"])
                    print("\nMetadata:", json.dumps(response["metadata"], indent=2))
                    
                # Test non-document query
                print("\n4. Testing general response...")
                test_query = "What is the capital of France?"
                response = await agent.process_message(
                    message=test_query,
                    metadata={"test": True, "provider": provider},
                    system_prompt="You are a helpful assistant. Keep answers concise.",
                    user_info=user_info
                )
                
                if "error" in response:
                    print(f"❌ General response failed: {response['error']}")
                else:
                    print("✓ General response generated")
                    print("\nQuery:", test_query)
                    print("\nResponse:", response["content"])
                    
                print(f"\n✨ All {provider} tests completed successfully!")
                
            except Exception as e:
                print(f"\n❌ {provider} test failed: {str(e)}")
                import traceback
                print("\nFull traceback:")
                print(traceback.format_exc())
            finally:
                if agent:
                    try:
                        if hasattr(agent, 'db_service') and agent.db_service.pool:
                            await agent.db_service.pool.close()
                        if hasattr(agent, 'vector_store'):
                            await agent.vector_store.disconnect()
                    except Exception as cleanup_error:
                        print(f"\nWarning: Cleanup error: {str(cleanup_error)}")
    
    # Run the tests
    asyncio.run(run_tests()) 