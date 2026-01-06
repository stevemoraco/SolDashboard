import os
import httpx
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager
import numpy as np

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from fastapi.responses import JSONResponse

from database import engine, Base, get_db, SessionLocal
from models import SensorReading, DeviceState, AIOutput, CoinMetric, HourlyAggregate, LikeEvent

import object_storage

EXTERNAL_API_BASE = "https://autoncorp.com/biodome/"
WEBCAM_URL = f"{EXTERNAL_API_BASE}get_webcam.php"
PUMPFUN_API = "https://frontend-api-v3.pump.fun/coins/jk1T35eWK41MBMM8AWoYVaNbjHEEQzMDetTsfnqpump"

latest_webcam_frame_path: Optional[str] = None

scheduler = BackgroundScheduler()

def fetch_and_store_plant_data():
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(f"{EXTERNAL_API_BASE}get_status.php")
            if response.status_code == 200:
                data = response.json()
                db = SessionLocal()
                try:
                    sensors = data.get("sensors", {})
                    devices = data.get("devices", {})
                    
                    sensor_reading = SensorReading(
                        timestamp=datetime.utcnow(),
                        air_temp=sensors.get("air_temp"),
                        humidity=sensors.get("humidity"),
                        vpd=sensors.get("vpd"),
                        soil_moisture=sensors.get("soil_moisture"),
                        co2=sensors.get("co2"),
                        leaf_temp_delta=sensors.get("leaf_temp_delta")
                    )
                    db.add(sensor_reading)
                    
                    device_state = DeviceState(
                        timestamp=datetime.utcnow(),
                        grow_light=devices.get("grow_light", False),
                        heat_mat=devices.get("heat_mat", False),
                        circulation_fan=devices.get("circulation_fan", False),
                        exhaust_fan=devices.get("exhaust_fan", False),
                        water_pump=devices.get("water_pump", False),
                        humidifier=devices.get("humidifier", False)
                    )
                    db.add(device_state)
                    
                    verdant_output = data.get("verdant_output", "")
                    if verdant_output:
                        ai_output = AIOutput(
                            timestamp=datetime.utcnow(),
                            output_text=verdant_output,
                            sol_day=data.get("sol_day")
                        )
                        db.add(ai_output)
                    
                    db.commit()
                    print(f"[{datetime.now()}] Stored plant data")
                finally:
                    db.close()
    except Exception as e:
        print(f"Error fetching plant data: {e}")

def fetch_and_store_coin_data():
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(PUMPFUN_API, headers={
                "Accept": "application/json",
                "User-Agent": "SolDashboard/1.0"
            })
            if response.status_code == 200:
                data = response.json()
                db = SessionLocal()
                try:
                    coin_metric = CoinMetric(
                        timestamp=datetime.utcnow(),
                        market_cap=data.get("market_cap"),
                        usd_market_cap=data.get("usd_market_cap"),
                        holders=data.get("holder_count"),
                        replies=data.get("reply_count"),
                        ath_market_cap=data.get("ath_market_cap"),
                        price=data.get("price"),
                        volume_24h=data.get("volume_24h")
                    )
                    db.add(coin_metric)
                    db.commit()
                    print(f"[{datetime.now()}] Stored coin data")
                finally:
                    db.close()
    except Exception as e:
        print(f"Error fetching coin data: {e}")

def compute_hourly_aggregates():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        hour_end = hour_start + timedelta(hours=1)
        
        existing = db.query(HourlyAggregate).filter(HourlyAggregate.hour_start == hour_start).first()
        if existing:
            return
        
        sensors = db.query(SensorReading).filter(
            SensorReading.timestamp >= hour_start,
            SensorReading.timestamp < hour_end
        ).all()
        
        if not sensors:
            return
        
        devices = db.query(DeviceState).filter(
            DeviceState.timestamp >= hour_start,
            DeviceState.timestamp < hour_end
        ).all()
        
        temps = [s.air_temp for s in sensors if s.air_temp is not None]
        humidities = [s.humidity for s in sensors if s.humidity is not None]
        vpds = [s.vpd for s in sensors if s.vpd is not None]
        soils = [s.soil_moisture for s in sensors if s.soil_moisture is not None]
        co2s = [s.co2 for s in sensors if s.co2 is not None]
        
        light_on = sum(1 for d in devices if d.grow_light) / max(len(devices), 1) * 100
        heat_on = sum(1 for d in devices if d.heat_mat) / max(len(devices), 1) * 100
        
        aggregate = HourlyAggregate(
            hour_start=hour_start,
            avg_temp=np.mean(temps) if temps else None,
            avg_humidity=np.mean(humidities) if humidities else None,
            avg_vpd=np.mean(vpds) if vpds else None,
            avg_soil_moisture=np.mean(soils) if soils else None,
            avg_co2=np.mean(co2s) if co2s else None,
            min_temp=min(temps) if temps else None,
            max_temp=max(temps) if temps else None,
            light_uptime_pct=light_on,
            heat_uptime_pct=heat_on
        )
        db.add(aggregate)
        db.commit()
        print(f"[{datetime.now()}] Computed hourly aggregate for {hour_start}")
    except Exception as e:
        print(f"Error computing aggregates: {e}")
    finally:
        db.close()

def fetch_and_store_webcam_frame():
    global latest_webcam_frame_path
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(WEBCAM_URL)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "image/jpeg")
                if "image" in content_type:
                    now = datetime.utcnow()
                    filename = f"webcam/frame_{now.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
                    
                    try:
                        path = object_storage.save_file(
                            content=response.content,
                            object_path=filename,
                            content_type="image/jpeg"
                        )
                        latest_webcam_frame_path = path
                        print(f"[{datetime.now()}] Stored webcam frame: {filename}")
                    except Exception as storage_error:
                        print(f"Error saving webcam frame to storage: {storage_error}")
                else:
                    print(f"Webcam response is not an image: {content_type}")
            else:
                print(f"Webcam fetch failed with status: {response.status_code}")
    except Exception as e:
        print(f"Error fetching webcam frame: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    scheduler.add_job(fetch_and_store_plant_data, 'interval', minutes=2, id='plant_data')
    scheduler.add_job(fetch_and_store_coin_data, 'interval', minutes=5, id='coin_data')
    scheduler.add_job(compute_hourly_aggregates, 'interval', minutes=10, id='aggregates')
    scheduler.add_job(fetch_and_store_webcam_frame, 'interval', minutes=2, id='webcam_frame')
    scheduler.start()
    
    fetch_and_store_plant_data()
    fetch_and_store_coin_data()
    fetch_and_store_webcam_frame()
    
    yield
    
    scheduler.shutdown()

app = FastAPI(title="Sol Dashboard API", lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/sensors/latest")
def get_latest_sensors(db: Session = Depends(get_db)):
    reading = db.query(SensorReading).order_by(desc(SensorReading.timestamp)).first()
    if not reading:
        return {"error": "No data"}
    return {
        "timestamp": reading.timestamp.isoformat(),
        "air_temp": reading.air_temp,
        "humidity": reading.humidity,
        "vpd": reading.vpd,
        "soil_moisture": reading.soil_moisture,
        "co2": reading.co2,
        "leaf_temp_delta": reading.leaf_temp_delta
    }

@app.get("/api/sensors/history")
def get_sensor_history(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(hours=hours)
    readings = db.query(SensorReading).filter(
        SensorReading.timestamp >= since
    ).order_by(SensorReading.timestamp).all()
    
    return [{
        "timestamp": r.timestamp.isoformat(),
        "air_temp": r.air_temp,
        "humidity": r.humidity,
        "vpd": r.vpd,
        "soil_moisture": r.soil_moisture,
        "co2": r.co2,
        "leaf_temp_delta": r.leaf_temp_delta
    } for r in readings]

@app.get("/api/devices/latest")
def get_latest_devices(db: Session = Depends(get_db)):
    state = db.query(DeviceState).order_by(desc(DeviceState.timestamp)).first()
    if not state:
        return {"error": "No data"}
    return {
        "timestamp": state.timestamp.isoformat(),
        "grow_light": state.grow_light,
        "heat_mat": state.heat_mat,
        "circulation_fan": state.circulation_fan,
        "exhaust_fan": state.exhaust_fan,
        "water_pump": state.water_pump,
        "humidifier": state.humidifier
    }

@app.get("/api/devices/history")
def get_device_history(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(hours=hours)
    states = db.query(DeviceState).filter(
        DeviceState.timestamp >= since
    ).order_by(DeviceState.timestamp).all()
    
    return [{
        "timestamp": s.timestamp.isoformat(),
        "grow_light": s.grow_light,
        "heat_mat": s.heat_mat,
        "circulation_fan": s.circulation_fan,
        "exhaust_fan": s.exhaust_fan,
        "water_pump": s.water_pump,
        "humidifier": s.humidifier
    } for s in states]

@app.get("/api/coin/latest")
def get_latest_coin(db: Session = Depends(get_db)):
    metric = db.query(CoinMetric).order_by(desc(CoinMetric.timestamp)).first()
    if not metric:
        return {"error": "No data"}
    return {
        "timestamp": metric.timestamp.isoformat(),
        "market_cap": metric.market_cap,
        "usd_market_cap": metric.usd_market_cap,
        "holders": metric.holders,
        "replies": metric.replies,
        "ath_market_cap": metric.ath_market_cap,
        "price": metric.price,
        "volume_24h": metric.volume_24h
    }

@app.get("/api/coin/history")
def get_coin_history(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(hours=hours)
    metrics = db.query(CoinMetric).filter(
        CoinMetric.timestamp >= since
    ).order_by(CoinMetric.timestamp).all()
    
    return [{
        "timestamp": m.timestamp.isoformat(),
        "market_cap": m.market_cap,
        "usd_market_cap": m.usd_market_cap,
        "holders": m.holders,
        "replies": m.replies,
        "price": m.price
    } for m in metrics]

@app.get("/api/ai/latest")
def get_latest_ai_output(db: Session = Depends(get_db)):
    output = db.query(AIOutput).order_by(desc(AIOutput.timestamp)).first()
    if not output:
        return {"error": "No data"}
    return {
        "timestamp": output.timestamp.isoformat(),
        "output_text": output.output_text,
        "sol_day": output.sol_day
    }

@app.get("/api/aggregates/hourly")
def get_hourly_aggregates(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(hours=hours)
    aggregates = db.query(HourlyAggregate).filter(
        HourlyAggregate.hour_start >= since
    ).order_by(HourlyAggregate.hour_start).all()
    
    return [{
        "hour_start": a.hour_start.isoformat(),
        "avg_temp": a.avg_temp,
        "avg_humidity": a.avg_humidity,
        "avg_vpd": a.avg_vpd,
        "avg_soil_moisture": a.avg_soil_moisture,
        "avg_co2": a.avg_co2,
        "min_temp": a.min_temp,
        "max_temp": a.max_temp,
        "light_uptime_pct": a.light_uptime_pct,
        "heat_uptime_pct": a.heat_uptime_pct
    } for a in aggregates]

@app.get("/api/analytics/trends")
def get_trends(
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(hours=hours)
    readings = db.query(SensorReading).filter(
        SensorReading.timestamp >= since
    ).order_by(SensorReading.timestamp).all()
    
    if len(readings) < 2:
        return {"error": "Not enough data for trends"}
    
    temps = [r.air_temp for r in readings if r.air_temp is not None]
    humidities = [r.humidity for r in readings if r.humidity is not None]
    vpds = [r.vpd for r in readings if r.vpd is not None]
    soils = [r.soil_moisture for r in readings if r.soil_moisture is not None]
    
    def calc_trend(values):
        if len(values) < 2:
            return {"direction": "stable", "change": 0}
        x = np.arange(len(values))
        if len(values) > 1:
            slope = np.polyfit(x, values, 1)[0]
            pct_change = (slope * len(values)) / max(np.mean(values), 1) * 100
            if abs(pct_change) < 2:
                direction = "stable"
            elif pct_change > 0:
                direction = "rising"
            else:
                direction = "falling"
            return {"direction": direction, "change_pct": round(pct_change, 2)}
        return {"direction": "stable", "change_pct": 0}
    
    return {
        "period_hours": hours,
        "data_points": len(readings),
        "temperature": {
            "current": temps[-1] if temps else None,
            "avg": round(np.mean(temps), 2) if temps else None,
            "min": min(temps) if temps else None,
            "max": max(temps) if temps else None,
            "trend": calc_trend(temps)
        },
        "humidity": {
            "current": humidities[-1] if humidities else None,
            "avg": round(np.mean(humidities), 2) if humidities else None,
            "trend": calc_trend(humidities)
        },
        "vpd": {
            "current": vpds[-1] if vpds else None,
            "avg": round(np.mean(vpds), 2) if vpds else None,
            "trend": calc_trend(vpds)
        },
        "soil_moisture": {
            "current": soils[-1] if soils else None,
            "avg": round(np.mean(soils), 2) if soils else None,
            "trend": calc_trend(soils)
        }
    }

@app.get("/api/analytics/predictions")
def get_predictions(
    hours_ahead: int = Query(6, ge=1, le=24),
    db: Session = Depends(get_db)
):
    readings = db.query(SensorReading).order_by(
        desc(SensorReading.timestamp)
    ).limit(100).all()
    
    readings = list(reversed(readings))
    
    if len(readings) < 10:
        return {"error": "Not enough historical data for predictions"}
    
    def predict_value(values, steps):
        if len(values) < 2:
            return None
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        future_x = len(values) + steps
        predicted = coeffs[0] * future_x + coeffs[1]
        return round(predicted, 2)
    
    temps = [r.air_temp for r in readings if r.air_temp is not None]
    humidities = [r.humidity for r in readings if r.humidity is not None]
    vpds = [r.vpd for r in readings if r.vpd is not None]
    soils = [r.soil_moisture for r in readings if r.soil_moisture is not None]
    
    steps = hours_ahead * 30
    
    return {
        "prediction_horizon_hours": hours_ahead,
        "based_on_readings": len(readings),
        "predictions": {
            "air_temp": predict_value(temps, steps),
            "humidity": predict_value(humidities, steps),
            "vpd": predict_value(vpds, steps),
            "soil_moisture": predict_value(soils, steps)
        },
        "current": {
            "air_temp": temps[-1] if temps else None,
            "humidity": humidities[-1] if humidities else None,
            "vpd": vpds[-1] if vpds else None,
            "soil_moisture": soils[-1] if soils else None
        },
        "confidence": "low" if len(readings) < 50 else "medium"
    }

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    sensor_count = db.query(func.count(SensorReading.id)).scalar()
    device_count = db.query(func.count(DeviceState.id)).scalar()
    coin_count = db.query(func.count(CoinMetric.id)).scalar()
    ai_count = db.query(func.count(AIOutput.id)).scalar()
    
    oldest_sensor = db.query(func.min(SensorReading.timestamp)).scalar()
    newest_sensor = db.query(func.max(SensorReading.timestamp)).scalar()
    
    return {
        "total_records": {
            "sensor_readings": sensor_count,
            "device_states": device_count,
            "coin_metrics": coin_count,
            "ai_outputs": ai_count
        },
        "data_range": {
            "oldest": oldest_sensor.isoformat() if oldest_sensor else None,
            "newest": newest_sensor.isoformat() if newest_sensor else None
        }
    }

@app.post("/api/engagement/like")
def add_like(message: str = "", db: Session = Depends(get_db)):
    like = LikeEvent(
        timestamp=datetime.utcnow(),
        source="web",
        message=message if message else None
    )
    db.add(like)
    db.commit()
    
    total = db.query(func.count(LikeEvent.id)).scalar()
    return {"success": True, "total_likes": total}

@app.get("/api/engagement/count")
def get_like_count(db: Session = Depends(get_db)):
    total = db.query(func.count(LikeEvent.id)).scalar()
    return {"total_likes": total}

@app.get("/api/engagement/export")
def export_likes(db: Session = Depends(get_db)):
    likes = db.query(LikeEvent).order_by(LikeEvent.timestamp).all()
    data = [{
        "id": l.id,
        "timestamp": l.timestamp.isoformat(),
        "source": l.source,
        "message": l.message
    } for l in likes]
    
    return JSONResponse(
        content={"likes": data, "total": len(data), "exported_at": datetime.utcnow().isoformat()},
        headers={"Content-Disposition": "attachment; filename=sol_likes.json"}
    )

@app.get("/api/webcam/latest")
def get_latest_webcam():
    global latest_webcam_frame_path
    if not latest_webcam_frame_path:
        try:
            frames = object_storage.list_files("webcam/")
            if frames:
                latest_webcam_frame_path = frames[0]["path"]
        except Exception as e:
            return {"error": f"No webcam frames available: {e}"}
    
    if not latest_webcam_frame_path:
        return {"error": "No webcam frames available"}
    
    try:
        signed_url = object_storage.get_signed_url(latest_webcam_frame_path, ttl_sec=3600)
        public_url = object_storage.get_public_url(latest_webcam_frame_path)
        return {
            "path": latest_webcam_frame_path,
            "signed_url": signed_url,
            "public_url": public_url,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {"error": f"Failed to get webcam URL: {e}"}

@app.get("/api/webcam/frames")
def list_webcam_frames(limit: int = Query(100, ge=1, le=1000)):
    try:
        frames = object_storage.list_files("webcam/")
        frames = frames[:limit]
        
        result = []
        for frame in frames:
            try:
                signed_url = object_storage.get_signed_url(frame["path"], ttl_sec=3600)
                result.append({
                    "path": frame["path"],
                    "signed_url": signed_url,
                    "size": frame.get("size"),
                    "updated": frame.get("updated")
                })
            except:
                result.append({
                    "path": frame["path"],
                    "size": frame.get("size"),
                    "updated": frame.get("updated")
                })
        
        return {"frames": result, "count": len(result)}
    except Exception as e:
        return {"error": f"Failed to list frames: {e}", "frames": [], "count": 0}

@app.get("/api/webcam/og-image")
def get_og_image():
    global latest_webcam_frame_path
    if not latest_webcam_frame_path:
        try:
            frames = object_storage.list_files("webcam/")
            if frames:
                latest_webcam_frame_path = frames[0]["path"]
        except:
            pass
    
    if latest_webcam_frame_path:
        try:
            signed_url = object_storage.get_signed_url(latest_webcam_frame_path, ttl_sec=86400)
            return RedirectResponse(url=signed_url, status_code=302)
        except:
            pass
    
    return RedirectResponse(url=f"{EXTERNAL_API_BASE}get_webcam.php", status_code=302)

app.mount("/", StaticFiles(directory=".", html=True), name="static")
