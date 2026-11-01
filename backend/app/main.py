from datetime import datetime, timedelta, timezone
from io import BytesIO
import os, re
from pathlib import Path
import jwt
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from passlib.context import CryptContext
from pypdf import PdfReader
from docx import Document
BASE = Path(__file__).resolve().parents[1]
DATABASE_URL = os.getenv('DATABASE_URL', f"sqlite:///{BASE / 'hiresense.db'}")
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-change-this-before-deploying')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {})
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    skills = Column(Text, nullable=False)

class Candidate(Base):
    __tablename__ = 'candidates'
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    extracted_text = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    matched_skills = Column(Text, nullable=False)
    missing_skills = Column(Text, nullable=False)
    status = Column(String(30), default='New')
Base.metadata.create_all(engine)
app = FastAPI(title='HireSense Recruitment API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
oauth = OAuth2PasswordBearer(tokenUrl='/auth/login')
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')

def db_session():
    with SessionLocal() as db:
        yield db

def current_user(token: str=Depends(oauth), db: Session=Depends(db_session)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        uid = int(payload['sub'])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, 'Invalid token')
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, 'Invalid token')
    return user

class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=72)

    @field_validator('email')
    @classmethod
    def validate_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch('[^\\s@]+@[^\\s@]+\\.[^\\s@]+', value):
            raise ValueError('Enter a valid email address')
        return value

    @field_validator('password')
    @classmethod
    def validate_password_bytes(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be at most 72 UTF-8 bytes')
        return value

class JobIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10)
    skills: list[str] = Field(min_length=1)

class StatusIn(BaseModel):
    status: str

def normalize_skills(skills):
    return sorted(set((s.strip().lower() for s in skills if s.strip())))

def job_dict(j):
    return {'id': j.id, 'title': j.title, 'description': j.description, 'skills': j.skills.split('|')}

def candidate_dict(c):
    return {'id': c.id, 'job_id': c.job_id, 'filename': c.filename, 'score': c.score, 'matched_skills': c.matched_skills.split('|') if c.matched_skills else [], 'missing_skills': c.missing_skills.split('|') if c.missing_skills else [], 'status': c.status, 'preview': c.extracted_text[:450]}

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.post('/auth/register', status_code=201)
def register(body: Credentials, db: Session=Depends(db_session)):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, 'Email already registered')
    u = User(email=email, password_hash=pwd.hash(body.password))
    db.add(u)
    db.commit()
    return {'message': 'Account created'}

@app.post('/auth/login')
def login(body: Credentials, db: Session=Depends(db_session)):
    u = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not u or not pwd.verify(body.password, u.password_hash):
        raise HTTPException(401, 'Incorrect email or password')
    token = jwt.encode({'sub': str(u.id), 'exp': datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET_KEY, algorithm='HS256')
    return {'access_token': token, 'token_type': 'bearer'}

@app.get('/jobs')
def jobs(user: User=Depends(current_user), db: Session=Depends(db_session)):
    return [job_dict(j) for j in db.scalars(select(Job).where(Job.owner_id == user.id).order_by(Job.id.desc()))]

@app.post('/jobs', status_code=201)
def create_job(body: JobIn, user: User=Depends(current_user), db: Session=Depends(db_session)):
    skills = normalize_skills(body.skills)
    if not skills:
        raise HTTPException(422, 'At least one skill required')
    j = Job(owner_id=user.id, title=body.title, description=body.description, skills='|'.join(skills))
    db.add(j)
    db.commit()
    db.refresh(j)
    return job_dict(j)

@app.delete('/jobs/{job_id}')
def delete_job(job_id: int, user: User=Depends(current_user), db: Session=Depends(db_session)):
    j = db.get(Job, job_id)
    if not j or j.owner_id != user.id:
        raise HTTPException(404, 'Job not found')
    for c in db.scalars(select(Candidate).where(Candidate.job_id == j.id)):
        db.delete(c)
    db.delete(j)
    db.commit()
    return {'message': 'Deleted'}

def extract(filename, data):
    try:
        if filename.lower().endswith('.pdf'):
            return '\n'.join((page.extract_text() or '' for page in PdfReader(BytesIO(data)).pages))
        if filename.lower().endswith('.docx'):
            return '\n'.join((p.text for p in Document(BytesIO(data)).paragraphs))
        if filename.lower().endswith('.txt'):
            return data.decode('utf-8')
    except Exception:
        raise HTTPException(400, 'Cannot read this document')
    raise HTTPException(400, 'Only PDF, DOCX, and TXT files are supported')

def match(text, skills):
    matched = [s for s in skills if re.search('(?<!\\w)' + re.escape(s) + '(?!\\w)', text.lower())]
    missing = [s for s in skills if s not in matched]
    return (round(100 * len(matched) / len(skills), 2), matched, missing)

@app.post('/candidates/upload', status_code=201)
async def upload(job_id: int=Form(...), file: UploadFile=File(...), user: User=Depends(current_user), db: Session=Depends(db_session)):
    j = db.get(Job, job_id)
    if not j or j.owner_id != user.id:
        raise HTTPException(404, 'Job not found')
    if not file.filename or not file.filename.lower().endswith(('.pdf', '.docx', '.txt')):
        raise HTTPException(400, 'Only PDF, DOCX, TXT allowed')
    data = await file.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise HTTPException(413, 'Max file size is 2 MB')
    text = extract(file.filename, data).strip()
    if not text:
        raise HTTPException(400, 'No extractable text found')
    score, matched, missing = match(text, j.skills.split('|'))
    c = Candidate(owner_id=user.id, job_id=j.id, filename=Path(file.filename).name[:255], extracted_text=text[:100000], score=score, matched_skills='|'.join(matched), missing_skills='|'.join(missing))
    db.add(c)
    db.commit()
    db.refresh(c)
    return candidate_dict(c)

@app.get('/candidates')
def candidates(job_id: int | None=None, user: User=Depends(current_user), db: Session=Depends(db_session)):
    q = select(Candidate).where(Candidate.owner_id == user.id)
    if job_id is not None:
        q = q.where(Candidate.job_id == job_id)
    return [candidate_dict(c) for c in db.scalars(q.order_by(Candidate.score.desc(), Candidate.id.desc()))]

@app.patch('/candidates/{candidate_id}')
def update_status(candidate_id: int, body: StatusIn, user: User=Depends(current_user), db: Session=Depends(db_session)):
    if body.status not in ['New', 'Review', 'Shortlisted', 'Rejected']:
        raise HTTPException(422, 'Invalid status')
    c = db.get(Candidate, candidate_id)
    if not c or c.owner_id != user.id:
        raise HTTPException(404, 'Candidate not found')
    c.status = body.status
    db.commit()
    return candidate_dict(c)

@app.get('/analytics')
def analytics(user: User=Depends(current_user), db: Session=Depends(db_session)):
    cs = list(db.scalars(select(Candidate).where(Candidate.owner_id == user.id)))
    return {'total_candidates': len(cs), 'shortlisted': sum((c.status == 'Shortlisted' for c in cs)), 'average_match_score': round(sum((c.score for c in cs)) / len(cs), 2) if cs else 0}
