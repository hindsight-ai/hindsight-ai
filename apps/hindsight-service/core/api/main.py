import logging # Moved to top
import os
from fastapi import FastAPI, Header, Depends, HTTPException, status, APIRouter
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import math # Import math for ceil

# Configure logging (Moved to top)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables are expected to be set by the deployment environment (e.g., Kubernetes)
# For local development, ensure these are set in your shell or via a tool like docker-compose.

from core.db import models, schemas, crud
from core.db.database import engine, get_db
from core.pruning.pruning_service import get_pruning_service
from core.pruning.compression_service import get_compression_service
from core.search.search_service import SearchService

# models.Base.metadata.create_all(bind=engine) # Removed: Database schema is now managed by Alembic migrations.

app = FastAPI(
    title="Intelligent AI Agent Memory Service",
    description="API for managing AI agent memories, including creation, retrieval, and feedback.",
    version="1.0.0",
)

origins = [
    "http://localhost",
    "http://localhost:3000", # React frontend
    "http://localhost:3001", # Allow your frontend to access the API
    "http://localhost:8000", # FastAPI backend
    "https://app.hindsight-ai.com",
    "https://api.hindsight-ai.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

@router.post("/agents/", response_model=schemas.Agent, status_code=status.HTTP_201_CREATED)
def create_agent_endpoint(agent: schemas.AgentCreate, db: Session = Depends(get_db)):
    db_agent = crud.get_agent_by_name(db, agent_name=agent.agent_name)
    if db_agent:
        raise HTTPException(status_code=400, detail="Agent with this name already exists")
    return crud.create_agent(db=db, agent=agent)

@router.get("/agents/", response_model=List[schemas.Agent])
def get_all_agents_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    agents = crud.get_agents(db, skip=skip, limit=limit)
    return agents

@router.get("/agents/{agent_id}", response_model=schemas.Agent)
def get_agent_endpoint(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    db_agent = crud.get_agent(db, agent_id=agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@router.get("/agents/search/", response_model=List[schemas.Agent])
def search_agents_endpoint(query: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    agents = crud.search_agents(db, query=query, skip=skip, limit=limit)
    return agents

@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_endpoint(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    success = crud.delete_agent(db, agent_id=agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}

@router.get("/memory-blocks/", response_model=schemas.PaginatedMemoryBlocks)
def get_all_memory_blocks_endpoint(
    agent_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    search_query: Optional[str] = None,
    search_type: Optional[str] = "basic",  # basic, fulltext, semantic, hybrid, enhanced
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_feedback_score: Optional[str] = None,
    max_feedback_score: Optional[str] = None,
    min_retrieval_count: Optional[str] = None,
    max_retrieval_count: Optional[str] = None,
    keywords: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    skip: int = 0,
    limit: int = 50,
    include_archived: Optional[bool] = False,
    # Advanced search parameters
    min_score: Optional[float] = None,  # Minimum relevance score threshold
    similarity_threshold: Optional[float] = None,  # For semantic search
    fulltext_weight: Optional[float] = None,  # For hybrid search
    semantic_weight: Optional[float] = None,  # For hybrid search
    min_combined_score: Optional[float] = None,  # For hybrid search
    db: Session = Depends(get_db)
):
    """
    Retrieve all memory blocks with advanced filtering, searching, and sorting capabilities.
    Supports multiple search types: basic, fulltext (BM25), semantic, hybrid, and enhanced.
    """
    logger.info(f"Received query parameters:")
    logger.info(f"  agent_id: {agent_id} (type: {type(agent_id)})")
    logger.info(f"  conversation_id: {conversation_id} (type: {type(conversation_id)})")
    logger.info(f"  search_query: {search_query} (type: {type(search_query)})")
    logger.info(f"  search_type: {search_type} (type: {type(search_type)})")
    logger.info(f"  skip: {skip} (type: {type(skip)})")
    logger.info(f"  limit: {limit} (type: {type(limit)})")

    # Process UUID parameters
    processed_agent_id: Optional[uuid.UUID] = None
    if agent_id:
        try:
            processed_agent_id = uuid.UUID(agent_id)
        except ValueError:
            if agent_id != "":
                logger.error(f"Invalid UUID format for agent_id: '{agent_id}'")
                raise HTTPException(status_code=422, detail="Invalid UUID format for agent_id.")
            processed_agent_id = None

    processed_conversation_id: Optional[uuid.UUID] = None
    if conversation_id:
        try:
            processed_conversation_id = uuid.UUID(conversation_id)
        except ValueError:
            if conversation_id != "":
                logger.error(f"Invalid UUID format for conversation_id: '{conversation_id}'")
                raise HTTPException(status_code=422, detail="Invalid UUID format for conversation_id.")
            processed_conversation_id = None

    # Process datetime parameters
    processed_start_date: Optional[datetime] = None
    if start_date and start_date != "":
        try:
            processed_start_date = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid datetime format for start_date. Expected ISO 8601.")

    processed_end_date: Optional[datetime] = None
    if end_date and end_date != "":
        try:
            processed_end_date = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid datetime format for end_date. Expected ISO 8601.")

    # Process integer parameters
    processed_min_feedback_score: Optional[int] = None
    if min_feedback_score:
        try:
            processed_min_feedback_score = int(min_feedback_score)
        except ValueError:
            if min_feedback_score != "":
                raise HTTPException(status_code=422, detail="Invalid integer format for min_feedback_score.")

    processed_max_feedback_score: Optional[int] = None
    if max_feedback_score:
        try:
            processed_max_feedback_score = int(max_feedback_score)
        except ValueError:
            if max_feedback_score != "":
                raise HTTPException(status_code=422, detail="Invalid integer format for max_feedback_score.")

    processed_min_retrieval_count: Optional[int] = None
    if min_retrieval_count:
        try:
            processed_min_retrieval_count = int(min_retrieval_count)
        except ValueError:
            if min_retrieval_count != "":
                raise HTTPException(status_code=422, detail="Invalid integer format for min_retrieval_count.")

    processed_max_retrieval_count: Optional[int] = None
    if max_retrieval_count:
        try:
            processed_max_retrieval_count = int(max_retrieval_count)
        except ValueError:
            if max_retrieval_count != "":
                raise HTTPException(status_code=422, detail="Invalid integer format for max_retrieval_count.")

    # Process keywords string into a list of UUIDs
    processed_keyword_ids: Optional[List[uuid.UUID]] = None
    if keywords and keywords != "":
        try:
            processed_keyword_ids = [uuid.UUID(kw.strip()) for kw in keywords.split(',') if kw.strip()]
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid UUID format in keywords parameter.")

    # Clean up parameters
    search_query = search_query if search_query else None
    sort_by = sort_by if sort_by else None
    sort_order = sort_order if sort_order else "asc"

    # Handle different search types
    if search_query and search_type in ["fulltext", "semantic", "hybrid"]:
        # Use advanced search service
        search_service = SearchService()
        
        try:
            if search_type == "fulltext":
                # Set defaults for fulltext search
                min_score_val = min_score if min_score is not None else 0.1
                
                results, metadata = search_service.search_memory_blocks_fulltext(
                    db=db,
                    query=search_query,
                    agent_id=processed_agent_id,
                    conversation_id=processed_conversation_id,
                    limit=skip + limit,  # Get extra to handle pagination
                    min_score=min_score_val,
                    include_archived=include_archived or False
                )
                
                # Apply pagination manually since search doesn't support skip
                paginated_results = results[skip:skip + limit]
                total_items = len(results)
                
            elif search_type == "semantic":
                # Set defaults for semantic search
                similarity_threshold_val = similarity_threshold if similarity_threshold is not None else 0.7
                
                results, metadata = search_service.search_memory_blocks_semantic(
                    db=db,
                    query=search_query,
                    agent_id=processed_agent_id,
                    conversation_id=processed_conversation_id,
                    limit=skip + limit,
                    similarity_threshold=similarity_threshold_val,
                    include_archived=include_archived or False
                )
                
                paginated_results = results[skip:skip + limit]
                total_items = len(results)
                
            elif search_type == "hybrid":
                # Set defaults for hybrid search
                fulltext_weight_val = fulltext_weight if fulltext_weight is not None else 0.7
                semantic_weight_val = semantic_weight if semantic_weight is not None else 0.3
                min_combined_score_val = min_combined_score if min_combined_score is not None else 0.1
                
                results, metadata = search_service.search_memory_blocks_hybrid(
                    db=db,
                    query=search_query,
                    agent_id=processed_agent_id,
                    conversation_id=processed_conversation_id,
                    limit=skip + limit,
                    fulltext_weight=fulltext_weight_val,
                    semantic_weight=semantic_weight_val,
                    min_combined_score=min_combined_score_val,
                    include_archived=include_archived or False
                )
                
                paginated_results = results[skip:skip + limit]
                total_items = len(results)
            
            # For advanced search, return results directly without conversion
            # The search results are already MemoryBlockWithScore but we'll extract the base fields
            memories = paginated_results
            
            logger.info(f"Advanced search ({search_type}) for '{search_query}' returned {len(memories)} results")
            
        except Exception as e:
            logger.error(f"Error in {search_type} search: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")
            
    else:
        # Use basic CRUD search with filtering
        memories, total_items = crud.get_all_memory_blocks(
            db=db,
            agent_id=processed_agent_id,
            conversation_id=processed_conversation_id,
            search_query=search_query,
            start_date=processed_start_date,
            end_date=processed_end_date,
            min_feedback_score=processed_min_feedback_score,
            max_feedback_score=processed_max_feedback_score,
            min_retrieval_count=processed_min_retrieval_count,
            max_retrieval_count=processed_max_retrieval_count,
            keyword_ids=processed_keyword_ids,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
            get_total=True,
            include_archived=include_archived or False
        )

    total_pages = math.ceil(total_items / limit) if limit > 0 else 0

    return {
        "items": memories,
        "total_items": total_items,
        "total_pages": total_pages
    }

@router.get("/memory-blocks/archived/", response_model=schemas.PaginatedMemoryBlocks)
def get_archived_memory_blocks_endpoint(
    agent_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    search_query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    min_feedback_score: Optional[str] = None,
    max_feedback_score: Optional[str] = None,
    min_retrieval_count: Optional[str] = None,
    max_retrieval_count: Optional[str] = None,
    keywords: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Retrieve all archived memory blocks with advanced filtering, searching, and sorting capabilities.
    """
    processed_agent_id: Optional[uuid.UUID] = None
    if agent_id:
        try:
            processed_agent_id = uuid.UUID(agent_id)
        except ValueError:
            if agent_id != "":
                raise HTTPException(status_code=422, detail="Invalid UUID format for agent_id.")
            processed_agent_id = None

    processed_conversation_id: Optional[uuid.UUID] = None
    if conversation_id:
        try:
            processed_conversation_id = uuid.UUID(conversation_id)
        except ValueError:
            if conversation_id != "":
                raise HTTPException(status_code=422, detail="Invalid UUID format for conversation_id.")
            processed_conversation_id = None

    processed_start_date: Optional[datetime] = None
    if start_date and start_date != "":
        try:
            processed_start_date = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid datetime format for start_date. Expected ISO 8601.")

    processed_end_date: Optional[datetime] = None
    if end_date and end_date != "":
        try:
            processed_end_date = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid datetime format for end_date. Expected ISO 8601.")

    processed_min_feedback_score: Optional[int] = None
    if min_feedback_score:
        try:
            processed_min_feedback_score = int(min_feedback_score)
        except ValueError:
            if min_feedback_score != "":
                raise HTTPException(status_code=422, detail="Invalid integer format for min_feedback_score.")

    processed_max_feedback_score: Optional[int] = None
    if max_feedback_score:
        try:
            processed_max_feedback_score = int(max_feedback_score)
        except ValueError:
            if max_feedback_score != "":
                raise HTTPException(status_code=422, detail="Invalid integer format for max_feedback_score.")

    processed_min_retrieval_count: Optional[int] = None
    if min_retrieval_count:
        try:
            processed_min_retrieval_count = int(min_retrieval_count)
        except ValueError:
            if min_retrieval_count != "":
                raise HTTPException(status_code=422, detail="Invalid integer format for min_retrieval_count.")

    processed_max_retrieval_count: Optional[int] = None
    if max_retrieval_count:
        try:
            processed_max_retrieval_count = int(max_retrieval_count)
        except ValueError:
            if max_retrieval_count != "":
                raise HTTPException(status_code=422, detail="Invalid integer format for max_retrieval_count.")

    processed_keyword_ids: Optional[List[uuid.UUID]] = None
    if keywords and keywords != "":
        try:
            processed_keyword_ids = [uuid.UUID(kw.strip()) for kw in keywords.split(',') if kw.strip()]
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid UUID format in keywords parameter.")

    search_query = search_query if search_query else None
    sort_by = sort_by if sort_by else None
    sort_order = sort_order if sort_order else "asc"

    processed_skip = skip
    processed_limit = limit

    memories, total_items = crud.get_all_memory_blocks(
        db=db,
        agent_id=processed_agent_id,
        conversation_id=processed_conversation_id,
        search_query=search_query,
        start_date=processed_start_date,
        end_date=processed_end_date,
        max_feedback_score=processed_max_feedback_score,
        min_retrieval_count=processed_min_retrieval_count,
        max_retrieval_count=processed_max_retrieval_count,
        keyword_ids=processed_keyword_ids,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=processed_skip,
        limit=processed_limit,
        get_total=True,
        include_archived=True, # Explicitly include archived blocks
        is_archived=True # Filter for only archived blocks
    )

    total_pages = math.ceil(total_items / processed_limit) if processed_limit > 0 else 0

    return {
        "items": memories,
        "total_items": total_items,
        "total_pages": total_pages
    }

@router.post("/memory-blocks/", response_model=schemas.MemoryBlock, status_code=status.HTTP_201_CREATED)
def create_memory_block_endpoint(memory_block: schemas.MemoryBlockCreate, db: Session = Depends(get_db)):
    # Ensure agent exists
    agent = crud.get_agent(db, agent_id=memory_block.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db_memory_block = crud.create_memory_block(db=db, memory_block=memory_block)
    print(f"Created memory block ID: {db_memory_block.id}") # Use .id as per schema change
    return db_memory_block

@router.get("/memory-blocks/{memory_id}", response_model=schemas.MemoryBlock)
def get_memory_block_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return db_memory_block

@router.put("/memory-blocks/{memory_id}", response_model=schemas.MemoryBlock)
def update_memory_block_endpoint(
    memory_id: uuid.UUID,
    memory_block: schemas.MemoryBlockUpdate,
    db: Session = Depends(get_db)
):
    db_memory_block = crud.update_memory_block(db, memory_id=memory_id, memory_block=memory_block)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return db_memory_block

@router.post("/memory-blocks/{memory_id}/archive", response_model=schemas.MemoryBlock)
def archive_memory_block_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Archives a memory block by setting its 'archived' flag to True.
    """
    db_memory_block = crud.archive_memory_block(db, memory_id=memory_id)
    if db_memory_block is None: # Check for None explicitly
        raise HTTPException(status_code=404, detail="Memory block not found")
    return db_memory_block

@router.delete("/memory-blocks/{memory_id}/hard-delete", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete_memory_block_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Performs a hard delete of a memory block from the database.
    """
    success = crud.delete_memory_block(db, memory_id=memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return {"message": "Memory block hard deleted successfully"}

@router.post("/memory-blocks/{memory_id}/feedback/", response_model=schemas.MemoryBlock)
def report_memory_feedback_endpoint(
    memory_id: uuid.UUID,
    feedback: schemas.FeedbackLogCreate,
    db: Session = Depends(get_db)
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    
    # Ensure the feedback's memory_id matches the path parameter
    if feedback.memory_id != memory_id:
        raise HTTPException(status_code=400, detail="Memory ID in path and request body do not match.")

    updated_memory = crud.report_memory_feedback(
        db=db,
        memory_id=memory_id,
        feedback_type=feedback.feedback_type,
        feedback_details=feedback.feedback_details
    )
    return updated_memory

# Keyword Endpoints
@router.post("/keywords/", response_model=schemas.Keyword, status_code=status.HTTP_201_CREATED)
def create_keyword_endpoint(keyword: schemas.KeywordCreate, db: Session = Depends(get_db)):
    db_keyword = crud.get_keyword_by_text(db, keyword_text=keyword.keyword_text)
    if db_keyword:
        raise HTTPException(status_code=400, detail="Keyword with this text already exists")
    return crud.create_keyword(db=db, keyword=keyword)

@router.get("/keywords/", response_model=List[schemas.Keyword])
def get_all_keywords_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    keywords = crud.get_keywords(db, skip=skip, limit=limit)
    return keywords

@router.get("/keywords/{keyword_id}", response_model=schemas.Keyword)
def get_keyword_endpoint(keyword_id: uuid.UUID, db: Session = Depends(get_db)):
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return db_keyword

@router.put("/keywords/{keyword_id}", response_model=schemas.Keyword)
def update_keyword_endpoint(
    keyword_id: uuid.UUID,
    keyword: schemas.KeywordUpdate,
    db: Session = Depends(get_db)
):
    db_keyword = crud.update_keyword(db, keyword_id=keyword_id, keyword=keyword)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return db_keyword

@router.delete("/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_endpoint(keyword_id: uuid.UUID, db: Session = Depends(get_db)):
    success = crud.delete_keyword(db, keyword_id=keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return {"message": "Keyword deleted successfully"}

# MemoryBlockKeyword Association Endpoints
@router.post("/memory-blocks/{memory_id}/keywords/{keyword_id}", response_model=schemas.MemoryBlockKeywordAssociation, status_code=status.HTTP_201_CREATED)
def associate_keyword_with_memory_block_endpoint(
    memory_id: uuid.UUID,
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    # Check if association already exists
    existing_association = db.query(models.MemoryBlockKeyword).filter(
        models.MemoryBlockKeyword.memory_id == memory_id,
        models.MemoryBlockKeyword.keyword_id == keyword_id
    ).first()
    if existing_association:
        raise HTTPException(status_code=409, detail="Association already exists")

    association = crud.create_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword_id)
    return association

@router.delete("/memory-blocks/{memory_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def disassociate_keyword_from_memory_block_endpoint(
    memory_id: uuid.UUID,
    keyword_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    success = crud.delete_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="Association not found")
    return {"message": "Association deleted successfully"}

@router.get("/memory-blocks/search/", response_model=List[schemas.MemoryBlock])
def search_memory_blocks_endpoint(
    keywords: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    # This endpoint is for agent-facing semantic search, not for the dashboard's simple search.
    # It will remain as a keyword-based search for now as per the plan,
    # with a note that complex logic will be implemented later.
    keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
    if not keyword_list:
        raise HTTPException(status_code=400, detail="At least one keyword is required for search.")
    
    memories = crud.retrieve_relevant_memories(
        db=db,
        keywords=keyword_list,
        agent_id=agent_id,
        conversation_id=conversation_id,
        limit=limit
    )
    return memories

@router.get("/memory-blocks/{memory_id}/keywords/", response_model=List[schemas.Keyword])
def get_memory_block_keywords_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")

    keywords = crud.get_memory_block_keywords(db, memory_id=memory_id)
    return keywords

@router.get("/keywords/{keyword_id}/memory-blocks/", response_model=List[schemas.MemoryBlock])
def get_keyword_memory_blocks_endpoint(keyword_id: uuid.UUID, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """
    Get all memory blocks associated with a specific keyword.
    This endpoint is used for keyword analytics to show which memory blocks use each keyword.
    """
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    memory_blocks = crud.get_keyword_memory_blocks(db, keyword_id=keyword_id, skip=skip, limit=limit)
    return memory_blocks

@router.get("/keywords/{keyword_id}/memory-blocks/count")
def get_keyword_memory_blocks_count_endpoint(keyword_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Get the count of memory blocks associated with a specific keyword.
    This endpoint is used for displaying usage statistics on keyword cards.
    """
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    count = crud.get_keyword_memory_blocks_count(db, keyword_id=keyword_id)
    return {"count": count}

# Consolidation Trigger Endpoint
@router.post("/consolidation/trigger/", status_code=status.HTTP_202_ACCEPTED)
def trigger_consolidation_endpoint(db: Session = Depends(get_db)):
    """
    Trigger the memory block consolidation process manually.
    This endpoint initiates the worker process to analyze memory blocks for duplicates
    and generate consolidation suggestions.
    """
    from core.core.consolidation_worker import run_consolidation_analysis
    logger.info("Manual trigger of consolidation process received")
    
    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. LLM-based consolidation will not occur.")
        # Optionally, you might raise an HTTPException here if LLM is strictly required
        # raise HTTPException(status_code=500, detail="LLM_API_KEY is not set, LLM-based consolidation cannot proceed.")

    try:
        # Run the consolidation process in a non-blocking way if possible
        # For simplicity in this implementation, we run it synchronously
        run_consolidation_analysis(llm_api_key)
        return {"message": "Consolidation process triggered successfully"}
    except Exception as e:
        logger.error(f"Error triggering consolidation process: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error triggering consolidation process: {str(e)}")

# Consolidation Suggestions Endpoints
@router.get("/consolidation-suggestions/", response_model=schemas.PaginatedConsolidationSuggestions)
def get_consolidation_suggestions_endpoint(
    status: Optional[str] = None,
    group_id: Optional[uuid.UUID] = None,
    sort_by: Optional[str] = "timestamp",
    sort_order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Retrieve all consolidation suggestions with filtering, sorting, and pagination.
    """
    logger.info(f"Fetching consolidation suggestions with filters: status={status}, group_id={group_id}")
    
    # Get paginated suggestions and total count
    suggestions, total_items = crud.get_consolidation_suggestions(
        db=db,
        status=status,
        group_id=group_id,
        skip=skip,
        limit=limit
    )
    
    total_pages = math.ceil(total_items / limit) if limit > 0 else 0

    return {
        "items": suggestions,
        "total_items": total_items,
        "total_pages": total_pages
    }

@router.get("/consolidation-suggestions/{suggestion_id}", response_model=schemas.ConsolidationSuggestion)
def get_consolidation_suggestion_endpoint(suggestion_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve a specific consolidation suggestion by ID.
    """
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    return suggestion

@router.post("/consolidation-suggestions/{suggestion_id}/validate/", response_model=schemas.ConsolidationSuggestion)
def validate_consolidation_suggestion_endpoint(suggestion_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Validate a consolidation suggestion, replacing original memory blocks with the consolidated version.
    """
    logger.info(f"Validating consolidation suggestion {suggestion_id}")
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail="Suggestion is not in pending status")

    try:
        crud.apply_consolidation(db, suggestion_id=suggestion_id)
        # Fetch the updated suggestion to return
        updated_suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
        if not updated_suggestion:
            raise HTTPException(status_code=404, detail="Updated consolidation suggestion not found")
        # Update status to 'validated' if not already set by apply_consolidation
        if updated_suggestion.status == "pending":
            update_schema = schemas.ConsolidationSuggestionUpdate(status="validated")
            updated_suggestion = crud.update_consolidation_suggestion(db, suggestion_id=suggestion_id, suggestion=update_schema)
        return updated_suggestion
    except Exception as e:
        logger.error(f"Error validating suggestion {suggestion_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating suggestion: {str(e)}")

@router.post("/consolidation-suggestions/{suggestion_id}/reject/", response_model=schemas.ConsolidationSuggestion)
def reject_consolidation_suggestion_endpoint(suggestion_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Reject a consolidation suggestion, marking it as rejected.
    """
    logger.info(f"Rejecting consolidation suggestion {suggestion_id}")
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail="Suggestion is not in pending status")

    # Create a schema object for the update
    update_schema = schemas.ConsolidationSuggestionUpdate(status="rejected")
    updated_suggestion = crud.update_consolidation_suggestion(db, suggestion_id=suggestion_id, suggestion=update_schema)
    return updated_suggestion

@router.delete("/consolidation-suggestions/{suggestion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consolidation_suggestion_endpoint(suggestion_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Deletes a consolidation suggestion from the database.
    """
    success = crud.delete_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not success:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    return {"message": "Consolidation suggestion deleted successfully"}

# Health check endpoint
@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.get("/build-info")
def get_build_info():
    """
    Returns build and deployment information for the current running service.
    """
    build_sha = os.getenv("BUILD_SHA")
    build_timestamp = os.getenv("BUILD_TIMESTAMP")
    image_tag = os.getenv("IMAGE_TAG")
    version = os.getenv("VERSION", "unknown")
    
    # Return None for missing values instead of default strings
    return {
        "build_sha": build_sha if build_sha else None,
        "build_timestamp": build_timestamp if build_timestamp else None,
        "image_tag": image_tag if image_tag else None,
        "service_name": "hindsight-service",
        "version": version
    }

# User info endpoint for OAuth2 authentication
@router.get("/user-info")
def get_user_info(
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None)
):
    """
    Returns the authenticated user information from OAuth2 proxy headers.
    These headers are set by the OAuth2 proxy when authentication is successful.

    For local development, bypasses authentication and returns mock user info.
    """
    # Check if we're in development mode
    is_dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

    if is_dev_mode:
        # Development mode: bypass authentication
        return {
            "authenticated": True,
            "user": "dev_user",
            "email": "dev@localhost"
        }

    # Production mode: check OAuth2 proxy headers
    if not x_auth_request_user and not x_auth_request_email:
        return {"authenticated": False, "message": "No authentication headers found"}

    return {
        "authenticated": True,
        "user": x_auth_request_user,
        "email": x_auth_request_email
    }

# Dashboard Stats Endpoints
@router.get("/conversations/count")
def get_conversations_count_endpoint(db: Session = Depends(get_db)):
    """
    Get the count of unique conversations from memory blocks.
    This endpoint is used by the dashboard to display conversation statistics.
    """
    try:
        count = crud.get_unique_conversation_count(db)
        return {"count": count or 0}  # Return 0 if count is None
    except Exception as e:
        logger.error(f"Error getting conversations count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting conversations count: {str(e)}")

# Pruning Endpoints
@router.post("/memory/prune/suggest", response_model=dict)
def generate_pruning_suggestions_endpoint(
    request: dict = None,
    db: Session = Depends(get_db)
):
    """
    Generate memory block pruning suggestions using LLM evaluation.
    Returns a batch of memory blocks with pruning scores for human review.
    """
    if request is None:
        request = {}
    
    batch_size = request.get("batch_size", 50)
    target_count = request.get("target_count")
    max_iterations = request.get("max_iterations", 10)
    
    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Fallback scoring will be used.")
    
    try:
        # Get pruning service instance
        pruning_service = get_pruning_service(llm_api_key)
        
        # Generate pruning suggestions
        suggestions = pruning_service.generate_pruning_suggestions(
            db=db,
            batch_size=batch_size,
            target_count=target_count,
            max_iterations=max_iterations
        )
        
        return suggestions
    except Exception as e:
        logger.error(f"Error generating pruning suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating pruning suggestions: {str(e)}")

@router.post("/memory/prune/confirm", response_model=dict)
def confirm_pruning_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Confirm and archive selected memory blocks for pruning.
    This endpoint archives the memory blocks that were approved for pruning.
    """
    memory_block_ids = request.get("memory_block_ids", [])
    
    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided for pruning")
    
    archived_count = 0
    failed_count = 0
    failed_blocks = []
    
    try:
        for memory_id_str in memory_block_ids:
            try:
                memory_id = uuid.UUID(memory_id_str)
                success = crud.archive_memory_block(db, memory_id=memory_id)
                if success:
                    archived_count += 1
                    logger.info(f"Successfully archived memory block {memory_id_str} for pruning")
                else:
                    failed_count += 1
                    failed_blocks.append(memory_id_str)
                    logger.warning(f"Failed to archive memory block {memory_id_str}")
            except ValueError:
                failed_count += 1
                failed_blocks.append(memory_id_str)
                logger.error(f"Invalid UUID format for memory block ID: {memory_id_str}")
            except Exception as e:
                failed_count += 1
                failed_blocks.append(memory_id_str)
                logger.error(f"Error archiving memory block {memory_id_str}: {str(e)}")
        
        db.commit()
        
        return {
            "message": f"Pruning confirmation processed successfully",
            "archived_count": archived_count,
            "failed_count": failed_count,
            "failed_blocks": failed_blocks if failed_blocks else None
        }
    except Exception as e:
        logger.error(f"Error confirming pruning: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error confirming pruning: {str(e)}")

# Compression Endpoints
@router.post("/memory-blocks/{memory_id}/compress", response_model=dict)
def compress_memory_block_endpoint(
    memory_id: uuid.UUID,
    request: dict = None,
    db: Session = Depends(get_db)
):
    """
    Compress a memory block using LLM to create a more condensed version.
    Returns the compression suggestion for user review and approval.
    """
    if request is None:
        request = {}

    user_instructions = request.get("user_instructions", "")

    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Cannot perform compression.")
        raise HTTPException(status_code=500, detail="LLM service not available for compression")

    try:
        # Get compression service instance
        compression_service = get_compression_service(llm_api_key)

        # Compress the memory block
        compression_result = compression_service.compress_memory_block(
            db=db,
            memory_id=memory_id,
            user_instructions=user_instructions
        )

        # Check if compression was successful
        if "error" in compression_result:
            raise HTTPException(
                status_code=400 if "not found" in compression_result["message"].lower() else 500,
                detail=compression_result["message"]
            )

        return compression_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error compressing memory block {memory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error compressing memory block: {str(e)}")

@router.post("/memory-blocks/{memory_id}/compress/apply", response_model=schemas.MemoryBlock)
def apply_memory_compression_endpoint(
    memory_id: uuid.UUID,
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Apply the compressed version to replace the original memory block content.
    """
    compressed_content = request.get("compressed_content")
    compressed_lessons = request.get("compressed_lessons_learned")

    if not compressed_content:
        raise HTTPException(status_code=400, detail="Compressed content is required")

    try:
        # Update the memory block with compressed content
        update_data = schemas.MemoryBlockUpdate(
            content=compressed_content,
            lessons_learned=compressed_lessons
        )

        updated_memory = crud.update_memory_block(
            db=db,
            memory_id=memory_id,
            memory_block=update_data
        )

        if not updated_memory:
            raise HTTPException(status_code=404, detail="Memory block not found")

        logger.info(f"Successfully applied compression to memory block {memory_id}")
        return updated_memory

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying compression to memory block {memory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error applying compression: {str(e)}")

# Bulk Keyword Generation Endpoint
@router.post("/memory-blocks/bulk-generate-keywords", response_model=dict)
def bulk_generate_keywords_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Generate keywords for multiple memory blocks using basic keyword extraction.
    Returns suggested keywords for each memory block for user review and approval.
    """
    memory_block_ids = request.get("memory_block_ids", [])
    
    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided")
    
    try:
        suggestions = []
        successful_count = 0
        failed_count = 0
        
        for memory_id_str in memory_block_ids:
            try:
                memory_id = uuid.UUID(memory_id_str)
                memory_block = crud.get_memory_block(db, memory_id=memory_id)
                
                if not memory_block:
                    logger.warning(f"Memory block not found: {memory_id_str}")
                    continue
                
                # Extract keywords from content and lessons_learned
                content_text = (memory_block.content or '') + ' ' + (memory_block.lessons_learned or '')
                
                # Simple keyword extraction (enhanced version of the disabled function)
                suggested_keywords = extract_keywords_enhanced(content_text)
                
                if suggested_keywords:
                    suggestions.append({
                        "memory_block_id": str(memory_id),
                        "memory_block_content_preview": (memory_block.content or '')[:100] + "..." if len(memory_block.content or '') > 100 else (memory_block.content or ''),
                        "suggested_keywords": suggested_keywords,
                        "current_keywords": [kw.keyword_text for kw in memory_block.keywords] if memory_block.keywords else []
                    })
                    successful_count += 1
                else:
                    logger.info(f"No keywords could be extracted for memory block {memory_id_str}")
                    failed_count += 1
                    
            except ValueError:
                failed_count += 1
                logger.error(f"Invalid UUID format: {memory_id_str}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing memory block {memory_id_str}: {str(e)}")
        
        return {
            "suggestions": suggestions,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "total_processed": len(memory_block_ids),
            "message": f"Generated keyword suggestions for {successful_count} memory blocks"
        }
        
    except Exception as e:
        logger.error(f"Error in bulk keyword generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating keywords: {str(e)}")

def extract_keywords_enhanced(text: str) -> List[str]:
    """
    Enhanced keyword extraction using simple text analysis.
    This is a fallback function when spaCy is not available.
    """
    if not text or not text.strip():
        return []
    
    import re
    from collections import Counter
    
    # Clean and normalize text
    text = text.lower()
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
        'his', 'hers', 'its', 'our', 'their', 'myself', 'yourself', 'himself', 'herself', 'itself',
        'ourselves', 'yourselves', 'themselves', 'what', 'which', 'who', 'whom', 'whose', 'where',
        'when', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
        'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'now', 'here', 'there', 'then', 'up', 'down', 'out', 'off', 'over', 'under', 'again',
        'further', 'once', 'during', 'before', 'after', 'above', 'below', 'between', 'through',
        'into', 'from', 'about', 'against', 'within', 'without'
    }
    
    # Extract words (alphanumeric sequences of 3+ characters)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
    
    # Filter out stop words and get word frequencies
    meaningful_words = [word for word in words if word not in stop_words]
    word_freq = Counter(meaningful_words)
    
    # Look for technical terms, proper nouns (capitalized words in original text), and domain-specific keywords
    technical_patterns = [
        r'\b(?:api|database|server|client|service|system|process|function|method|class|object|data|model|algorithm|framework|library|module|component|interface|protocol|network|security|authentication|authorization|token|session|cache|memory|storage|disk|cpu|gpu|performance|optimization|configuration|deployment|environment|production|development|testing|debugging|logging|monitoring|analytics|metrics|dashboard|report|analysis|query|search|filter|sort|pagination|validation|error|exception|warning|info|debug|trace)\b',
        r'\b(?:python|javascript|typescript|java|c\+\+|golang|rust|php|ruby|html|css|sql|json|xml|yaml|api|rest|graphql|http|https|tcp|udp|websocket|oauth|jwt|ssl|tls|aws|azure|gcp|docker|kubernetes|git|github|gitlab|jenkins|terraform|ansible|nginx|apache|postgresql|mysql|mongodb|redis|elasticsearch|kafka|rabbitmq|react|vue|angular|node|express|flask|django|fastapi|spring|laravel)\b',
        r'\b(?:user|admin|client|customer|account|profile|settings|preferences|notification|email|password|login|logout|signup|registration|dashboard|home|page|view|screen|form|input|button|menu|navigation|header|footer|sidebar|modal|dialog|popup|tab|accordion|carousel|slider|chart|graph|table|list|grid|card|tile|widget|component)\b'
    ]
    
    # Find technical terms
    technical_words = set()
    for pattern in technical_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        technical_words.update(matches)
    
    # Combine high-frequency words with technical terms
    # Get top words by frequency (minimum frequency of 2 or if text is short, frequency of 1)
    min_freq = 2 if len(meaningful_words) > 20 else 1
    frequent_words = [word for word, count in word_freq.most_common(10) if count >= min_freq]
    
    # Combine and deduplicate
    keywords = list(set(frequent_words + list(technical_words)))
    
    # Sort by relevance (technical terms first, then by frequency)
    def keyword_score(word):
        tech_score = 10 if word.lower() in technical_words else 0
        freq_score = word_freq.get(word, 0)
        return tech_score + freq_score
    
    keywords.sort(key=keyword_score, reverse=True)
    
    # Return top 8 keywords
    return keywords[:8]

@router.post("/memory-blocks/bulk-apply-keywords", response_model=dict)
def bulk_apply_keywords_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Apply selected keywords to memory blocks.
    Expects a list of memory block IDs with their selected keywords.
    """
    applications = request.get("applications", [])
    
    if not applications:
        raise HTTPException(status_code=400, detail="No keyword applications provided")
    
    try:
        successful_count = 0
        failed_count = 0
        results = []
        
        for application in applications:
            memory_block_id = application.get("memory_block_id")
            selected_keywords = application.get("selected_keywords", [])
            
            if not memory_block_id or not selected_keywords:
                failed_count += 1
                continue
                
            try:
                memory_id = uuid.UUID(memory_block_id)
                memory_block = crud.get_memory_block(db, memory_id=memory_id)
                
                if not memory_block:
                    failed_count += 1
                    continue
                
                added_keywords = []
                skipped_keywords = []
                
                for keyword_text in selected_keywords:
                    # Get or create keyword
                    keyword = crud.get_keyword_by_text(db, keyword_text=keyword_text)
                    if not keyword:
                        keyword_create = schemas.KeywordCreate(keyword_text=keyword_text)
                        keyword = crud.create_keyword(db=db, keyword=keyword_create)
                    
                    # Check if association already exists
                    existing_association = db.query(models.MemoryBlockKeyword).filter(
                        models.MemoryBlockKeyword.memory_id == memory_id,
                        models.MemoryBlockKeyword.keyword_id == keyword.keyword_id
                    ).first()
                    
                    if not existing_association:
                        crud.create_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword.keyword_id)
                        added_keywords.append(keyword_text)
                    else:
                        skipped_keywords.append(keyword_text)
                
                results.append({
                    "memory_block_id": memory_block_id,
                    "added_keywords": added_keywords,
                    "skipped_keywords": skipped_keywords,
                    "success": True
                })
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Error applying keywords to memory block {memory_block_id}: {str(e)}")
                results.append({
                    "memory_block_id": memory_block_id,
                    "error": str(e),
                    "success": False
                })
                failed_count += 1
        
        return {
            "results": results,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "message": f"Applied keywords to {successful_count} memory blocks"
        }
        
    except Exception as e:
        logger.error(f"Error in bulk keyword application: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error applying keywords: {str(e)}")

@router.post("/memory-blocks/bulk-compact", response_model=dict)
async def bulk_compact_memory_blocks_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Bulk compact multiple memory blocks using AI compression.
    This endpoint processes multiple memory blocks for compaction with optional concurrency.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    logger.info(f"Bulk compaction request received with {len(request.get('memory_block_ids', []))} blocks")
    
    memory_block_ids = request.get("memory_block_ids", [])
    user_instructions = request.get("user_instructions", "")
    max_concurrent = request.get("max_concurrent", 1)  # Default to 1 for safety
    
    # Validate max_concurrent parameter
    if not isinstance(max_concurrent, int) or max_concurrent < 1:
        max_concurrent = 1
    if max_concurrent > 10:  # Reasonable upper limit to prevent abuse
        max_concurrent = 10
    
    logger.info(f"Using max_concurrent: {max_concurrent}")
    
    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided")
    
    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Cannot perform bulk compaction.")
        raise HTTPException(status_code=500, detail="LLM service not available for compaction")
    
    logger.info(f"Starting bulk compaction for {len(memory_block_ids)} blocks with {max_concurrent} concurrent processes")
    
    def process_single_block(memory_id_str: str):
        """Process a single memory block in a separate thread."""
        try:
            memory_id = uuid.UUID(memory_id_str)
            logger.info(f"Starting compression for block {memory_id_str}")
            
            # Get compression service instance (in the thread)
            compression_service = get_compression_service(llm_api_key)
            
            # Create a new DB session for this thread
            db_gen = get_db()
            thread_db = next(db_gen)
            
            try:
                # Compress the memory block
                compression_result = compression_service.compress_memory_block(
                    db=thread_db,
                    memory_id=memory_id,
                    user_instructions=user_instructions
                )
                logger.info(f"Compression completed for block {memory_id_str}")
                
                # Check if compression was successful
                if "error" not in compression_result:
                    # Auto-apply the compression if successful
                    compressed_content = compression_result.get("compressed_content")
                    compressed_lessons = compression_result.get("compressed_lessons_learned")
                    
                    if compressed_content:
                        # Update the memory block with compressed content
                        update_data = schemas.MemoryBlockUpdate(
                            content=compressed_content,
                            lessons_learned=compressed_lessons
                        )
                        
                        updated_memory = crud.update_memory_block(
                            db=thread_db,
                            memory_id=memory_id,
                            memory_block=update_data
                        )
                        
                        if updated_memory:
                            return {
                                "memory_block_id": memory_id_str,
                                "success": True,
                                "original_length": len(compression_result.get("original_content", "")),
                                "compressed_length": len(compressed_content),
                                "compression_ratio": compression_result.get("compression_ratio", 0),
                                "message": "Successfully compacted"
                            }
                        else:
                            return {
                                "memory_block_id": memory_id_str,
                                "success": False,
                                "error": "Failed to update memory block"
                            }
                    else:
                        return {
                            "memory_block_id": memory_id_str,
                            "success": False,
                            "error": "No compressed content returned"
                        }
                else:
                    return {
                        "memory_block_id": memory_id_str,
                        "success": False,
                        "error": compression_result.get("message", "Compression failed")
                    }
            finally:
                thread_db.close()
                    
        except ValueError:
            logger.error(f"Invalid UUID format: {memory_id_str}")
            return {
                "memory_block_id": memory_id_str,
                "success": False,
                "error": "Invalid UUID format"
            }
        except Exception as e:
            logger.error(f"Error compacting memory block {memory_id_str}: {str(e)}")
            return {
                "memory_block_id": memory_id_str,
                "success": False,
                "error": str(e)
            }
    
    try:
        # Use ThreadPoolExecutor for concurrent processing
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Create tasks for all memory blocks
            tasks = [
                loop.run_in_executor(executor, process_single_block, memory_id)
                for memory_id in memory_block_ids
            ]
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        successful_count = 0
        failed_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                processed_results.append({
                    "memory_block_id": "unknown",
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
                if result.get("success", False):
                    successful_count += 1
                else:
                    failed_count += 1
        
        return {
            "results": processed_results,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "total_processed": len(memory_block_ids),
            "message": f"Successfully compacted {successful_count} out of {len(memory_block_ids)} memory blocks"
        }
        
    except Exception as e:
        logger.error(f"Error in bulk memory block compaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error compacting memory blocks: {str(e)}")

# Enhanced Search Endpoints

@router.get("/memory-blocks/search/fulltext", response_model=List[schemas.MemoryBlockWithScore])
def search_memory_blocks_fulltext_endpoint(
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    min_score: float = 0.1,
    include_archived: bool = False,
    db: Session = Depends(get_db)
):
    """
    Perform BM25-like full-text search on memory blocks using PostgreSQL's full-text search capabilities.
    
    Args:
        query: Search query string
        agent_id: Optional agent filter
        conversation_id: Optional conversation filter
        limit: Maximum number of results (default: 50)
        min_score: Minimum relevance score threshold (default: 0.1)
        include_archived: Whether to include archived memory blocks (default: False)
    
    Returns:
        List of memory blocks with search scores, ranked by relevance
    """
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
        results, metadata = crud.search_memory_blocks_fulltext(
            db=db,
            query=query.strip(),
            agent_id=agent_id,
            conversation_id=conversation_id,
            limit=limit,
            min_score=min_score,
            include_archived=include_archived
        )
        
        logger.info(f"Full-text search for '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in full-text search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/memory-blocks/search/semantic", response_model=List[schemas.MemoryBlockWithScore])
def search_memory_blocks_semantic_endpoint(
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    similarity_threshold: float = 0.7,
    include_archived: bool = False,
    db: Session = Depends(get_db)
):
    """
    Perform semantic search on memory blocks using embeddings (placeholder implementation).
    
    Args:
        query: Search query string
        agent_id: Optional agent filter
        conversation_id: Optional conversation filter
        limit: Maximum number of results (default: 50)
        similarity_threshold: Minimum similarity threshold (default: 0.7)
        include_archived: Whether to include archived memory blocks (default: False)
    
    Returns:
        List of memory blocks with similarity scores (currently empty - placeholder)
    """
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    try:
        results, metadata = crud.search_memory_blocks_semantic(
            db=db,
            query=query.strip(),
            agent_id=agent_id,
            conversation_id=conversation_id,
            limit=limit,
            similarity_threshold=similarity_threshold,
            include_archived=include_archived
        )
        
        logger.info(f"Semantic search for '{query}' returned {len(results)} results (placeholder)")
        return results
        
    except Exception as e:
        logger.error(f"Error in semantic search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/memory-blocks/search/hybrid", response_model=List[schemas.MemoryBlockWithScore])
def search_memory_blocks_hybrid_endpoint(
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    fulltext_weight: float = 0.7,
    semantic_weight: float = 0.3,
    min_combined_score: float = 0.1,
    include_archived: bool = False,
    db: Session = Depends(get_db)
):
    """
    Perform hybrid search combining full-text and semantic search with weighted scoring.
    
    Args:
        query: Search query string
        agent_id: Optional agent filter
        conversation_id: Optional conversation filter
        limit: Maximum number of results (default: 50)
        fulltext_weight: Weight for full-text search results (default: 0.7)
        semantic_weight: Weight for semantic search results (default: 0.3)
        min_combined_score: Minimum combined score threshold (default: 0.1)
        include_archived: Whether to include archived memory blocks (default: False)
    
    Returns:
        List of memory blocks with combined scores from both search methods
    """
    if not query or query.strip() == "":
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    # Validate weights
    if abs(fulltext_weight + semantic_weight - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="Fulltext and semantic weights must sum to 1.0")
    
    try:
        results, metadata = crud.search_memory_blocks_hybrid(
            db=db,
            query=query.strip(),
            agent_id=agent_id,
            conversation_id=conversation_id,
            limit=limit,
            fulltext_weight=fulltext_weight,
            semantic_weight=semantic_weight,
            min_combined_score=min_combined_score,
            include_archived=include_archived
        )
        
        logger.info(f"Hybrid search for '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Error in hybrid search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

# Include the main router
app.include_router(router)

# Include memory optimization router
try:
    from core.api.memory_optimization import router as memory_optimization_router
    app.include_router(memory_optimization_router, prefix="/memory-optimization", tags=["memory-optimization"])
    logger.info("Memory optimization endpoints loaded successfully")
except ImportError as e:
    logger.warning(f"Could not load memory optimization endpoints: {e}")

# Health check endpoint (duplicate but keeping for compatibility)
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "hindsight-service"}
