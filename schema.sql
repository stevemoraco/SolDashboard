-- Sol Biodome Dashboard - Database Schema
-- PostgreSQL (Neon DB compatible)

-- Sensor readings with device states
CREATE TABLE IF NOT EXISTS sensor_readings (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    source_timestamp TIMESTAMPTZ,  -- Original timestamp from Martin's API
    sol_day INTEGER,

    -- Sensor readings
    air_temp DECIMAL(5,2),
    humidity DECIMAL(5,2),
    vpd DECIMAL(6,4),
    soil_moisture DECIMAL(5,2),
    co2 DECIMAL(7,2),
    leaf_temp_delta DECIMAL(5,2),

    -- Device states
    grow_light BOOLEAN DEFAULT FALSE,
    heat_mat BOOLEAN DEFAULT FALSE,
    circulation_fan BOOLEAN DEFAULT FALSE,
    exhaust_fan BOOLEAN DEFAULT FALSE,
    water_pump BOOLEAN DEFAULT FALSE,
    humidifier BOOLEAN DEFAULT FALSE
);

-- Index for fast time-range queries
CREATE INDEX IF NOT EXISTS idx_readings_recorded_at ON sensor_readings(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_readings_sol_day ON sensor_readings(sol_day);

-- Verdant AI outputs (Claude's observations)
CREATE TABLE IF NOT EXISTS verdant_outputs (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    sol_day INTEGER,
    output_text TEXT,
    output_hash VARCHAR(64)  -- To avoid storing duplicates
);

CREATE INDEX IF NOT EXISTS idx_outputs_recorded_at ON verdant_outputs(recorded_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_outputs_hash ON verdant_outputs(output_hash);

-- Pump.fun token metrics history
CREATE TABLE IF NOT EXISTS token_metrics (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    market_cap_sol DECIMAL(20,6),
    market_cap_usd DECIMAL(20,2),
    ath_market_cap DECIMAL(20,6),
    num_participants INTEGER,
    reply_count INTEGER,
    is_graduated BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_token_recorded_at ON token_metrics(recorded_at DESC);

-- View for hourly aggregates (useful for charts)
CREATE OR REPLACE VIEW hourly_averages AS
SELECT
    date_trunc('hour', recorded_at) AS hour,
    AVG(air_temp) AS avg_temp,
    AVG(humidity) AS avg_humidity,
    AVG(vpd) AS avg_vpd,
    AVG(soil_moisture) AS avg_soil_moisture,
    AVG(co2) AS avg_co2,
    AVG(leaf_temp_delta) AS avg_leaf_delta,
    COUNT(*) AS reading_count
FROM sensor_readings
GROUP BY date_trunc('hour', recorded_at)
ORDER BY hour DESC;

-- View for daily aggregates
CREATE OR REPLACE VIEW daily_averages AS
SELECT
    date_trunc('day', recorded_at) AS day,
    MAX(sol_day) AS sol_day,
    AVG(air_temp) AS avg_temp,
    MIN(air_temp) AS min_temp,
    MAX(air_temp) AS max_temp,
    AVG(humidity) AS avg_humidity,
    AVG(vpd) AS avg_vpd,
    AVG(soil_moisture) AS avg_soil_moisture,
    AVG(co2) AS avg_co2,
    COUNT(*) AS reading_count
FROM sensor_readings
GROUP BY date_trunc('day', recorded_at)
ORDER BY day DESC;

-- View for current stats (last 24 hours)
CREATE OR REPLACE VIEW current_stats AS
SELECT
    COUNT(*) AS readings_24h,
    AVG(air_temp) AS avg_temp_24h,
    MIN(air_temp) AS min_temp_24h,
    MAX(air_temp) AS max_temp_24h,
    AVG(humidity) AS avg_humidity_24h,
    AVG(vpd) AS avg_vpd_24h,
    MIN(vpd) AS min_vpd_24h,
    MAX(vpd) AS max_vpd_24h,
    AVG(soil_moisture) AS avg_soil_24h,
    AVG(co2) AS avg_co2_24h
FROM sensor_readings
WHERE recorded_at > NOW() - INTERVAL '24 hours';
