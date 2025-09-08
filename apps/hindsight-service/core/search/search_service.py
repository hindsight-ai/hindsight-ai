"""
Advanced search service for memory blocks.
Supports BM25-like full-text search, semantic search (future), and hybrid search.
"""

import logging
import time
import uuid
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_

from core.db import models, schemas

logger = logging.getLogger(__name__)


def _create_memory_block_with_score(
    memory_block: models.MemoryBlock,
    score: float,
    search_type: str,
    rank_explanation: Optional[str] = None
) -> schemas.MemoryBlockWithScore:
    """
    Convert a MemoryBlock model to a MemoryBlockWithScore schema with search metadata.
    """
    # Convert keywords from SQLAlchemy models to Pydantic schemas
    keywords_list = []
    for keyword in memory_block.keywords:
        keywords_list.append(schemas.Keyword(
            keyword_id=keyword.keyword_id,
            keyword_text=keyword.keyword_text,
            created_at=keyword.created_at
        ))
    
    # Convert the MemoryBlock to dict, then add search-specific fields
    memory_block_dict = {
        'id': memory_block.id,
        'agent_id': memory_block.agent_id,
        'conversation_id': memory_block.conversation_id,
        'content': memory_block.content,
        'errors': memory_block.errors,
        'lessons_learned': memory_block.lessons_learned,
        'metadata_col': memory_block.metadata_col,
        'feedback_score': memory_block.feedback_score,
        'archived': memory_block.archived,
        'archived_at': memory_block.archived_at,
        'timestamp': memory_block.timestamp,
        'created_at': memory_block.created_at,
        'updated_at': memory_block.updated_at,
        'keywords': keywords_list,  # Use converted keywords
        'search_score': score,
        'search_type': search_type,
        'rank_explanation': rank_explanation
    }
    
    return schemas.MemoryBlockWithScore(**memory_block_dict)


class SearchService:
    """Service for handling different types of memory block searches."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def search_memory_blocks_fulltext(
        self,
        db: Session,
        query: str,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        min_score: float = 0.1,
        include_archived: bool = False,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """
        Perform BM25-like full-text search using PostgreSQL's built-in capabilities.
        
        Args:
            db: Database session
            query: Search query string
            agent_id: Optional agent filter
            conversation_id: Optional conversation filter
            limit: Maximum number of results
            min_score: Minimum relevance score threshold
            include_archived: Whether to include archived memory blocks
            
        Returns:
            Tuple of (results, metadata)
        """
        start_time = time.time()
        
        try:
            # Convert query to tsquery format
            # Use plainto_tsquery for simple queries, websearch_to_tsquery for advanced
            search_query_func = func.plainto_tsquery('english', query)
            
            # If query contains operators, use websearch_to_tsquery
            if any(op in query.lower() for op in ['and', 'or', 'not', '"']):
                search_query_func = func.websearch_to_tsquery('english', query)
            
            # Build base query with ranking using the pre-computed search_vector
            # Use ts_rank_cd for better ranking that considers document length
            rank_expression = func.ts_rank_cd(
                models.MemoryBlock.search_vector,
                search_query_func
            )
            
            base_query = db.query(
                models.MemoryBlock,
                rank_expression.label('rank')
            ).filter(
                models.MemoryBlock.search_vector.op('@@')(search_query_func)
            ).filter(
                rank_expression >= min_score
            )

            # Scope filters
            if current_user is None:
                base_query = base_query.filter(models.MemoryBlock.visibility_scope == 'public')
            else:
                org_ids: List[uuid.UUID] = []
                for m in (current_user.get('memberships') or []):
                    try:
                        org_ids.append(uuid.UUID(m.get('organization_id')))
                    except Exception:
                        pass
                base_query = base_query.filter(
                    or_(
                        models.MemoryBlock.visibility_scope == 'public',
                        models.MemoryBlock.owner_user_id == current_user.get('id'),
                        and_(
                            models.MemoryBlock.visibility_scope == 'organization',
                            models.MemoryBlock.organization_id.in_(org_ids) if org_ids else False,
                        ),
                    )
                )
            
            # Apply filters
            if agent_id:
                base_query = base_query.filter(models.MemoryBlock.agent_id == agent_id)
            
            if conversation_id:
                base_query = base_query.filter(models.MemoryBlock.conversation_id == conversation_id)
            
            # Handle archived filter
            if not include_archived:
                base_query = base_query.filter(
                    or_(
                        models.MemoryBlock.archived == False,
                        models.MemoryBlock.archived.is_(None)
                    )
                )
            
            # Order by relevance and limit
            results_with_rank = base_query.order_by(
                rank_expression.desc(),
                models.MemoryBlock.created_at.desc()  # Secondary sort for ties
            ).limit(limit).all()
            
            # Extract memory blocks and prepare results with scores
            memory_blocks_with_scores = []
            
            for memory_block, rank in results_with_rank:
                score = float(rank) if rank else 0.0
                memory_block_with_score = _create_memory_block_with_score(
                    memory_block, score, "fulltext", 
                    f"BM25 relevance score: {score:.4f}"
                )
                memory_blocks_with_scores.append(memory_block_with_score)
            
            search_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            metadata = {
                "total_search_time_ms": search_time,
                "fulltext_results_count": len(memory_blocks_with_scores),
                "query_terms": query.split(),
                "search_type": "fulltext",
                "min_score_threshold": min_score
            }
            
            self.logger.info(f"Full-text search for '{query}' returned {len(memory_blocks_with_scores)} results in {search_time:.2f}ms")
            
            return memory_blocks_with_scores, metadata
            
        except Exception as e:
            self.logger.error(f"Error in full-text search: {str(e)}")
            raise
    
    def search_memory_blocks_semantic(
        self,
        db: Session,
        query: str,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        similarity_threshold: float = 0.7,
        include_archived: bool = False,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """
        Placeholder for semantic search using embeddings.
        
        This is a stub implementation that will be enhanced when embedding infrastructure is ready.
        For now, it returns empty results with proper structure.
        """
        start_time = time.time()
        
        self.logger.info(f"Semantic search requested for query: '{query}'")
        self.logger.info("Semantic search not yet implemented - returning empty results")
        
        # TODO: Future implementation:
        # 1. Generate embedding for query using configured model
        # 2. Perform vector similarity search using pgvector or similar
        # 3. Apply filters and ranking
        # 4. Return scored results
        
        search_time = (time.time() - start_time) * 1000
        
        metadata = {
            "total_search_time_ms": search_time,
            "semantic_results_count": 0,
            "search_type": "semantic",
            "similarity_threshold": similarity_threshold,
            "implementation_status": "placeholder",
            "scores": []
        }
        
        return [], metadata
    
    def search_memory_blocks_hybrid(
        self,
        db: Session,
        query: str,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        fulltext_weight: float = 0.7,
        semantic_weight: float = 0.3,
        min_combined_score: float = 0.1,
        include_archived: bool = False,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """
        Combine full-text and semantic search with weighted scoring.
        
        Currently only uses full-text search until semantic search is implemented.
        """
        start_time = time.time()
        
        # Get results from both search methods
        fulltext_results, fulltext_metadata = self.search_memory_blocks_fulltext(
            db, query, agent_id, conversation_id, limit * 2,  # Get more for reranking
            min_score=0.01, include_archived=include_archived, current_user=current_user  # Lower threshold for hybrid
        )
        
        semantic_results, semantic_metadata = self.search_memory_blocks_semantic(
            db, query, agent_id, conversation_id, limit * 2,
            similarity_threshold=0.5, include_archived=include_archived, current_user=current_user
        )
        
        # If fulltext returned nothing (e.g., search_vector unpopulated), fall back to basic substring search
        if not fulltext_results:
            basic_results, _ = self._basic_search_fallback(
                db, query, agent_id, conversation_id, limit * 2, include_archived, current_user
            )
            fulltext_results = basic_results

        # Combine and rerank results
        combined_results = self._combine_and_rerank_with_scores(
            fulltext_results, semantic_results,
            fulltext_weight, semantic_weight, min_combined_score
        )
        
        # Limit final results
        final_results = combined_results[:limit]
        
        search_time = (time.time() - start_time) * 1000
        
        metadata = {
            "total_search_time_ms": search_time,
            "fulltext_results_count": len(fulltext_results),
            "semantic_results_count": len(semantic_results),
            "hybrid_weights": {
                "fulltext": fulltext_weight,
                "semantic": semantic_weight
            },
            "combined_results_count": len(final_results),
            "search_type": "hybrid",
            "min_combined_score": min_combined_score
        }
        
        self.logger.info(f"Hybrid search for '{query}' combined {len(fulltext_results)} fulltext + {len(semantic_results)} semantic results into {len(final_results)} final results")
        
        return final_results, metadata
    
    def _combine_and_rerank_with_scores(
        self,
        fulltext_results: List[schemas.MemoryBlockWithScore],
        semantic_results: List[schemas.MemoryBlockWithScore],
        fulltext_weight: float,
        semantic_weight: float,
        min_combined_score: float
    ) -> List[schemas.MemoryBlockWithScore]:
        """
        Combine results from multiple search methods and rerank by weighted score.
        """
        # Create score dictionaries
        fulltext_score_dict = {
            result.id: result.search_score for result in fulltext_results
        }
        semantic_score_dict = {
            result.id: result.search_score for result in semantic_results
        }
        
        # Get all unique memory blocks
        all_memory_blocks = {}
        for result in fulltext_results + semantic_results:
            all_memory_blocks[result.id] = result
        
        # Calculate combined scores
        scored_results = []
        for memory_id, memory_block in all_memory_blocks.items():
            fulltext_score = fulltext_score_dict.get(memory_id, 0.0)
            semantic_score = semantic_score_dict.get(memory_id, 0.0)
            
            # Normalize scores (both should be 0-1 range)
            normalized_fulltext = min(1.0, max(0.0, fulltext_score))
            normalized_semantic = min(1.0, max(0.0, semantic_score))
            
            # Calculate weighted combined score
            combined_score = (
                normalized_fulltext * fulltext_weight + 
                normalized_semantic * semantic_weight
            )
            
            if combined_score >= min_combined_score:
                # Create new MemoryBlockWithScore with combined score
                # Extract base memory block data from the MemoryBlockWithScore
                base_data = {k: v for k, v in memory_block.model_dump().items() 
                           if k not in ['search_score', 'search_type', 'rank_explanation']}
                
                combined_result = schemas.MemoryBlockWithScore(
                    **base_data,
                    search_score=combined_score,
                    search_type="hybrid",
                    rank_explanation=f"Hybrid score: {combined_score:.4f} (fulltext: {normalized_fulltext:.4f} * {fulltext_weight}, semantic: {normalized_semantic:.4f} * {semantic_weight})"
                )
                scored_results.append((combined_result, combined_score))
        
        # Sort by combined score (descending)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the memory blocks with scores
        return [result[0] for result in scored_results]
    
    def _combine_and_rerank(
        self,
        fulltext_results: List[models.MemoryBlock],
        semantic_results: List[models.MemoryBlock],
        fulltext_scores: List[float],
        semantic_scores: List[float],
        fulltext_weight: float,
        semantic_weight: float,
        min_combined_score: float
    ) -> List[models.MemoryBlock]:
        """
        Combine results from multiple search methods and rerank by weighted score.
        """
        # Create score dictionaries
        fulltext_score_dict = {
            result.id: score for result, score in zip(fulltext_results, fulltext_scores)
        }
        semantic_score_dict = {
            result.id: score for result, score in zip(semantic_results, semantic_scores)
        }
        
        # Get all unique memory blocks
        all_memory_blocks = {}
        for result in fulltext_results + semantic_results:
            all_memory_blocks[result.id] = result
        
        # Calculate combined scores
        scored_results = []
        for memory_id, memory_block in all_memory_blocks.items():
            fulltext_score = fulltext_score_dict.get(memory_id, 0.0)
            semantic_score = semantic_score_dict.get(memory_id, 0.0)
            
            # Normalize scores (both should be 0-1 range)
            normalized_fulltext = min(1.0, max(0.0, fulltext_score))
            normalized_semantic = min(1.0, max(0.0, semantic_score))
            
            # Calculate weighted combined score
            combined_score = (
                normalized_fulltext * fulltext_weight + 
                normalized_semantic * semantic_weight
            )
            
            if combined_score >= min_combined_score:
                scored_results.append((memory_block, combined_score))
        
        # Sort by combined score (descending)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the memory blocks
        return [result[0] for result in scored_results]
    
    def enhanced_search_memory_blocks(
        self,
        db: Session,
        search_query: Optional[str] = None,
        search_type: str = "basic",
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        include_archived: bool = False,
        **search_params
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """
        Enhanced search method that supports multiple search types.
        
        Args:
            db: Database session
            search_type: Type of search ("basic", "fulltext", "semantic", "hybrid")
            search_query: Search query string
            agent_id: Optional agent filter
            conversation_id: Optional conversation filter
            limit: Maximum number of results
            include_archived: Whether to include archived blocks
            **search_params: Additional search parameters
            
        Returns:
            Tuple of (results, metadata)
        """
        if not search_query or search_query.strip() == "":
            # Return empty results for empty queries
            return [], {"search_type": search_type, "message": "Empty query"}
        
        if search_type == "fulltext":
            return self.search_memory_blocks_fulltext(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("min_score", 0.1), include_archived
            )
        elif search_type == "semantic":
            return self.search_memory_blocks_semantic(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("similarity_threshold", 0.7), include_archived
            )
        elif search_type == "hybrid":
            return self.search_memory_blocks_hybrid(
                db, search_query, agent_id, conversation_id,
                limit, search_params.get("fulltext_weight", 0.7),
                search_params.get("semantic_weight", 0.3),
                search_params.get("min_combined_score", 0.1), include_archived
            )
        else:
            # Fall back to basic search (existing ILIKE implementation)
            return self._basic_search_fallback(
                db, search_query, agent_id, conversation_id, limit, include_archived, search_params.get('current_user')
            )
    
    def _basic_search_fallback(
        self,
        db: Session,
        search_query: str,
        agent_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        include_archived: bool = False,
        current_user: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[schemas.MemoryBlockWithScore], Dict[str, Any]]:
        """
        Fallback to basic ILIKE search for backward compatibility.
        """
        start_time = time.time()
        
        # Build search filters using ILIKE (case-insensitive substring search)
        search_filters = []
        search_terms = search_query.split()
        
        for term in search_terms:
            term_filter = or_(
                models.MemoryBlock.content.ilike(f"%{term}%"),
                models.MemoryBlock.errors.ilike(f"%{term}%"),
                models.MemoryBlock.lessons_learned.ilike(f"%{term}%"),
                models.MemoryBlock.id.cast(models.String).ilike(f"%{term}%")
            )
            search_filters.append(term_filter)
        
        # Combine all search filters with AND logic
        combined_filter = and_(*search_filters) if search_filters else None
        
        query = db.query(models.MemoryBlock)
        
        if combined_filter is not None:
            query = query.filter(combined_filter)
        
        # Apply scope filters
        if current_user is None:
            query = query.filter(models.MemoryBlock.visibility_scope == 'public')
        else:
            org_ids: List[uuid.UUID] = []
            for m in (current_user.get('memberships') or []):
                try:
                    org_ids.append(uuid.UUID(m.get('organization_id')))
                except Exception:
                    pass
            query = query.filter(
                or_(
                    models.MemoryBlock.visibility_scope == 'public',
                    models.MemoryBlock.owner_user_id == current_user.get('id'),
                    and_(
                        models.MemoryBlock.visibility_scope == 'organization',
                        models.MemoryBlock.organization_id.in_(org_ids) if org_ids else False,
                    ),
                )
            )

        # Apply additional filters
        if agent_id:
            query = query.filter(models.MemoryBlock.agent_id == agent_id)
        
        if conversation_id:
            query = query.filter(models.MemoryBlock.conversation_id == conversation_id)
        
        # Handle archived filter
        if not include_archived:
            query = query.filter(
                or_(
                    models.MemoryBlock.archived == False,
                    models.MemoryBlock.archived.is_(None)
                )
            )
        
        # Order by creation date and limit
        raw_results = query.order_by(
            models.MemoryBlock.created_at.desc()
        ).limit(limit).all()
        
        # Convert to MemoryBlockWithScore objects
        results = []
        for i, memory_block in enumerate(raw_results):
            # Basic search doesn't have a real score, so use inverted rank
            score = 1.0 - (i / (len(raw_results) + 1))  # Score from 1.0 to close to 0
            result_with_score = _create_memory_block_with_score(
                memory_block, score, "basic",
                f"Basic search result rank: {i+1}"
            )
            results.append(result_with_score)
        
        search_time = (time.time() - start_time) * 1000
        
        metadata = {
            "total_search_time_ms": search_time,
            "basic_results_count": len(results),
            "search_type": "basic",
            "search_terms": search_terms
        }
        
        return results, metadata


# Global search service instance
_search_service = None


def get_search_service() -> SearchService:
    """Get or create the global search service instance."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
