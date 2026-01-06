/**
 * Sol Biodome Dashboard - Server
 * Express server with API endpoints and background data polling
 */

require('dotenv').config();

const express = require('express');
const cors = require('cors');
const path = require('path');
const fetch = require('node-fetch');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 3000;

// Martin's production API endpoints
const MARTIN_API = {
    status: 'https://autoncorp.com/biodome/get_status.php',
    webcam: 'https://autoncorp.com/biodome/get_webcam.php',
};

const PUMPFUN_API = 'https://frontend-api-v3.pump.fun';
const PUMPFUN_TOKEN = 'jk1T35eWK41MBMM8AWoYVaNbjHEEQzMDetTsfnqpump';

// Polling intervals (in ms)
const SENSOR_POLL_INTERVAL = 2 * 60 * 1000;  // 2 minutes
const TOKEN_POLL_INTERVAL = 60 * 1000;        // 1 minute

// Cache for latest data (avoid hammering Martin's server)
let cachedStatus = null;
let cachedStatusTime = 0;
const CACHE_TTL = 30 * 1000; // 30 seconds

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Serve index.html for root
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// ============================================
// API Routes
// ============================================

/**
 * GET /api/status
 * Returns current sensor status (from cache or Martin's API)
 */
app.get('/api/status', async (req, res) => {
    try {
        const now = Date.now();

        // Return cached data if fresh
        if (cachedStatus && (now - cachedStatusTime) < CACHE_TTL) {
            return res.json(cachedStatus);
        }

        // Fetch fresh data from Martin's API
        const response = await fetch(`${MARTIN_API.status}?t=${now}`);
        if (!response.ok) {
            throw new Error(`Martin API returned ${response.status}`);
        }

        const data = await response.json();
        cachedStatus = data;
        cachedStatusTime = now;

        res.json(data);
    } catch (error) {
        console.error('Error fetching status:', error.message);

        // Return cached data even if stale
        if (cachedStatus) {
            return res.json({ ...cachedStatus, _stale: true });
        }

        res.status(503).json({ error: 'Unable to fetch status', message: error.message });
    }
});

/**
 * GET /api/webcam
 * Proxies webcam image from Martin's server
 */
app.get('/api/webcam', async (req, res) => {
    try {
        const response = await fetch(`${MARTIN_API.webcam}?t=${Date.now()}`);
        if (!response.ok) {
            throw new Error(`Webcam API returned ${response.status}`);
        }

        const contentType = response.headers.get('content-type');
        res.setHeader('Content-Type', contentType || 'image/jpeg');
        res.setHeader('Cache-Control', 'no-cache');

        response.body.pipe(res);
    } catch (error) {
        console.error('Error fetching webcam:', error.message);
        res.status(503).json({ error: 'Webcam unavailable' });
    }
});

/**
 * GET /api/history
 * Returns historical sensor readings
 * Query params: hours (default 24), limit (default 500)
 */
app.get('/api/history', async (req, res) => {
    try {
        const hours = parseInt(req.query.hours) || 24;
        const limit = Math.min(parseInt(req.query.limit) || 500, 2000);

        const readings = await db.getReadings({ hours, limit });
        res.json({
            count: readings.length,
            hours,
            readings,
        });
    } catch (error) {
        console.error('Error fetching history:', error.message);
        res.status(500).json({ error: 'Database error', message: error.message });
    }
});

/**
 * GET /api/history/hourly
 * Returns hourly averages for charting
 * Query params: hours (default 48)
 */
app.get('/api/history/hourly', async (req, res) => {
    try {
        const hours = parseInt(req.query.hours) || 48;
        const data = await db.getHourlyAverages(hours);
        res.json({
            count: data.length,
            hours,
            data,
        });
    } catch (error) {
        console.error('Error fetching hourly averages:', error.message);
        res.status(500).json({ error: 'Database error', message: error.message });
    }
});

/**
 * GET /api/history/daily
 * Returns daily averages for charting
 * Query params: days (default 30)
 */
app.get('/api/history/daily', async (req, res) => {
    try {
        const days = parseInt(req.query.days) || 30;
        const data = await db.getDailyAverages(days);
        res.json({
            count: data.length,
            days,
            data,
        });
    } catch (error) {
        console.error('Error fetching daily averages:', error.message);
        res.status(500).json({ error: 'Database error', message: error.message });
    }
});

/**
 * GET /api/stats
 * Returns computed statistics for the last 24 hours
 */
app.get('/api/stats', async (req, res) => {
    try {
        const stats = await db.getStats24h();
        const totalReadings = await db.getReadingCount();

        res.json({
            period: '24h',
            total_readings_all_time: totalReadings,
            ...stats,
        });
    } catch (error) {
        console.error('Error fetching stats:', error.message);
        res.status(500).json({ error: 'Database error', message: error.message });
    }
});

/**
 * GET /api/token
 * Returns current pump.fun token data
 */
app.get('/api/token', async (req, res) => {
    try {
        const response = await fetch(`${PUMPFUN_API}/coins/${PUMPFUN_TOKEN}`);
        if (!response.ok) {
            throw new Error(`Pump.fun API returned ${response.status}`);
        }

        const data = await response.json();
        res.json(data);
    } catch (error) {
        console.error('Error fetching token data:', error.message);
        res.status(503).json({ error: 'Unable to fetch token data' });
    }
});

/**
 * GET /api/token/history
 * Returns historical token metrics
 */
app.get('/api/token/history', async (req, res) => {
    try {
        const hours = parseInt(req.query.hours) || 24;
        const data = await db.getTokenHistory(hours);
        res.json({
            count: data.length,
            hours,
            data,
        });
    } catch (error) {
        console.error('Error fetching token history:', error.message);
        res.status(500).json({ error: 'Database error', message: error.message });
    }
});

/**
 * GET /api/health
 * Health check endpoint
 */
app.get('/api/health', async (req, res) => {
    const dbHealth = await db.healthCheck();
    const totalReadings = dbHealth.ok ? await db.getReadingCount() : 0;

    res.json({
        status: dbHealth.ok ? 'healthy' : 'degraded',
        database: dbHealth,
        total_readings: totalReadings,
        uptime: process.uptime(),
        cached_status_age: cachedStatus ? Date.now() - cachedStatusTime : null,
    });
});

// ============================================
// Background Polling Jobs
// ============================================

let isPolling = false;

/**
 * Poll Martin's API and store sensor data
 */
async function pollSensorData() {
    if (isPolling) return;
    isPolling = true;

    try {
        console.log(`[${new Date().toISOString()}] Polling sensor data...`);

        const response = await fetch(`${MARTIN_API.status}?t=${Date.now()}`);
        if (!response.ok) {
            throw new Error(`Status API returned ${response.status}`);
        }

        const data = await response.json();

        // Update cache
        cachedStatus = data;
        cachedStatusTime = Date.now();

        // Store in database
        const result = await db.storeSensorReading(data);
        console.log(`[${new Date().toISOString()}] Stored reading #${result.id}`);

        // Store verdant output if present
        if (data.verdant_output) {
            const outputResult = await db.storeVerdantOutput(data.sol_day, data.verdant_output);
            if (outputResult) {
                console.log(`[${new Date().toISOString()}] Stored new verdant output #${outputResult.id}`);
            }
        }
    } catch (error) {
        console.error(`[${new Date().toISOString()}] Sensor poll error:`, error.message);
    } finally {
        isPolling = false;
    }
}

/**
 * Poll pump.fun API and store token metrics
 */
async function pollTokenData() {
    try {
        console.log(`[${new Date().toISOString()}] Polling token data...`);

        const response = await fetch(`${PUMPFUN_API}/coins/${PUMPFUN_TOKEN}`);
        if (!response.ok) {
            throw new Error(`Pump.fun API returned ${response.status}`);
        }

        const data = await response.json();
        const result = await db.storeTokenMetrics(data);
        console.log(`[${new Date().toISOString()}] Stored token metrics #${result.id}`);
    } catch (error) {
        console.error(`[${new Date().toISOString()}] Token poll error:`, error.message);
    }
}

// ============================================
// Server Startup
// ============================================

async function startServer() {
    try {
        // Check database connection
        console.log('Checking database connection...');
        const health = await db.healthCheck();

        if (!health.ok) {
            console.error('Database connection failed:', health.error);
            console.log('Attempting to initialize schema...');
        }

        // Initialize schema (safe to run multiple times)
        try {
            await db.initializeSchema();
        } catch (schemaError) {
            console.log('Schema may already exist:', schemaError.message);
        }

        // Start polling jobs
        console.log('Starting background polling jobs...');

        // Initial poll
        pollSensorData();
        pollTokenData();

        // Schedule recurring polls
        setInterval(pollSensorData, SENSOR_POLL_INTERVAL);
        setInterval(pollTokenData, TOKEN_POLL_INTERVAL);

        // Start HTTP server
        app.listen(PORT, () => {
            console.log(`
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║   🌱 Sol Biodome Dashboard Server                          ║
║                                                            ║
║   Running on: http://localhost:${PORT}                       ║
║                                                            ║
║   API Endpoints:                                           ║
║   • GET /api/status          - Current sensor data         ║
║   • GET /api/webcam          - Live webcam image           ║
║   • GET /api/history         - Historical readings         ║
║   • GET /api/history/hourly  - Hourly averages             ║
║   • GET /api/history/daily   - Daily averages              ║
║   • GET /api/stats           - 24h statistics              ║
║   • GET /api/token           - Pump.fun token data         ║
║   • GET /api/token/history   - Token metrics history       ║
║   • GET /api/health          - Health check                ║
║                                                            ║
║   Polling: Sensors every 2min, Token every 1min            ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
            `);
        });
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
}

// Handle graceful shutdown
process.on('SIGTERM', async () => {
    console.log('Shutting down...');
    const pool = db.getPool();
    await pool.end();
    process.exit(0);
});

startServer();
