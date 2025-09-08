import uuid
from core.db import models, crud, schemas


def test_update_and_delete_keyword(db_session):
    db = db_session
    user = models.User(email=f"kw_{uuid.uuid4().hex}@ex.com", display_name="KWUser", is_superadmin=False)
    db.add(user); db.commit(); db.refresh(user)

    kw = models.Keyword(keyword_text=f"kw_{uuid.uuid4().hex[:6]}", visibility_scope="personal", owner_user_id=user.id)
    db.add(kw); db.commit(); db.refresh(kw)

    upd = schemas.KeywordUpdate(visibility_scope="public") if hasattr(schemas, 'KeywordUpdate') else None
    if upd:
        updated = crud.update_keyword(db, kw.keyword_id, upd)
        assert updated.visibility_scope == "public"

    # Delete
    deleted = crud.delete_keyword(db, kw.keyword_id)
    assert deleted.keyword_id == kw.keyword_id
    # Double delete returns None
    assert crud.delete_keyword(db, kw.keyword_id) is None
