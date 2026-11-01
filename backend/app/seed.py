"""Create the local demo workspace: python -m app.seed."""

from sqlalchemy import select

from app.main import Candidate, Job, SessionLocal, User, match, normalize_skills, pwd

DEMO_EMAIL = 'demo@hiresense.local'
DEMO_PASSWORD = 'HireSenseDemo123!'

ROLES = [
    ('Backend Python Developer', 'Build and maintain recruitment APIs and database services.',
     ['python', 'fastapi', 'sql', 'docker'], [
         ('Aarav_Sharma.txt', 'Python developer experienced in FastAPI, SQL, Docker and REST APIs.', 'Shortlisted'),
         ('Meera_Patel.txt', 'Backend engineer working with Python, FastAPI and SQL databases.', 'Review'),
         ('Rohan_Desai.txt', 'Graduate developer with Python and Git project experience.', 'New'),
     ]),
    ('Frontend React Developer', 'Develop accessible, responsive interfaces for the recruitment dashboard.',
     ['react', 'javascript', 'css', 'typescript'], [
         ('Ananya_Rao.txt', 'Frontend developer using React, JavaScript, CSS and TypeScript.', 'Shortlisted'),
         ('Kabir_Shah.txt', 'Web developer building React interfaces with JavaScript and CSS.', 'Review'),
         ('Priya_Nair.txt', 'Designer with CSS and HTML experience.', 'Rejected'),
     ]),
    ('Data Analyst', 'Analyze recruitment metrics and communicate findings to the team.',
     ['python', 'sql', 'excel', 'power bi'], [
         ('Ishaan_Verma.txt', 'Data analyst using Python, SQL, Excel and Power BI for reporting.', 'Shortlisted'),
         ('Sara_Khan.txt', 'Reporting analyst experienced with SQL and Excel dashboards.', 'New'),
     ]),
]


def seed_demo():
    with SessionLocal() as db:
        # Never reset an existing account or re-add data the user changed/deleted.
        if db.scalar(select(User).where(User.email == DEMO_EMAIL)):
            return False
        user = User(email=DEMO_EMAIL, password_hash=pwd.hash(DEMO_PASSWORD))
        db.add(user)
        db.flush()
        for title, description, skills, resumes in ROLES:
            skills = normalize_skills(skills)
            job = Job(owner_id=user.id, title=title, description=description,
                      skills='|'.join(skills))
            db.add(job)
            db.flush()
            for filename, text, status in resumes:
                text = 'Synthetic demo resume. All candidate details are fictional.\n' + text
                score, matched, missing = match(text, skills)
                db.add(Candidate(owner_id=user.id, job_id=job.id, filename=filename,
                                 extracted_text=text, score=score,
                                 matched_skills='|'.join(matched),
                                 missing_skills='|'.join(missing), status=status))
        db.commit()
        return True


if __name__ == '__main__':
    created = seed_demo()
    print('Demo workspace created (3 jobs, 8 candidates).' if created
          else 'Demo account already exists; existing data was preserved.')
    if created:
        print(f'Email: {DEMO_EMAIL}\nPassword: {DEMO_PASSWORD}')
