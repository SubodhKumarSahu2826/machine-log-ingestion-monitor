import datetime
from sqlalchemy.orm import Session
from .database import engine, SessionLocal, Base
from . import models

def seed_data():
    # Make sure tables exist (usually alembic does this, but just in case)
    # Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    # Check if we already have data
    if db.query(models.Site).first():
        print("Data already seeded.")
        db.close()
        return

    print("Seeding initial data...")
    
    # Create Site
    site = models.Site(name="Hauptfabrik", location="Berlin")
    db.add(site)
    db.commit()
    db.refresh(site)
    
    # Create Line
    line = models.Line(name="Line 1", site_id=site.id)
    db.add(line)
    db.commit()
    db.refresh(line)
    
    # Create Station
    station = models.Station(name="Station A", line_id=line.id)
    db.add(station)
    db.commit()
    db.refresh(station)
    
    # Create Machine
    machine = models.Machine(name="Robot Arm 1", station_id=station.id)
    db.add(machine)
    db.commit()
    db.refresh(machine)
    
    # Create Integrations
    integration1 = models.Integration(
        name="MQTT_Connector_1",
        type="MQTT",
        machine_id=machine.id,
        expected_interval_seconds=30,
        warning_threshold_seconds=60,
        stale_threshold_seconds=120,
        health_state=models.IntegrationHealthState.HEALTHY,
        last_heartbeat_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(integration1)

    integration2 = models.Integration(
        name="API_Connector_2",
        type="API",
        machine_id=machine.id,
        expected_interval_seconds=60,
        warning_threshold_seconds=120,
        stale_threshold_seconds=240,
        health_state=models.IntegrationHealthState.HEALTHY,
        last_heartbeat_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db.add(integration2)
    
    db.commit()
    print("Seeding complete.")
    db.close()

if __name__ == "__main__":
    seed_data()
