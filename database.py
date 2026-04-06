import logging
from contextlib import contextmanager
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Text, DateTime, ForeignKey, Boolean,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import QueuePool
from sqlalchemy.sql import func

log = logging.getLogger(__name__)

Base = declarative_base()

# ── ORM Models ────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    name          = Column(String(120), nullable=False)
    email         = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(20), nullable=False, default="patient")
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    patient_profile = relationship("Patient", back_populates="user",
                                   uselist=False, foreign_keys="Patient.user_id")
    audit_logs      = relationship("AuditLog", back_populates="user")


class Patient(Base):
    __tablename__ = "patients"
    id                    = Column(Integer, primary_key=True)
    user_id               = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    age                   = Column(Integer)
    gender                = Column(String(30))
    underlying_conditions = Column(Text)
    assigned_doctor_id    = Column(Integer, ForeignKey("users.id"), nullable=True)

    user            = relationship("User", back_populates="patient_profile",
                                   foreign_keys=[user_id])
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_id])
    assessments     = relationship("Assessment", back_populates="patient",
                                   cascade="all, delete-orphan")


class Assessment(Base):
    __tablename__ = "assessments"
    id                = Column(Integer, primary_key=True)
    patient_id        = Column(Integer, ForeignKey("patients.id"), nullable=False)
    respiratory_rate  = Column(Integer, nullable=False)
    oxygen_saturation = Column(Integer, nullable=False)
    o2_scale          = Column(Integer, nullable=False)
    systolic_bp       = Column(Integer, nullable=False)
    heart_rate        = Column(Integer, nullable=False)
    temperature       = Column(Float,   nullable=False)
    consciousness     = Column(String(5), nullable=False)
    on_oxygen         = Column(Integer, nullable=False)
    rule_score        = Column(Integer, nullable=True)   # nullable; legacy only
    ml_prediction     = Column(String(20))
    ml_probability    = Column(Float)
    final_risk        = Column(String(20))
    explanation       = Column(Text)
    recommendation    = Column(Text)
    status            = Column(String(20), default="pending")
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    patient      = relationship("Patient", back_populates="assessments")
    doctor_notes = relationship("DoctorNote", back_populates="assessment",
                                cascade="all, delete-orphan")


class DoctorNote(Base):
    __tablename__ = "doctor_notes"
    id            = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False)
    doctor_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    note          = Column(Text, nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    assessment = relationship("Assessment", back_populates="doctor_notes")
    doctor     = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=True)
    action    = Column(String(200), nullable=False)
    details   = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")


# ── Engine & session factory (module-level singletons) ────────────────────────

_engine         = None
_SessionFactory = None


def init_db(database_url: str) -> None:
    global _engine, _SessionFactory
    _engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # handles Neon/serverless idle-connection drops
        pool_recycle=300,
        echo=False,
    )
    _SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=_engine)
    log.info("Database initialised.")


@contextmanager
def get_db():
    if _SessionFactory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    session = _SessionFactory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
