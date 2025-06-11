import logging # Moved to top
import os
from dotenv import load_dotenv, dotenv_values # Import dotenv_values
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import math # Import math for ceil

# Configure logging (Moved to top)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
# The .env file is in the parent directory (apps/hindsight-service)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
base_dir = os.path.dirname(parent_dir)
dotenv_path = os.path.join(base_dir, '.env')
logger.info(f"Attempting to load .env file from path: {dotenv_path}")
logger.info(f"Does .env file exist at path: {os.path.exists(dotenv_path)}")
# Use dotenv_values to load values and then manually set them in os.environ
config_values = dotenv_values(dotenv_path)
logger.info(f"Loaded config values from .env: {config_values.keys()}")
for key, value in config_values.items():
    os.environ[key] = value
    logger.info(f"Set environment variable {key} from .env")
logger.info(f"LLM_API_KEY after manual os.environ update: {os.getenv('LLM_API_KEY')}")

from core.db import models, schemas, crud
from core.db.database import engine, get_db

# models.Base.metadata.create_all(bind=engine) # Removed: Database schema is now managed by Alembic migrations.

app = FastAPI(
    title="Intelligent AI Agent Memory Service",
    description="API for managing AI agent memories, including creation, retrieval, and feedback.",
    version="1.0.0",
)

origins = [
    "http://localhost",
    "http://localhost:3000", # React frontend
    "http://localhost:8000", # FastAPI backend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/agents/", response_model=schemas.Agent, status_code=status.HTTP_201_CREATED)
def create_agent_endpoint(agent: schemas.AgentCreate, db: Session = Depends(get_db)):
    db_agent = crud.get_agent_by_name(db, agent_name=agent.agent_name)
    if db_agent:
        raise HTTPException(status_code=400, detail="Agent with this name already exists")
    return crud.create_agent(db=db, agent=agent)

@app.get("/agents/", response_model=List[schemas.Agent])
def get_all_agents_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    agents = crud.get_agents(db, skip=skip, limit=limit)
    return agents

@app.get("/agents/{agent_id}", response_model=schemas.Agent)
def get_agent_endpoint(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    db_agent = crud.get_agent(db, agent_id=agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@app.get("/agents/search/", response_model=List[schemas.Agent])
def search_agents_endpoint(query: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    agents = crud.search_agents(db, query=query, skip=skip, limit=limit)
    return agents

@app.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_endpoint(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    success = crud.delete_agent(db, agent_id=agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted successfully"}

@app.get("/memory-blocks/", response_model=schemas.PaginatedMemoryBlocks) # Changed response_model
def get_all_memory_blocks_endpoint(
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
    skip: int = 0, # Changed type to int and set default
    limit: int = 50, # Changed type to int and set default
    include_archived: Optional[bool] = False, # Added include_archived parameter
    db: Session = Depends(get_db)
):
    """
    Retrieve all memory blocks with advanced filtering, searching, and sorting capabilities.
    """
    logger.info(f"Received query parameters:")
    logger.info(f"  agent_id: {agent_id} (type: {type(agent_id)})")
    logger.info(f"  conversation_id: {conversation_id} (type: {type(conversation_id)})")
    logger.info(f"  search_query: {search_query} (type: {type(search_query)})")
    logger.info(f"  start_date: {start_date} (type: {type(start_date)})")
    logger.info(f"  end_date: {end_date} (type: {type(end_date)})")
    logger.info(f"  min_feedback_score: {min_feedback_score} (type: {type(min_feedback_score)})")
    logger.info(f"  max_feedback_score: {max_feedback_score} (type: {type(max_feedback_score)})")
    logger.info(f"  min_retrieval_count: {min_retrieval_count} (type: {type(min_retrieval_count)})")
    logger.info(f"  max_retrieval_count: {max_retrieval_count} (type: {type(max_retrieval_count)})")
    logger.info(f"  keywords: {keywords} (type: {type(keywords)})")
    logger.info(f"  sort_by: {sort_by} (type: {type(sort_by)})")
    logger.info(f"  sort_order: {sort_order} (type: {type(sort_order)})")
    logger.info(f"  skip: {skip} (type: {type(skip)})") # Updated log to reflect int type
    logger.info(f"  limit: {limit} (type: {type(limit)})") # Updated log to reflect int type

    # Process UUID parameters
    processed_agent_id: Optional[uuid.UUID] = None
    if agent_id: # Check if agent_id is not None or empty string
        try:
            processed_agent_id = uuid.UUID(agent_id)
        except ValueError:
            # If it's not a valid UUID, but not an empty string, raise error
            if agent_id != "":
                logger.error(f"Invalid UUID format for agent_id: '{agent_id}'")
                raise HTTPException(status_code=422, detail="Invalid UUID format for agent_id.")
            # If it's an empty string, treat as None
            processed_agent_id = None
    logger.info(f"  processed_agent_id: {processed_agent_id} (type: {type(processed_agent_id)})")

    processed_conversation_id: Optional[uuid.UUID] = None
    if conversation_id: # Check if conversation_id is not None or empty string
        try:
            processed_conversation_id = uuid.UUID(conversation_id)
        except ValueError:
            # If it's not a valid UUID, but not an empty string, raise error
            if conversation_id != "":
                logger.error(f"Invalid UUID format for conversation_id: '{conversation_id}'")
                raise HTTPException(status_code=422, detail="Invalid UUID format for conversation_id.")
            # If it's an empty string, treat as None
            processed_conversation_id = None
    logger.info(f"  processed_conversation_id: {processed_conversation_id} (type: {type(processed_conversation_id)})")

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

    # Process integer parameters (feedback score, retrieval count)
    # FastAPI will handle the conversion from query string to int directly if the type hint is int.
    # If the parameter is Optional[str], we need to manually convert.
    # Let's keep them as Optional[str] for now to avoid breaking changes with frontend sending empty strings,
    # and convert them to int if they are not None or empty.
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

    # Convert empty strings to None for other Optional[str] parameters
    # FastAPI handles Optional[str] where empty string is treated as None if not explicitly handled.
    # However, for robustness, explicitly setting to None if empty string is received.
    search_query = search_query if search_query else None
    sort_by = sort_by if sort_by else None
    sort_order = sort_order if sort_order else "asc" # Default to "asc" if empty

    # Process pagination parameters
    processed_skip = skip
    processed_limit = limit

    # Get paginated memories and total count
    memories, total_items = crud.get_all_memory_blocks( # crud function needs to return total_items
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
        skip=processed_skip,
        limit=processed_limit,
        get_total=True, # Add a parameter to crud function to get total count
        include_archived=include_archived # Pass the include_archived parameter
    )

    total_pages = math.ceil(total_items / processed_limit) if processed_limit > 0 else 0

    return {
        "items": memories,
        "total_items": total_items,
        "total_pages": total_pages
    }

@app.get("/memory-blocks/archived/", response_model=schemas.PaginatedMemoryBlocks)
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

@app.post("/memory-blocks/", response_model=schemas.MemoryBlock, status_code=status.HTTP_201_CREATED)
def create_memory_block_endpoint(memory_block: schemas.MemoryBlockCreate, db: Session = Depends(get_db)):
    # Ensure agent exists
    agent = crud.get_agent(db, agent_id=memory_block.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db_memory_block = crud.create_memory_block(db=db, memory_block=memory_block)
    print(f"Created memory block ID: {db_memory_block.id}") # Use .id as per schema change
    return db_memory_block

@app.get("/memory-blocks/{memory_id}", response_model=schemas.MemoryBlock)
def get_memory_block_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return db_memory_block

@app.put("/memory-blocks/{memory_id}", response_model=schemas.MemoryBlock)
def update_memory_block_endpoint(
    memory_id: uuid.UUID,
    memory_block: schemas.MemoryBlockUpdate,
    db: Session = Depends(get_db)
):
    db_memory_block = crud.update_memory_block(db, memory_id=memory_id, memory_block=memory_block)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return db_memory_block

@app.post("/memory-blocks/{memory_id}/archive", response_model=schemas.MemoryBlock)
def archive_memory_block_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Archives a memory block by setting its 'archived' flag to True.
    """
    db_memory_block = crud.archive_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return db_memory_block

@app.delete("/memory-blocks/{memory_id}/hard-delete", status_code=status.HTTP_204_NO_CONTENT)
def hard_delete_memory_block_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Performs a hard delete of a memory block from the database.
    """
    success = crud.delete_memory_block(db, memory_id=memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory block not found")
    return {"message": "Memory block hard deleted successfully"}

@app.post("/memory-blocks/{memory_id}/feedback/", response_model=schemas.MemoryBlock)
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
@app.post("/keywords/", response_model=schemas.Keyword, status_code=status.HTTP_201_CREATED)
def create_keyword_endpoint(keyword: schemas.KeywordCreate, db: Session = Depends(get_db)):
    db_keyword = crud.get_keyword_by_text(db, keyword_text=keyword.keyword_text)
    if db_keyword:
        raise HTTPException(status_code=400, detail="Keyword with this text already exists")
    return crud.create_keyword(db=db, keyword=keyword)

@app.get("/keywords/", response_model=List[schemas.Keyword])
def get_all_keywords_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    keywords = crud.get_keywords(db, skip=skip, limit=limit)
    return keywords

@app.get("/keywords/{keyword_id}", response_model=schemas.Keyword)
def get_keyword_endpoint(keyword_id: uuid.UUID, db: Session = Depends(get_db)):
    db_keyword = crud.get_keyword(db, keyword_id=keyword_id)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return db_keyword

@app.put("/keywords/{keyword_id}", response_model=schemas.Keyword)
def update_keyword_endpoint(
    keyword_id: uuid.UUID,
    keyword: schemas.KeywordUpdate,
    db: Session = Depends(get_db)
):
    db_keyword = crud.update_keyword(db, keyword_id=keyword_id, keyword=keyword)
    if not db_keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return db_keyword

@app.delete("/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_keyword_endpoint(keyword_id: uuid.UUID, db: Session = Depends(get_db)):
    success = crud.delete_keyword(db, keyword_id=keyword_id)
    if not success:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return {"message": "Keyword deleted successfully"}

# MemoryBlockKeyword Association Endpoints
@app.post("/memory-blocks/{memory_id}/keywords/{keyword_id}", response_model=schemas.MemoryBlockKeywordAssociation, status_code=status.HTTP_201_CREATED)
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

@app.delete("/memory-blocks/{memory_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
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

@app.get("/memory-blocks/search/", response_model=List[schemas.MemoryBlock])
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

@app.get("/memory-blocks/{memory_id}/keywords/", response_model=List[schemas.Keyword])
def get_memory_block_keywords_endpoint(memory_id: uuid.UUID, db: Session = Depends(get_db)):
    db_memory_block = crud.get_memory_block(db, memory_id=memory_id)
    if not db_memory_block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    
    keywords = crud.get_memory_block_keywords(db, memory_id=memory_id)
    return keywords

# Consolidation Trigger Endpoint
@app.post("/consolidation/trigger/", status_code=status.HTTP_202_ACCEPTED)
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
@app.get("/consolidation-suggestions/", response_model=schemas.PaginatedConsolidationSuggestions)
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
    
    # Get paginated suggestions
    suggestions = crud.get_consolidation_suggestions(
        db=db,
        status=status,
        group_id=group_id,
        skip=skip,
        limit=limit
    )
    
    # Calculate total items (assuming suggestions is a list)
    total_items = len(suggestions) if suggestions else 0
    total_pages = math.ceil(total_items / limit) if limit > 0 else 0

    return {
        "items": suggestions,
        "total_items": total_items,
        "total_pages": total_pages
    }

@app.get("/consolidation-suggestions/{suggestion_id}", response_model=schemas.ConsolidationSuggestion)
def get_consolidation_suggestion_endpoint(suggestion_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve a specific consolidation suggestion by ID.
    """
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    return suggestion

@app.post("/consolidation-suggestions/{suggestion_id}/validate/", response_model=schemas.ConsolidationSuggestion)
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

@app.post("/consolidation-suggestions/{suggestion_id}/reject/", response_model=schemas.ConsolidationSuggestion)
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

@app.delete("/consolidation-suggestions/{suggestion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consolidation_suggestion_endpoint(suggestion_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Deletes a consolidation suggestion from the database.
    """
    success = crud.delete_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not success:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    return {"message": "Consolidation suggestion deleted successfully"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}
