# Sol The Trophy Tomato - Live Dashboard

## Overview
A live monitoring dashboard for "Sol The Trophy Tomato" - an AI-powered plant growing project by AutonCorp. The dashboard displays real-time sensor data, webcam feed, device status, and Claude's AI outputs.

## Project Structure
- `index.html` - Main dashboard frontend (static HTML/CSS/JS)
- `server.py` - Simple Python HTTP server to serve the static files
- `ftp_uploader.py` - Python utility for uploading data to external server (used on biodome machine)
- `get_*.php` - PHP API endpoints (meant for deployment on autoncorp.com server)
- `SETUP_INSTRUCTIONS.md` - Original setup documentation

## How It Works
The dashboard is a static frontend that fetches data from an external API at `https://autoncorp.com/biodome/`:
- `get_status.php` - Returns sensor data, device states, and AI output
- `get_webcam.php` - Returns live webcam image
- `get_pumpfun.php` - Returns $SOL token metrics from pump.fun API

## Running Locally
The workflow `Web Dashboard` runs `python server.py` which serves the static files on port 5000.

## Deployment
This is a static site that can be deployed using Replit's static deployment. The frontend communicates with external APIs at autoncorp.com.

## Recent Changes
- 2026-01-06: Imported to Replit, added Python static file server
