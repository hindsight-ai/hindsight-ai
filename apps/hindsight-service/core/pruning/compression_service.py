"""
Memory Compression Service for Hindsight AI

This service implements LLM-based compression of memory blocks.
It uses Google Gemini API to generate condensed versions of memory content
while preserving critical information and insights.

The service works with individual memory blocks and provides human-in-the-loop
review and approval workflow similar to consolidation suggestions.
"""

import os
import json
import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import requests
from datetime import datetime

from core.db.crud import get_memory_block

# Configure logging
logger = logging.getLogger(__name__)

class CompressionService:
    """Service for compressing memory blocks using LLM evaluation."""

    def __init__(self, llm_api_key: str = None):
        """
        Initialize the compression service.

        Args:
            llm_api_key: API key for the LLM service (Google Gemini)
        """
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY")
        self.llm_model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash-preview-05-20")

    def compress_memory_block(self, db: Session, memory_id: uuid.UUID, user_instructions: str = "") -> Dict[str, Any]:
        """
        Compress a single memory block using LLM.

        Args:
            db: Database session
            memory_id: UUID of the memory block to compress
            user_instructions: Optional user instructions for compression

        Returns:
            Dictionary containing compression results
        """
        if not self.llm_api_key:
            logger.warning("LLM_API_KEY not available, cannot perform compression")
            return {
                "error": "LLM service not available",
                "message": "LLM_API_KEY is not configured"
            }

        # Retrieve the memory block
        memory_block = get_memory_block(db, memory_id)
        if not memory_block:
            return {
                "error": "Memory block not found",
                "message": f"Memory block {memory_id} does not exist"
            }

        try:
            from google import genai

            # Initialize the Gemini client with API key
            client = genai.Client(api_key=self.llm_api_key)

            # Create compression prompt
            prompt = self._create_compression_prompt(memory_block, user_instructions)

            # Define structured JSON schema for response
            response_schema = {
                "type": "object",
                "properties": {
                    "compressed_content": {"type": "string"},
                    "compressed_lessons_learned": {"type": "string"},
                    "compression_ratio": {"type": "number", "minimum": 0, "maximum": 1},
                    "key_insights_preserved": {"type": "array", "items": {"type": "string"}},
                    "compression_quality_score": {"type": "integer", "minimum": 1, "maximum": 10},
                    "rationale": {"type": "string"}
                },
                "required": [
                    "compressed_content",
                    "compressed_lessons_learned",
                    "compression_ratio",
                    "key_insights_preserved",
                    "compression_quality_score",
                    "rationale"
                ]
            }

            # Make LLM call for compression
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
            result_text = response.text if response.text else "{}"
            try:
                compression_result = json.loads(result_text)

                # Validate compression results
                original_content_length = len(memory_block.content or "")
                original_lessons_length = len(memory_block.lessons_learned or "")
                compressed_content_length = len(compression_result.get("compressed_content", ""))
                compressed_lessons_length = len(compression_result.get("compressed_lessons_learned", ""))

                # Calculate actual compression ratio
                total_original = original_content_length + original_lessons_length
                total_compressed = compressed_content_length + compressed_lessons_length
                actual_ratio = total_compressed / total_original if total_original > 0 else 1.0

                # Ensure compressed content is actually shorter
                if actual_ratio >= 1.0:
                    logger.warning(f"Compression did not reduce content size for memory {memory_id}")
                    return {
                        "error": "Compression failed",
                        "message": "LLM did not produce shorter content"
                    }

                # Return successful compression result
                return {
                    "memory_id": str(memory_id),
                    "original_content": memory_block.content,
                    "original_lessons_learned": memory_block.lessons_learned,
                    "compressed_content": compression_result.get("compressed_content", ""),
                    "compressed_lessons_learned": compression_result.get("compressed_lessons_learned", ""),
                    "compression_ratio": actual_ratio,
                    "key_insights_preserved": compression_result.get("key_insights_preserved", []),
                    "compression_quality_score": compression_result.get("compression_quality_score", 5),
                    "rationale": compression_result.get("rationale", ""),
                    "user_instructions": user_instructions,
                    "timestamp": datetime.utcnow().isoformat()
                }

            except json.JSONDecodeError as parse_error:
                logger.error(f"Failed to parse LLM compression response: {str(parse_error)}")
                logger.error(f"Response content: {result_text}")
                return {
                    "error": "LLM response parsing failed",
                    "message": "Could not parse compression results"
                }

        except Exception as e:
            logger.error(f"LLM compression failed: {str(e)}")
            return {
                "error": "Compression service error",
                "message": f"LLM compression failed: {str(e)}"
            }

    def _create_compression_prompt(self, memory_block, user_instructions: str = "") -> str:
        """Create a detailed prompt for memory block compression."""

        # Extract keywords for context
        keywords = [kw.keyword_text for kw in memory_block.keywords] if hasattr(memory_block, 'keywords') else []

        prompt = f"""You are an expert AI assistant specializing in content compression and information distillation. Your task is to compress a memory block while preserving all critical information, insights, and lessons learned.

MEMORY BLOCK TO COMPRESS:
ID: {memory_block.id}
Created: {memory_block.created_at}
Agent: {memory_block.agent_id}

ORIGINAL CONTENT:
{memory_block.content or 'No content available'}

ORIGINAL LESSONS LEARNED:
{memory_block.lessons_learned or 'No lessons learned available'}

KEYWORDS: {', '.join(keywords) if keywords else 'None'}

METADATA: {json.dumps(memory_block.metadata_col or {}, indent=2, default=str)}

{f'ADDITIONAL USER INSTRUCTIONS: {user_instructions}' if user_instructions else ''}

COMPRESSION REQUIREMENTS:

1. **Content Density**: Create a more condensed version that removes verbosity, redundancy, and unnecessary details while preserving:
   - Critical technical information
   - Key insights and observations
   - Actionable lessons learned
   - Important context and background
   - Essential error details and solutions

2. **Quality Preservation**: Ensure the compressed version maintains:
   - All critical insights and learnings
   - Technical accuracy
   - Problem-solving context
   - Decision-making rationale

3. **Length Optimization**: The compressed content should be significantly shorter (aim for 30-70% reduction) but never exceed the original length.

4. **Structure Maintenance**: Keep logical flow and important relationships between concepts.

IMPORTANT CONSTRAINTS:
- Compressed content MUST be shorter than original
- Never remove critical technical details, error information, or key insights
- Maintain professional tone and technical accuracy
- Preserve all actionable information

Provide your response in JSON format with the following structure:
{{
  "compressed_content": "The condensed version of the content",
  "compressed_lessons_learned": "The condensed version of lessons learned",
  "compression_ratio": 0.65,
  "key_insights_preserved": ["List of key insights that were preserved"],
  "compression_quality_score": 8,
  "rationale": "Explanation of compression decisions and what was preserved/removed"
}}

Focus on creating a high-quality, information-dense version that maintains all value while reducing verbosity."""

        return prompt

# Convenience function for direct use
def get_compression_service(llm_api_key: str = None):
    """Get an instance of the compression service."""
    return CompressionService(llm_api_key)
