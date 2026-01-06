#!/usr/bin/env python3
"""
Verdant Web Dashboard FTP Uploader
Uploads status JSON and webcam image to GoDaddy server
"""

import json
import ftplib
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from io import BytesIO

logger = logging.getLogger("FTPUploader")

# FTP Configuration
FTP_CONFIG = {
    "host": "autoncorp.com",
    "port": 21,
    "username": "verdant@autoncorp.com",
    "password": "BioDome420!",
    "remote_path": "/",  # Root of the verdant user's directory
}

# Plant start date for calculating Sol's day
SOL_PLANTED_DATE = datetime(2025, 11, 24)


def calculate_sol_day() -> int:
    """Calculate how many days since Sol was planted."""
    delta = datetime.now() - SOL_PLANTED_DATE
    return delta.days + 1  # Day 1 = planting day


def generate_status_json(
    sensors: Dict[str, Any],
    devices: Dict[str, bool],
    verdant_output: str
) -> str:
    """Generate the status JSON for the web dashboard."""
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "sol_day": calculate_sol_day(),
        "verdant_output": verdant_output,
        "sensors": {
            "air_temp": sensors.get("air_temp"),
            "humidity": sensors.get("humidity"),
            "vpd": sensors.get("vpd"),
            "soil_moisture": sensors.get("soil_moisture"),
            "co2": sensors.get("co2"),
            "leaf_temp_delta": sensors.get("leaf_temp_delta"),
        },
        "devices": {
            "grow_light": devices.get("grow_light", False),
            "heat_mat": devices.get("heating_mat", False),
            "circulation_fan": devices.get("circulation_fan", False),
            "exhaust_fan": devices.get("exhaust_fan", False),
            "water_pump": devices.get("water_pump", False),
            "humidifier": devices.get("humidifier", False),
        }
    }
    
    return json.dumps(status, indent=2)


def upload_to_ftp(
    json_data: str,
    image_data: Optional[bytes] = None
) -> bool:
    """
    Upload status JSON and optionally webcam image to FTP server.
    
    Args:
        json_data: The JSON string to upload as verdant_status.json
        image_data: Optional JPEG bytes to upload as latest_webcam.jpg
        
    Returns:
        True if upload successful, False otherwise
    """
    try:
        # Connect to FTP
        ftp = ftplib.FTP()
        ftp.connect(FTP_CONFIG["host"], FTP_CONFIG["port"], timeout=30)
        ftp.login(FTP_CONFIG["username"], FTP_CONFIG["password"])
        
        # Change to remote directory if specified
        if FTP_CONFIG["remote_path"] and FTP_CONFIG["remote_path"] != "/":
            ftp.cwd(FTP_CONFIG["remote_path"])
        
        # Upload JSON status
        json_bytes = BytesIO(json_data.encode('utf-8'))
        ftp.storbinary('STOR verdant_status.json', json_bytes)
        logger.info("✅ Uploaded verdant_status.json")
        
        # Upload webcam image if provided
        if image_data:
            image_bytes = BytesIO(image_data)
            ftp.storbinary('STOR latest_webcam.jpg', image_bytes)
            logger.info("✅ Uploaded latest_webcam.jpg")
        
        ftp.quit()
        logger.info("📡 FTP upload complete")
        return True
        
    except ftplib.all_errors as e:
        logger.error(f"❌ FTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return False


class WebDashboardUploader:
    """
    Manages periodic uploads to the web dashboard.
    Designed to be integrated into the Verdant UI.
    """
    
    def __init__(self):
        self.last_upload = None
        self.upload_count = 0
        self.last_verdant_output = ""
        
    def update_verdant_output(self, output: str):
        """Update the cached Verdant output for next upload."""
        self.last_verdant_output = output
        
    def upload(
        self,
        sensors: Dict[str, Any],
        devices: Dict[str, bool],
        webcam_image: Optional[bytes] = None
    ) -> bool:
        """
        Perform an upload to the web dashboard.
        
        Args:
            sensors: Current sensor readings dict
            devices: Current device states dict
            webcam_image: Optional JPEG bytes from camera
            
        Returns:
            True if successful
        """
        # Generate JSON
        json_data = generate_status_json(
            sensors=sensors,
            devices=devices,
            verdant_output=self.last_verdant_output
        )
        
        # Upload
        success = upload_to_ftp(json_data, webcam_image)
        
        if success:
            self.last_upload = datetime.now()
            self.upload_count += 1
            
        return success


# Singleton instance for UI integration
_uploader_instance = None

def get_uploader() -> WebDashboardUploader:
    """Get the singleton uploader instance."""
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = WebDashboardUploader()
    return _uploader_instance


# Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test data
    test_sensors = {
        "air_temp": 29.5,
        "humidity": 44.2,
        "vpd": 2.31,
        "soil_moisture": 42,
        "co2": 520,
        "leaf_temp_delta": -3.2
    }
    
    test_devices = {
        "grow_light": True,
        "heating_mat": True,
        "circulation_fan": False,
        "exhaust_fan": False,
        "water_pump": False,
        "humidifier": False
    }
    
    test_output = """Hey Sol! Checking in on you.

Conditions look good:
- Temp: 29.5°C ✓
- VPD: 2.31 kPa - perfect range!
- Soil at 42% - no watering needed

You're looking healthy today. Keep growing strong! 🌱
"""
    
    # Generate and print JSON
    json_str = generate_status_json(test_sensors, test_devices, test_output)
    print("Generated JSON:")
    print(json_str)
    
    # Uncomment to test actual upload:
    # success = upload_to_ftp(json_str, None)
    # print(f"Upload {'succeeded' if success else 'failed'}")

