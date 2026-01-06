/**
 * Database module for Sol Biodome Dashboard
 * Handles PostgreSQL connection and queries
 */

const { Pool } = require('pg');
const crypto = require('crypto');

// Connection pool (lazy initialized)
let pool = null;

function getPool() {
    if (!pool) {
        const connectionString = process.env.DATABASE_URL;
        if (!connectionString) {
            throw new Error('DATABASE_URL environment variable is required');
        }
        pool = new Pool({
            connectionString,
            ssl: { rejectUnauthorized: false }, // Required for Neon
            max: 10,
            idleTimeoutMillis: 30000,
        });
    }
    return pool;
}

/**
 * Store a sensor reading in the database
 */
async function storeSensorReading(data) {
    const query = `
        INSERT INTO sensor_readings (
            source_timestamp, sol_day,
            air_temp, humidity, vpd, soil_moisture, co2, leaf_temp_delta,
            grow_light, heat_mat, circulation_fan, exhaust_fan, water_pump, humidifier
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        RETURNING id, recorded_at
    `;

    const values = [
        data.timestamp || null,
        data.sol_day || null,
        data.sensors?.air_temp || null,
        data.sensors?.humidity || null,
        data.sensors?.vpd || null,
        data.sensors?.soil_moisture || null,
        data.sensors?.co2 || null,
        data.sensors?.leaf_temp_delta || null,
        data.devices?.grow_light || false,
        data.devices?.heat_mat || false,
        data.devices?.circulation_fan || false,
        data.devices?.exhaust_fan || false,
        data.devices?.water_pump || false,
        data.devices?.humidifier || false,
    ];

    const result = await getPool().query(query, values);
    return result.rows[0];
}

/**
 * Store verdant output (only if it's new/different)
 */
async function storeVerdantOutput(solDay, outputText) {
    const hash = crypto.createHash('sha256').update(outputText).digest('hex');

    const query = `
        INSERT INTO verdant_outputs (sol_day, output_text, output_hash)
        VALUES ($1, $2, $3)
        ON CONFLICT (output_hash) DO NOTHING
        RETURNING id
    `;

    const result = await getPool().query(query, [solDay, outputText, hash]);
    return result.rows[0] || null;
}

/**
 * Store token metrics
 */
async function storeTokenMetrics(data) {
    const query = `
        INSERT INTO token_metrics (
            market_cap_sol, market_cap_usd, ath_market_cap,
            num_participants, reply_count, is_graduated
        ) VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, recorded_at
    `;

    const values = [
        data.market_cap || null,
        data.usd_market_cap || null,
        data.ath_market_cap || null,
        data.num_participants || null,
        data.reply_count || null,
        data.complete || false,
    ];

    const result = await getPool().query(query, values);
    return result.rows[0];
}

/**
 * Get the latest sensor reading
 */
async function getLatestReading() {
    const query = `
        SELECT * FROM sensor_readings
        ORDER BY recorded_at DESC
        LIMIT 1
    `;
    const result = await getPool().query(query);
    return result.rows[0] || null;
}

/**
 * Get sensor readings for a time range
 */
async function getReadings(options = {}) {
    const {
        hours = 24,
        limit = 500,
        offset = 0,
    } = options;

    const query = `
        SELECT
            id, recorded_at, sol_day,
            air_temp, humidity, vpd, soil_moisture, co2, leaf_temp_delta,
            grow_light, heat_mat, circulation_fan, exhaust_fan, water_pump, humidifier
        FROM sensor_readings
        WHERE recorded_at > NOW() - INTERVAL '${hours} hours'
        ORDER BY recorded_at DESC
        LIMIT $1 OFFSET $2
    `;

    const result = await getPool().query(query, [limit, offset]);
    return result.rows;
}

/**
 * Get hourly averages for charts
 */
async function getHourlyAverages(hours = 48) {
    const query = `
        SELECT
            date_trunc('hour', recorded_at) AS hour,
            AVG(air_temp)::numeric(5,2) AS avg_temp,
            AVG(humidity)::numeric(5,2) AS avg_humidity,
            AVG(vpd)::numeric(6,4) AS avg_vpd,
            AVG(soil_moisture)::numeric(5,2) AS avg_soil_moisture,
            AVG(co2)::numeric(7,2) AS avg_co2,
            AVG(leaf_temp_delta)::numeric(5,2) AS avg_leaf_delta,
            COUNT(*) AS reading_count
        FROM sensor_readings
        WHERE recorded_at > NOW() - INTERVAL '${hours} hours'
        GROUP BY date_trunc('hour', recorded_at)
        ORDER BY hour ASC
    `;

    const result = await getPool().query(query);
    return result.rows;
}

/**
 * Get daily averages
 */
async function getDailyAverages(days = 30) {
    const query = `
        SELECT
            date_trunc('day', recorded_at) AS day,
            MAX(sol_day) AS sol_day,
            AVG(air_temp)::numeric(5,2) AS avg_temp,
            MIN(air_temp)::numeric(5,2) AS min_temp,
            MAX(air_temp)::numeric(5,2) AS max_temp,
            AVG(humidity)::numeric(5,2) AS avg_humidity,
            AVG(vpd)::numeric(6,4) AS avg_vpd,
            AVG(soil_moisture)::numeric(5,2) AS avg_soil_moisture,
            AVG(co2)::numeric(7,2) AS avg_co2,
            COUNT(*) AS reading_count
        FROM sensor_readings
        WHERE recorded_at > NOW() - INTERVAL '${days} days'
        GROUP BY date_trunc('day', recorded_at)
        ORDER BY day ASC
    `;

    const result = await getPool().query(query);
    return result.rows;
}

/**
 * Get statistics for the last 24 hours
 */
async function getStats24h() {
    const query = `
        SELECT
            COUNT(*) AS readings_count,
            AVG(air_temp)::numeric(5,2) AS avg_temp,
            MIN(air_temp)::numeric(5,2) AS min_temp,
            MAX(air_temp)::numeric(5,2) AS max_temp,
            AVG(humidity)::numeric(5,2) AS avg_humidity,
            MIN(humidity)::numeric(5,2) AS min_humidity,
            MAX(humidity)::numeric(5,2) AS max_humidity,
            AVG(vpd)::numeric(6,4) AS avg_vpd,
            MIN(vpd)::numeric(6,4) AS min_vpd,
            MAX(vpd)::numeric(6,4) AS max_vpd,
            AVG(soil_moisture)::numeric(5,2) AS avg_soil,
            MIN(soil_moisture)::numeric(5,2) AS min_soil,
            MAX(soil_moisture)::numeric(5,2) AS max_soil,
            AVG(co2)::numeric(7,2) AS avg_co2,
            MIN(co2)::numeric(7,2) AS min_co2,
            MAX(co2)::numeric(7,2) AS max_co2
        FROM sensor_readings
        WHERE recorded_at > NOW() - INTERVAL '24 hours'
    `;

    const result = await getPool().query(query);
    return result.rows[0] || null;
}

/**
 * Get token metrics history
 */
async function getTokenHistory(hours = 24) {
    const query = `
        SELECT
            recorded_at,
            market_cap_sol,
            market_cap_usd,
            ath_market_cap,
            num_participants,
            reply_count
        FROM token_metrics
        WHERE recorded_at > NOW() - INTERVAL '${hours} hours'
        ORDER BY recorded_at ASC
    `;

    const result = await getPool().query(query);
    return result.rows;
}

/**
 * Get total reading count
 */
async function getReadingCount() {
    const result = await getPool().query('SELECT COUNT(*) FROM sensor_readings');
    return parseInt(result.rows[0].count, 10);
}

/**
 * Health check - verify database connection
 */
async function healthCheck() {
    try {
        const result = await getPool().query('SELECT NOW()');
        return { ok: true, timestamp: result.rows[0].now };
    } catch (error) {
        return { ok: false, error: error.message };
    }
}

/**
 * Initialize database schema
 */
async function initializeSchema() {
    const fs = require('fs');
    const path = require('path');

    const schemaPath = path.join(__dirname, 'schema.sql');
    const schema = fs.readFileSync(schemaPath, 'utf8');

    await getPool().query(schema);
    console.log('Database schema initialized');
}

module.exports = {
    getPool,
    storeSensorReading,
    storeVerdantOutput,
    storeTokenMetrics,
    getLatestReading,
    getReadings,
    getHourlyAverages,
    getDailyAverages,
    getStats24h,
    getTokenHistory,
    getReadingCount,
    healthCheck,
    initializeSchema,
};
