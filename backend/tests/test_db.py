from sqlalchemy import select

from app.db.models import Messages, Repositories, Sessions, ShareableLinks, Users


def test_create_user(db):
    user = Users(github_id="999", username="testuser", email="pytest@test.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None
    assert user.github_id == "999"
    assert user.username == "testuser"
    assert user.email == "pytest@test.com"


def test_read_user(db):
    user = Users(github_id="998", username="readuser", email="readuser@test.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    fetched = db.execute(select(Users).where(Users.github_id == "998")).scalar_one()
    assert fetched.username == "readuser"
    assert fetched.email == "readuser@test.com"


def test_create_repo(db):
    repo = Repositories(
        owner="testowner",
        name="testrepo",
        url="https://github.com/testowner/testrepo",
        commit_hash="abc123",
        status="pending",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    assert repo.id is not None
    assert repo.status == "pending"
    assert repo.owner == "testowner"


def test_create_session(db):
    user = Users(github_id="997", username="sessionuser", email="sess@test.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    repo = Repositories(
        owner="sowner", name="srepo", url="https://github.com/sowner/srepo", status="pending"
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    session = Sessions(user_id=user.id, repo_id=repo.id, title="My Session")
    db.add(session)
    db.commit()
    db.refresh(session)

    assert session.id is not None
    assert session.user_id == user.id
    assert session.repo_id == repo.id
    assert session.title == "My Session"
    assert session.created_at is not None
    assert session.last_active_at is not None


def test_create_message(db):
    user = Users(github_id="996", username="msguser", email="msg@test.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    repo = Repositories(
        owner="mowner", name="mrepo", url="https://github.com/mowner/mrepo", status="pending"
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    session = Sessions(user_id=user.id, repo_id=repo.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    msg = Messages(session_id=session.id, role="user", content="Hello, world!")
    db.add(msg)
    db.commit()
    db.refresh(msg)

    assert msg.id is not None
    assert msg.role == "user"
    assert msg.content == "Hello, world!"
    assert msg.created_at is not None


def test_create_shareable_link(db):
    user = Users(github_id="995", username="linkuser", email="link@test.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    repo = Repositories(
        owner="lowner", name="lrepo", url="https://github.com/lowner/lrepo", status="completed"
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    session = Sessions(user_id=user.id, repo_id=repo.id)
    db.add(session)
    db.commit()
    db.refresh(session)

    link = ShareableLinks(session_id=session.id, created_by=user.id, token="abc123tok")
    db.add(link)
    db.commit()
    db.refresh(link)

    assert link.id is not None
    assert link.token == "abc123tok"
    assert link.created_by == user.id
    assert link.session_id == session.id
