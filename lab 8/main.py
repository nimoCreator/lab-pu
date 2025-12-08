from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Patient
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/patients", response_model=list[schemas.PatientRead])
def get_patients(db: Session = Depends(get_db)):
    return db.query(Patient).all()

@app.get("/patients/{patient_id}", response_model=schemas.PatientRead)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    return db.query(Patient).filter(Patient.id == patient_id).first()

@app.post("/patients", response_model=schemas.PatientRead)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    db_obj = Patient(**patient.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@app.put("/patients/{patient_id}", response_model=schemas.PatientRead)
def update_patient(patient_id: int, patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    db_obj = db.query(Patient).filter(Patient.id == patient_id).first()
    for key, value in patient.dict().items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj

@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    db_obj = db.query(Patient).filter(Patient.id == patient_id).first()
    db.delete(db_obj)
    db.commit()
    return {"status": "deleted"}


def seed_data():
    db = SessionLocal()
    if db.query(Patient).count() == 0:
        db.add(Patient(name="Jan Kowalski", age=34, is_active=True))
        db.add(Patient(name="Anna Nowak", age=28, is_active=False))
        db.commit()

seed_data()
