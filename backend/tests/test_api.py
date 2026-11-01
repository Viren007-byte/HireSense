import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import Base, app, db_session, match


@pytest.fixture
def client():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    def test_db():
        with sessions() as db:
            yield db
    app.dependency_overrides[db_session] = test_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def account(client, email='recruiter@example.com'):
    credentials = {'email': email, 'password': 'RecruiterPass123!'}
    assert client.post('/auth/register', json=credentials).status_code == 201
    response = client.post('/auth/login', json=credentials)
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['access_token']}


def job(client, headers):
    response = client.post('/jobs', headers=headers, json={
        'title': 'Backend developer', 'description': 'Build backend services.',
        'skills': ['Python', 'sql', 'docker', 'python'],
    })
    assert response.status_code == 201
    assert response.json()['skills'] == ['docker', 'python', 'sql']
    return response.json()['id']


def test_health(client):
    assert client.get('/health').json() == {'status': 'ok'}


def test_match():
    assert match('Python and SQL developer', ['python', 'sql', 'docker']) == (
        66.67, ['python', 'sql'], ['docker'])
    assert match('javascript', ['java'])[0] == 0


def test_authentication(client):
    assert client.get('/jobs').status_code == 401
    account(client)
    credentials = {'email': 'recruiter@example.com', 'password': 'RecruiterPass123!'}
    assert client.post('/auth/register', json=credentials).status_code == 409
    credentials['password'] = 'IncorrectPass123'
    assert client.post('/auth/login', json=credentials).status_code == 401
    assert client.get('/jobs', headers={'Authorization': 'Bearer invalid'}).status_code == 401


def test_expired_token(client):
    import jwt
    from app.main import SECRET_KEY

    account(client)
    token = jwt.encode({'sub': '1', 'exp': 0}, SECRET_KEY, algorithm='HS256')
    response = client.get('/jobs', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 401


def test_email_normalization(client):
    account(client, 'Recruiter@Example.com')
    response = client.post('/auth/login', json={
        'email': ' recruiter@example.com ', 'password': 'RecruiterPass123!',
    })
    assert response.status_code == 200


@pytest.mark.parametrize('email,password', [
    ('invalid', 'RecruiterPass123!'), ('a@b', 'RecruiterPass123!'),
    ('valid@example.com', 'short'), ('valid@example.com', chr(0x1f600) * 20),
])
def test_invalid_credentials(client, email, password):
    assert client.post('/auth/register', json={
        'email': email, 'password': password}).status_code == 422


def test_candidate_workflow_and_ownership(client):
    owner = account(client)
    job_id = job(client, owner)
    response = client.post('/candidates/upload', headers=owner, data={'job_id': job_id},
                           files={'file': ('resume.txt', b'Python SQL developer')})
    assert response.status_code == 201
    candidate = response.json()
    assert candidate['score'] == 66.67
    assert candidate['missing_skills'] == ['docker']
    path = f"/candidates/{candidate['id']}"
    assert client.patch(path, headers=owner, json={'status': 'Unknown'}).status_code == 422
    assert client.patch(path, headers=owner, json={'status': 'Shortlisted'}).status_code == 200
    assert client.get('/analytics', headers=owner).json() == {
        'total_candidates': 1, 'shortlisted': 1, 'average_match_score': 66.67}
    outsider = account(client, 'other@example.com')
    assert client.get('/jobs', headers=outsider).json() == []
    assert client.get('/candidates', headers=outsider).json() == []
    assert client.patch(path, headers=outsider, json={'status': 'Rejected'}).status_code == 404
    assert client.delete(f'/jobs/{job_id}', headers=outsider).status_code == 404
    assert client.post('/candidates/upload', headers=outsider, data={'job_id': job_id},
                       files={'file': ('resume.txt', b'Python')}).status_code == 404
    assert client.delete(f'/jobs/{job_id}', headers=owner).status_code == 200
    assert client.get('/candidates', headers=owner).json() == []
    assert client.get('/analytics', headers=owner).json()['total_candidates'] == 0


@pytest.mark.parametrize('filename,content,expected', [
    ('resume.exe', b'Python', 400), ('resume.txt', b'   ', 400),
    ('resume.pdf', b'not a pdf', 400),
    ('resume.txt', b'a' * (2 * 1024 * 1024 + 1), 413),
])
def test_upload_validation(client, filename, content, expected):
    headers = account(client)
    job_id = job(client, headers)
    response = client.post('/candidates/upload', headers=headers,
                           data={'job_id': job_id}, files={'file': (filename, content)})
    assert response.status_code == expected
