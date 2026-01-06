<?php
/**
 * Pump.fun API Proxy
 * Bypasses CORS restrictions by fetching from server-side
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache, must-revalidate');

$token = 'jk1T35eWK41MBMM8AWoYVaNbjHEEQzMDetTsfnqpump';
$api_url = "https://frontend-api-v3.pump.fun/coins/{$token}";

// Initialize cURL
$ch = curl_init();
curl_setopt_array($ch, [
    CURLOPT_URL => $api_url,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 10,
    CURLOPT_HTTPHEADER => [
        'Accept: application/json',
        'User-Agent: SolDashboard/1.0'
    ],
    CURLOPT_SSL_VERIFYPEER => true
]);

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

if ($error) {
    http_response_code(500);
    echo json_encode(['error' => 'Failed to fetch data', 'details' => $error]);
    exit;
}

if ($http_code !== 200) {
    http_response_code($http_code);
    echo json_encode(['error' => 'API returned error', 'http_code' => $http_code]);
    exit;
}

// Return the pump.fun data
echo $response;
?>
