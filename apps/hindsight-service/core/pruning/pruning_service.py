"""
Memory Pruning Service for Hindsight AI

This service implements an LLM-based approach to evaluate memory blocks for pruning.
It uses Google Gemini API with structured JSON output to assess the usefulness and 
importance of memory blocks, generating pruning suggestions that require human review 
and confirmation.

The service works in batches (default 20) to avoid performance issues and integrates 
with the existing human-in-the-loop workflow pattern used by consolidation suggestions.
"""

import os
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import requests
from datetime import datetime

from core.db.crud import get_all_memory_blocks
from core.db.models import MemoryBlock

# Configure logging
logger = logging.getLogger(__name__)

# Configuration settings - Reduced batch size to 20 for better LLM performance
DEFAULT_BATCH_SIZE = int(os.getenv("PRUNING_BATCH_SIZE", 20))
DEFAULT_MAX_ITERATIONS = int(os.getenv("PRUNING_MAX_ITERATIONS", 10))

class PruningService:
    """Service for evaluating and suggesting memory blocks for pruning using batch processing."""
    
    def __init__(self, llm_api_key: str = None):
        """
        Initialize the pruning service.
        
        Args:
            llm_api_key: API key for the LLM service (Google Gemini)
        """
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY")
        self.llm_model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash-preview-05-20")
        
    def get_random_memory_blocks(self, db: Session, batch_size: int = DEFAULT_BATCH_SIZE, exclude_ids: set = None) -> List[Dict[str, Any]]:
        """
        Retrieve a random batch of non-archived memory blocks for evaluation.
        
        Args:
            db: Database session
            batch_size: Number of memory blocks to retrieve (default 20)
            exclude_ids: Set of memory block IDs to exclude from selection
            
        Returns:
            List of memory block dictionaries
        """
        try:
            # Build query for non-archived memory blocks
            query = db.query(MemoryBlock).filter(MemoryBlock.archived == False)
            
            # Exclude previously selected blocks
            if exclude_ids:
                query = query.filter(~MemoryBlock.id.in_(exclude_ids))
            
            # Get random blocks using ORDER BY RANDOM() and limit
            memory_blocks = query.order_by(func.random()).limit(batch_size).all()
            
            logger.info(f"Retrieved {len(memory_blocks)} random memory blocks for pruning evaluation")
            
            # Convert to dictionary format for processing
            blocks_data = []
            for block in memory_blocks:
                block_dict = {
                    "id": str(block.id),
                    "agent_id": str(block.agent_id),
                    "conversation_id": str(block.conversation_id),
                    "content": block.content or "",
                    "lessons_learned": block.lessons_learned or "",
                    "metadata_col": block.metadata_col or {},
                    "feedback_score": block.feedback_score or 0,
                    "retrieval_count": block.retrieval_count or 0,
                    "created_at": block.created_at.isoformat() if block.created_at else None,
                    "updated_at": block.updated_at.isoformat() if block.updated_at else None,
                    "keywords": [kw.keyword_text for kw in block.keywords] if hasattr(block, 'keywords') else []
                }
                blocks_data.append(block_dict)
            
            return blocks_data
        except Exception as e:
            logger.error(f"Error retrieving random memory blocks: {str(e)}")
            return []
    
    def evaluate_memory_blocks_with_llm(self, memory_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use LLM to evaluate memory blocks and assign pruning priority scores using batch processing.
        
        Args:
            memory_blocks: List of memory block dictionaries to evaluate
            
        Returns:
            List of memory blocks with added pruning scores and rationale
        """
        if not memory_blocks:
            logger.warning("No memory blocks to evaluate")
            return []
        
        if not self.llm_api_key:
            logger.warning("LLM_API_KEY not available, using fallback scoring")
            return self._fallback_scoring(memory_blocks)
        
        try:
            from google import genai
            
            # Initialize the Gemini client with API key
            client = genai.Client(api_key=self.llm_api_key)
            
            # Create batch prompt with all memory blocks
            prompt = self._create_batch_evaluation_prompt(memory_blocks)
            
            # Define structured JSON schema for response
            response_schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "memory_block_id": {"type": "string"},
                        "criticality_score": {"type": "integer", "minimum": 1, "maximum": 10},
                        "information_value_score": {"type": "integer", "minimum": 1, "maximum": 10},
                        "redundancy_score": {"type": "integer", "minimum": 1, "maximum": 10},
                        "temporal_relevance_score": {"type": "integer", "minimum": 1, "maximum": 10},
                        "pruning_priority_score": {"type": "integer", "minimum": 1, "maximum": 100},
                        "rationale": {"type": "string"}
                    },
                    "required": [
                        "memory_block_id",
                        "criticality_score",
                        "information_value_score",
                        "redundancy_score",
                        "temporal_relevance_score",
                        "pruning_priority_score",
                        "rationale"
                    ],
                    "propertyOrdering": [
                        "memory_block_id",
                        "criticality_score",
                        "information_value_score",
                        "redundancy_score",
                        "temporal_relevance_score",
                        "pruning_priority_score",
                        "rationale"
                    ]
                }
            }
            
            # Make single LLM call for entire batch with structured output
            response = client.models.generate_content(
                model=self.llm_model_name,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": response_schema,
                    "temperature": 0.3
                }
            )
            
            # Parse the structured JSON response
            result_text = response.text if response.text else "[]"
            try:
                evaluation_results = json.loads(result_text)
                
                # Create lookup dictionary for quick access
                evaluation_lookup = {result["memory_block_id"]: result for result in evaluation_results}
                
                # Apply scores to memory blocks
                evaluated_blocks = []
                for block in memory_blocks:
                    block_id = block["id"]
                    
                    if block_id in evaluation_lookup:
                        evaluation_data = evaluation_lookup[block_id]
                        
                        # Calculate final pruning score (lower = higher priority for pruning)
                        pruning_score = evaluation_data.get("pruning_priority_score", 50)
                        
                        evaluated_block = {
                            **block,
                            "pruning_score": pruning_score,
                            "pruning_rationale": evaluation_data.get("rationale", ""),
                            "criticality_score": evaluation_data.get("criticality_score", 5),
                            "information_value_score": evaluation_data.get("information_value_score", 5),
                            "redundancy_score": evaluation_data.get("redundancy_score", 5),
                            "temporal_relevance_score": evaluation_data.get("temporal_relevance_score", 5)
                        }
                        
                        evaluated_blocks.append(evaluated_block)
                        logger.info(f"Evaluated memory block {block_id} with pruning score: {pruning_score}")
                    else:
                        # Fallback for blocks not in LLM response
                        logger.warning(f"Block {block_id} not found in LLM response, using fallback scoring")
                        evaluated_blocks.append(self._fallback_score_block(block))
                
                # Sort by pruning score (ascending - lowest scores first for pruning)
                evaluated_blocks.sort(key=lambda x: x.get("pruning_score", 100))
                
                return evaluated_blocks
                
            except json.JSONDecodeError as parse_error:
                logger.error(f"Failed to parse LLM batch response: {str(parse_error)}")
                logger.error(f"Response content: {result_text}")
                return self._fallback_scoring(memory_blocks)
                
        except Exception as e:
            logger.error(f"LLM batch evaluation failed: {str(e)}. Using fallback scoring.")
            return self._fallback_scoring(memory_blocks)
    
    def _create_batch_evaluation_prompt(self, memory_blocks: List[Dict[str, Any]]) -> str:
        """Create a single prompt for batch evaluation of all memory blocks."""
        prompt = """You are an AI assistant tasked with evaluating multiple memory blocks for pruning priority. 
Analyze each memory block and assess its importance and usefulness.

For each memory block, evaluate it on the following criteria:

1. Criticality (1-10): Does this contain information about critical errors, security vulnerabilities, 
   system failures, or other high-priority issues? Higher scores indicate more critical information.

2. Information Value (1-10): Does this provide unique, actionable insights that improve system awareness? 
   Does it contain complex problem-solving processes or valuable knowledge? Higher scores indicate more value.

3. Redundancy (1-10): Is this information trivial, repetitive, or unhelpful (e.g., 'nothing special happened', 
   generic success messages)? Higher scores indicate more redundant/low-value content.

4. Temporal Relevance (1-10): Is this information still relevant or has it become outdated? 
   Does it reference obsolete systems or deprecated practices? Higher scores indicate more current relevance.

Based on these assessments, provide a final pruning priority score (1-100) where:
- Lower scores (1-30): High priority for pruning (low value, high redundancy, low criticality)
- Medium scores (31-70): Moderate priority for pruning 
- Higher scores (71-100): Low priority for pruning (high value, low redundancy, high criticality)

Here are the memory blocks to evaluate:
"""
        
        for i, block in enumerate(memory_blocks, 1):
            prompt += f"""

[BLOCK {i}]
Memory Block ID: {block['id']}
Created: {block['created_at']}

Content:
{block.get('content', '')[:2000]}

Lessons Learned:
{block.get('lessons_learned', '')[:1000]}

Metadata:
{json.dumps(block.get('metadata_col', {}), indent=2, default=str)}

Keywords:
{', '.join(block.get('keywords', [])[:20])}

Feedback Score: {block.get('feedback_score', 0)}
Retrieval Count: {block.get('retrieval_count', 0)}
"""
        
        prompt += """

IMPORTANT: Respond ONLY in JSON array format with one object per memory block, following this exact structure:
[
  {
    "memory_block_id": "uuid-string",
    "criticality_score": 7,
    "information_value_score": 8,
    "redundancy_score": 3,
    "temporal_relevance_score": 9,
    "pruning_priority_score": 25,
    "rationale": "Brief explanation of the scoring"
  },
  ...
]

Do not include any other text in your response. Ensure each memory block is evaluated and included in the response array.
"""
        
        return prompt
    
    def _fallback_scoring(self, memory_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback scoring method when LLM is unavailable."""
        logger.info("Using fallback scoring method")
        
        evaluated_blocks = []
        for block in memory_blocks:
            evaluated_block = self._fallback_score_block(block)
            evaluated_blocks.append(evaluated_block)
        
        # Sort by fallback score (ascending)
        evaluated_blocks.sort(key=lambda x: x.get("pruning_score", 100))
        return evaluated_blocks
    
    def _fallback_score_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate fallback score based on metadata factors."""
        # Simple heuristic scoring
        feedback_score = block.get("feedback_score", 0)
        retrieval_count = block.get("retrieval_count", 0)
        content_length = len(block.get("content", ""))
        lessons_length = len(block.get("lessons_learned", ""))
        
        # Age factor (older blocks get lower scores = higher pruning priority)
        created_at_str = block.get("created_at")
        age_factor = 1.0
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                age_days = (datetime.utcnow() - created_at).days
                # Older than 1 year gets penalty
                if age_days > 365:
                    age_factor = 0.7
                elif age_days > 180:
                    age_factor = 0.85
            except Exception:
                pass
        
        # Content quality factor (very short content = lower value)
        content_quality = 1.0
        if content_length < 100:
            content_quality = 0.5
        elif content_length < 500:
            content_quality = 0.8
        
        # Simple scoring formula
        base_score = (
            max(1, min(10, feedback_score + 5)) * 0.3 +  # Normalize feedback score
            min(10, retrieval_count * 0.1 + 1) * 0.3 +   # Retrieval count factor
            content_quality * 0.2 +                      # Content quality
            age_factor * 0.2                             # Age factor
        )
        
        # Convert to 1-100 scale
        pruning_score = int((10 - base_score) * 10)  # Invert so lower = higher pruning priority
        
        return {
            **block,
            "pruning_score": max(1, min(100, pruning_score)),
            "pruning_rationale": "Fallback scoring based on feedback score, retrieval count, content quality, and age",
            "criticality_score": max(1, min(10, feedback_score + 5)),
            "information_value_score": min(10, retrieval_count * 0.1 + 1),
            "redundancy_score": 10 if content_length > 100 else 3,
            "temporal_relevance_score": int(age_factor * 10)
        }
    
    def generate_pruning_suggestions(
        self,
        db: Session,
        batch_size: int = DEFAULT_BATCH_SIZE,
        target_count: Optional[int] = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS
    ) -> Dict[str, Any]:
        """
        Generate pruning suggestions by evaluating random memory blocks using batch processing.
        
        Args:
            db: Database session
            batch_size: Number of blocks to evaluate per batch (default 20)
            target_count: Target number of blocks to suggest for pruning
            max_iterations: Maximum number of iterations to run
            
        Returns:
            Dictionary containing suggestions and workflow information
        """
        logger.info(f"Generating pruning suggestions: batch_size={batch_size}, target_count={target_count}, max_iterations={max_iterations}")
        
        # Get random memory blocks for evaluation (limited to batch size of 20)
        actual_batch_size = min(batch_size, DEFAULT_BATCH_SIZE)
        memory_blocks = self.get_random_memory_blocks(db, actual_batch_size)
        
        if not memory_blocks:
            return {
                "suggestions": [],
                "message": "No memory blocks available for pruning evaluation",
                "batch_size": actual_batch_size,
                "target_count": target_count,
                "max_iterations": max_iterations
            }
        
        # Evaluate blocks with LLM using batch processing
        evaluated_blocks = self.evaluate_memory_blocks_with_llm(memory_blocks)
        
        # Select blocks with lowest pruning scores (highest priority for pruning)
        suggestions = evaluated_blocks[:min(actual_batch_size, len(evaluated_blocks))]
        
        # Filter to target count if specified
        if target_count:
            suggestions = suggestions[:min(target_count, len(suggestions))]
        
        # Format suggestions for API response
        formatted_suggestions = []
        for block in suggestions:
            formatted_suggestions.append({
                "memory_block_id": block["id"],
                "pruning_score": block.get("pruning_score", 50),
                "rationale": block.get("pruning_rationale", ""),
                "criticality_score": block.get("criticality_score", 5),
                "information_value_score": block.get("information_value_score", 5),
                "redundancy_score": block.get("redundancy_score", 5),
                "temporal_relevance_score": block.get("temporal_relevance_score", 5),
                "content_preview": block.get("content", "")[:200] + "..." if len(block.get("content", "")) > 200 else block.get("content", ""),
                "feedback_score": block.get("feedback_score", 0),
                "retrieval_count": block.get("retrieval_count", 0),
                "created_at": block.get("created_at")
            })
        
        return {
            "suggestions": formatted_suggestions,
            "total_evaluated": len(evaluated_blocks),
            "batch_size": actual_batch_size,
            "target_count": target_count,
            "max_iterations": max_iterations,
            "message": f"Generated {len(formatted_suggestions)} pruning suggestions"
        }

# Convenience function for direct use
def get_pruning_service(llm_api_key: str = None) -> PruningService:
    """Get an instance of the pruning service."""
    return PruningService(llm_api_key)
