# Verdant Web Dashboard Setup

## What You Have

The Biodome machine side is ready! The UI will now:
- Upload `verdant_status.json` every 2 minutes
- Upload `latest_webcam.jpg` every 2 minutes (when Verdant is sleeping)

## What You Need To Do (cPanel)

### Step 1: Create the `/biodome/` folder

1. Open cPanel File Manager
2. Navigate to `public_html/`
3. Create new folder: `biodome`

### Step 2: Create the PHP files

In `public_html/biodome/`, create these two files:

---

**File 1: `get_status.php`**
```php
<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache, must-revalidate');

$status_file = '/home/smjinhg78fg0/verdant/verdant_status.json';

if (file_exists($status_file)) {
    echo file_get_contents($status_file);
} else {
    http_response_code(404);
    echo json_encode(['error' => 'Status file not found', 'message' => 'Waiting for first upload...']);
}
?>
```

---

**File 2: `get_webcam.php`**
```php
<?php
$image_file = '/home/smjinhg78fg0/verdant/latest_webcam.jpg';

if (file_exists($image_file)) {
    header('Content-Type: image/jpeg');
    header('Cache-Control: no-cache, must-revalidate');
    header('Content-Length: ' . filesize($image_file));
    readfile($image_file);
} else {
    http_response_code(404);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Webcam image not found']);
}
?>
```

---

### Step 3: Upload the HTML dashboard

Upload the `index.html` from this folder to `public_html/biodome/index.html`

Or create it in cPanel and paste the contents.

---

### Step 4: Test!

1. Make sure the Verdant UI is running on the biodome machine
2. Wait 2 minutes for the first upload
3. Visit: `https://autoncorp.com/biodome/`

---

## File Locations Summary

| What | Where |
|------|-------|
| **FTP uploads** | `/home/smjinhg78fg0/verdant/` (private) |
| **verdant_status.json** | `/verdant/verdant_status.json` |
| **latest_webcam.jpg** | `/verdant/latest_webcam.jpg` |
| **Dashboard page** | `/public_html/biodome/index.html` |
| **Status API** | `/public_html/biodome/get_status.php` |
| **Webcam API** | `/public_html/biodome/get_webcam.php` |

---

## Troubleshooting

### "Status file not found"
- Wait for the first upload (2 minutes after UI starts)
- Check FTP credentials in `ftp_uploader.py`

### Webcam image not showing
- Webcam only uploads when Verdant is sleeping
- Check if Verdant is in active mode

### PHP errors
- Make sure the path `/home/smjinhg78fg0/verdant/` is correct
- Check file permissions

---

*Files in this folder are also ready to copy/paste into cPanel!*

