from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, Text, Index
from database import Base

class SensorReading(Base):
    __tablename__ = "sensor_readings"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    air_temp = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    vpd = Column(Float, nullable=True)
    soil_moisture = Column(Float, nullable=True)
    co2 = Column(Float, nullable=True)
    leaf_temp_delta = Column(Float, nullable=True)
    
    __table_args__ = (
        Index('idx_sensor_timestamp', 'timestamp'),
    )

class DeviceState(Base):
    __tablename__ = "device_states"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    grow_light = Column(Boolean, default=False)
    heat_mat = Column(Boolean, default=False)
    circulation_fan = Column(Boolean, default=False)
    exhaust_fan = Column(Boolean, default=False)
    water_pump = Column(Boolean, default=False)
    humidifier = Column(Boolean, default=False)

class AIOutput(Base):
    __tablename__ = "ai_outputs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    output_text = Column(Text)
    sol_day = Column(Integer, nullable=True)

class CoinMetric(Base):
    __tablename__ = "coin_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    market_cap = Column(Float, nullable=True)
    usd_market_cap = Column(Float, nullable=True)
    holders = Column(Integer, nullable=True)
    replies = Column(Integer, nullable=True)
    ath_market_cap = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    
    __table_args__ = (
        Index('idx_coin_timestamp', 'timestamp'),
    )

class HourlyAggregate(Base):
    __tablename__ = "hourly_aggregates"
    
    id = Column(Integer, primary_key=True, index=True)
    hour_start = Column(DateTime, unique=True, index=True)
    avg_temp = Column(Float, nullable=True)
    avg_humidity = Column(Float, nullable=True)
    avg_vpd = Column(Float, nullable=True)
    avg_soil_moisture = Column(Float, nullable=True)
    avg_co2 = Column(Float, nullable=True)
    min_temp = Column(Float, nullable=True)
    max_temp = Column(Float, nullable=True)
    light_uptime_pct = Column(Float, nullable=True)
    heat_uptime_pct = Column(Float, nullable=True)

class LikeEvent(Base):
    __tablename__ = "like_events"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    source = Column(String(100), nullable=True)
    message = Column(Text, nullable=True)
