import pytest
from core.db.database import SessionLocal, engine
from core.db import models, schemas, crud


@pytest.fixture(scope="module")
def db():
    models.Base.metadata.create_all(bind=engine)
    try:
        yield SessionLocal()
    finally:
        models.Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def clean(db):
    for table in reversed(models.Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def _user(db, email: str):
    u = models.User(email=email, display_name=email.split('@')[0])
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _org(db, name: str):
    o = models.Organization(name=name)
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def test_keyword_crud_personal(db):
    user = _user(db, "kwowner@example.com")
    kw = crud.create_keyword(db, schemas.KeywordCreate(keyword_text="apple", visibility_scope="personal", owner_user_id=user.id))
    assert kw.keyword_text == "apple"

    fetched = crud.get_keyword(db, kw.keyword_id)
    assert fetched.keyword_id == kw.keyword_id

    crud.update_keyword(db, kw.keyword_id, schemas.KeywordUpdate(keyword_text="banana"))
    assert crud.get_keyword(db, kw.keyword_id).keyword_text == "banana"

    crud.delete_keyword(db, kw.keyword_id)
    assert crud.get_keyword(db, kw.keyword_id) is None


def test_keyword_crud_org_and_conflict_lookup(db):
    org = _org(db, "KOrg")
    # create org keyword
    kw1 = crud.create_keyword(db, schemas.KeywordCreate(keyword_text="shared", visibility_scope="organization", organization_id=org.id))
    assert kw1.organization_id == org.id
    # conflict-style lookup by text (helper returns first match)
    found = crud.get_scoped_keyword_by_text(db, keyword_text="shared", visibility_scope="organization", organization_id=org.id)
    assert found is not None
    assert found.keyword_id == kw1.keyword_id
