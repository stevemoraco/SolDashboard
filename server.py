#!/usr/bin/env python3
"""
Local development server with pump.fun API proxy
Serves static files and proxies API requests to avoid CORS
"""

import http.server
import json
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs
import os

PORT = 8080
PUMPFUN_TOKEN = 'jk1T35eWK41MBMM8AWoYVaNbjHEEQzMDetTsfnqpump'

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        # Proxy pump.fun API requests
        if parsed.path == '/get_pumpfun.php':
            self.proxy_pumpfun()
            return

        # Serve demo data for status (no real backend locally)
        if parsed.path == '/get_status.php':
            self.serve_demo_status()
            return

        # Serve demo webcam
        if parsed.path == '/get_webcam.php':
            self.serve_demo_webcam()
            return

        # Serve static files normally
        super().do_GET()

    def proxy_pumpfun(self):
        """Fetch pump.fun data and return it"""
        api_url = f'https://frontend-api-v3.pump.fun/coins/{PUMPFUN_TOKEN}'

        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'SolDashboard/1.0'
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = response.read()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def serve_demo_status(self):
        """Serve demo plant status data"""
        demo_data = {
            "verdant_output": "## Daily Check-in - Sol's Growth Report\n\nGood morning! **Sol is thriving** today. The new compound leaves are developing beautifully.\n\n### Current Observations:\n- Leaf color: *Vibrant green*\n- New growth: `3 new leaves emerging`\n- Overall health: **Excellent**\n\n> \"A tomato plant's happiness is measured in the unfurling of its leaves.\" - Verdant AI\n\n### Recommendations:\n1. Maintain current watering schedule\n2. VPD is optimal for transpiration\n3. Consider slight nutrient boost next week",
            "sensors": {
                "air_temp": 24.5,
                "humidity": 65,
                "vpd": 0.85,
                "soil_moisture": 72,
                "co2": 850,
                "leaf_temp_delta": -1.2
            },
            "devices": {
                "grow_light": True,
                "heat_mat": False,
                "circulation_fan": True,
                "exhaust_fan": False,
                "water_pump": False,
                "humidifier": True
            },
            "sol_day": 42,
            "timestamp": "2025-01-05T12:00:00Z"
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(demo_data).encode())

    def serve_demo_webcam(self):
        """Redirect to pump.fun thumbnail for demo"""
        self.send_response(302)
        self.send_header('Location', 'https://thumbnails.pump.fun/1904377/1767658059127.jpeg')
        self.end_headers()

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    with http.server.HTTPServer(('', PORT), ProxyHandler) as httpd:
        print(f'🌱 Sol Dashboard Server running at http://localhost:{PORT}')
        print(f'📊 Pump.fun proxy enabled at /get_pumpfun.php')
        print(f'🧪 Demo mode for plant data')
        print(f'Press Ctrl+C to stop\n')
        httpd.serve_forever()
