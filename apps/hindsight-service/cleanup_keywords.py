"""
Maintenance script to normalize and de-duplicate keywords.

Finds canonical forms, re-associates memory relations, and prunes duplicates
to keep keyword taxonomy clean.
"""
import sys
import os
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict

# Add the src directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from core.db.database import SessionLocal, engine
from core.db import models, crud

def cleanup_existing_keywords():
    db: Session = SessionLocal()
    try:
        print("Starting keyword cleanup...")

        # Pass 1: Identify canonical keywords and duplicates, and prepare updates/deletions
        all_keywords = db.query(models.Keyword).all()
        
        # Map processed text to the ID of the keyword that will be the canonical one
        # { "processed_text": canonical_keyword_id }
        processed_text_to_canonical_id = {}
        
        # Store IDs of keywords that will be deleted (duplicates)
        keywords_to_delete_ids = set()
        
        # Store {keyword_id: new_text} for canonical keywords whose text needs updating
        keywords_to_update_text = {}

        # First, establish canonical IDs and mark duplicates for deletion/re-association
        for keyword in all_keywords:
            original_text = keyword.keyword_text
            processed_text = original_text.strip().rstrip('.')

            if processed_text not in processed_text_to_canonical_id:
                # This is the first time we've seen this processed_text, so this keyword becomes canonical
                processed_text_to_canonical_id[processed_text] = keyword.keyword_id
                if original_text != processed_text:
                    keywords_to_update_text[keyword.keyword_id] = processed_text
                    print(f"  Marking '{original_text}' (ID: {keyword.keyword_id}) to be updated to '{processed_text}'")
            else:
                # This processed_text already has a canonical keyword, so this one is a duplicate
                canonical_id = processed_text_to_canonical_id[processed_text]
                if keyword.keyword_id != canonical_id: # Ensure it's not the same keyword
                    print(f"  '{original_text}' (ID: {keyword.keyword_id}) will be merged into '{processed_text}' (ID: {canonical_id})")
                    keywords_to_delete_ids.add(keyword.keyword_id)
                    
                    # Re-associate MemoryBlockKeyword entries for this duplicate keyword
                    # This update must happen before the duplicate keyword is deleted
                    db.query(models.MemoryBlockKeyword).filter(
                        models.MemoryBlockKeyword.keyword_id == keyword.keyword_id
                    ).update(
                        {models.MemoryBlockKeyword.keyword_id: canonical_id},
                        synchronize_session=False # Important for bulk updates
                    )
        
        # Pass 2: Perform database operations in a safe order
        
        # 1. Delete all duplicate keywords
        if keywords_to_delete_ids:
            print(f"  Deleting {len(keywords_to_delete_ids)} duplicate keywords...")
            db.query(models.Keyword).filter(
                models.Keyword.keyword_id.in_(list(keywords_to_delete_ids))
            ).delete(synchronize_session=False)
            print("  Duplicate keywords deleted.")
        else:
            print("  No duplicate keywords to delete.")

        # 2. Update the text of canonical keywords
        if keywords_to_update_text:
            print(f"  Updating {len(keywords_to_update_text)} canonical keywords...")
            for keyword_id, new_text in keywords_to_update_text.items():
                db.query(models.Keyword).filter(
                    models.Keyword.keyword_id == keyword_id
                ).update(
                    {models.Keyword.keyword_text: new_text},
                    synchronize_session=False # Important for bulk updates
                )
            print("  Canonical keywords updated.")
        else:
            print("  No canonical keywords to update.")

        db.commit()
        print("Keyword cleanup completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"An error occurred during keyword cleanup: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_existing_keywords()
