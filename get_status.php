<?php
/**
 * Verdant Status API
 * Serves the latest biodome status from the private verdant directory
 */

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

