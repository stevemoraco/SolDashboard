<?php
/**
 * Verdant Webcam Image API
 * Serves the latest webcam image from the private verdant directory
 */

$image_file = '/home/smjinhg78fg0/verdant/latest_webcam.jpg';

if (file_exists($image_file)) {
    header('Content-Type: image/jpeg');
    header('Cache-Control: no-cache, must-revalidate');
    header('Content-Length: ' . filesize($image_file));
    readfile($image_file);
} else {
    // Return a placeholder or 404
    http_response_code(404);
    header('Content-Type: application/json');
    echo json_encode(['error' => 'Webcam image not found']);
}
?>

