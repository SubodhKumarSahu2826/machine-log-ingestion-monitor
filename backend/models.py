from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Enum, UniqueConstraint, Text
from sqlalchemy.orm import relationship
import enum
import datetime
from .database import Base

class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    location = Column(String, nullable=True)

    lines = relationship("Line", back_populates="site")

class Line(Base):
    __tablename__ = "lines"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    
    __table_args__ = (UniqueConstraint('site_id', 'name', name='_site_line_uc'),)

    site = relationship("Site", back_populates="lines")
    stations = relationship("Station", back_populates="line")

class Station(Base):
    __tablename__ = "stations"
    id = Column(Integer, primary_key=True, index=True)
    line_id = Column(Integer, ForeignKey("lines.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    
    __table_args__ = (UniqueConstraint('line_id', 'name', name='_line_station_uc'),)

    line = relationship("Line", back_populates="stations")
    machines = relationship("Machine", back_populates="station")

class Machine(Base):
    __tablename__ = "machines"
    id = Column(Integer, primary_key=True, index=True)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    
    __table_args__ = (UniqueConstraint('station_id', 'name', name='_station_machine_uc'),)

    station = relationship("Station", back_populates="machines")
    integrations = relationship("Integration", back_populates="machine")
    events = relationship("MachineEvent", back_populates="machine")

class IntegrationHealthState(str, enum.Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    STALE = "STALE"
    RECOVERING = "RECOVERING"
    FAILED = "FAILED"

class Integration(Base):
    __tablename__ = "integrations"
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False) # e.g. "API", "MQTT"
    
    expected_interval_seconds = Column(Integer, default=30)
    warning_threshold_seconds = Column(Integer, default=60)
    stale_threshold_seconds = Column(Integer, default=120)
    
    health_state = Column(Enum(IntegrationHealthState), default=IntegrationHealthState.HEALTHY, nullable=False)
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    
    machine = relationship("Machine", back_populates="integrations")
    events = relationship("MachineEvent", back_populates="integration")
    heartbeats = relationship("Heartbeat", back_populates="integration")
    incidents = relationship("Incident", back_populates="integration")

class MachineEvent(Base):
    __tablename__ = "machine_events"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False) # Client provided unique ID
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    payload = Column(JSON, nullable=False)

    machine = relationship("Machine", back_populates="events")
    integration = relationship("Integration", back_populates="events")

class Heartbeat(Base):
    __tablename__ = "heartbeats"
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    status = Column(String, nullable=False)

    integration = relationship("Integration", back_populates="heartbeats")

class IncidentState(str, enum.Enum):
    DETECTED = "DETECTED"
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RECOVERING = "RECOVERING"
    VERIFIED = "VERIFIED"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False)
    state = Column(Enum(IncidentState), default=IncidentState.DETECTED, nullable=False)
    probable_cause = Column(String, nullable=True)
    diagnostic_details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    integration = relationship("Integration", back_populates="incidents")
    recovery_attempts = relationship("RecoveryAttempt", back_populates="incident")

class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    action = Column(String, nullable=False) # e.g. "RETRY_CONNECTION"
    status = Column(String, nullable=False) # e.g. "STARTED", "SUCCESS", "FAILURE"
    attempted_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    result_message = Column(Text, nullable=True)

    incident = relationship("Incident", back_populates="recovery_attempts")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False) # e.g. "Incident"
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), nullable=False)
