# Sol The Trophy Tomato - Live Dashboard

## Overview
A live monitoring dashboard for "Sol The Trophy Tomato" - an AI-powered plant growing project by AutonCorp. The dashboard displays real-time sensor data, webcam feed, device status, Claude's AI outputs, with persistent data storage for trends, analytics, and predictions.

## Project Structure
- `index.html` - Main dashboard frontend with charts and analytics
- `server.py` - FastAPI server entry point
- `api.py` - FastAPI backend with data collection and API endpoints
- `database.py` - Database connection and session management
- `models.py` - SQLAlchemy ORM models for PostgreSQL
- `ftp_uploader.py` - Python utility for uploading data to external server (used on biodome machine)
- `get_*.php` - PHP API endpoints (for deployment on autoncorp.com server)

## Database Schema
The PostgreSQL database stores:
- **sensor_readings**: Temperature, humidity, VPD, soil moisture, CO2, leaf delta
- **device_states**: Grow light, heat mat, fans, pump, humidifier status
- **ai_outputs**: Claude's plant care outputs
- **coin_metrics**: $SOL token data from pump.fun
- **hourly_aggregates**: Pre-computed hourly averages

## API Endpoints
- `/api/sensors/latest` - Current sensor readings
- `/api/sensors/history?hours=24` - Historical sensor data
- `/api/devices/latest` - Current device states
- `/api/coin/latest` - Latest coin metrics
- `/api/coin/history?hours=24` - Coin price history
- `/api/analytics/trends?hours=24` - Trend analysis with direction
- `/api/analytics/predictions?hours_ahead=6` - Simple linear predictions
- `/api/aggregates/hourly` - Hourly aggregated data
- `/api/stats` - Database statistics

## Background Jobs
Data is automatically collected and stored:
- Plant data: Every 2 minutes (from autoncorp.com API)
- Coin data: Every 5 minutes (from pump.fun API)
- Hourly aggregates: Every 10 minutes

## Running Locally
The workflow `Web Dashboard` runs `python server.py` which starts FastAPI on port 5000.

## Deployment
Uses autoscale deployment with FastAPI + Uvicorn.

## Recent Changes
- 2026-01-06: Added PostgreSQL database for persistent storage
- 2026-01-06: Built FastAPI backend with analytics and predictions
- 2026-01-06: Added Chart.js trends visualization
- 2026-01-06: Added 6-hour prediction display
