-- schema.sql: Core database structure for the Marketing Agent

-- 1. Brand Integrations: Stores OAuth tokens and property IDs for different platforms
CREATE TABLE IF NOT EXISTS brand_integrations (
    id SERIAL PRIMARY KEY,
    brand_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL, -- 'ga4', 'google_ads', 'meta_ads', 'shopify'
    property_id VARCHAR(100),       -- GA4 Property ID or Shopify Store URL
    refresh_token TEXT NOT NULL,
    access_token TEXT,             -- Optional: Cached temporary access token
    token_expires_at TIMESTAMP,    -- Optional: Expiration for access_token
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(brand_id, platform)
);

-- 2. Raw Daily Metrics: Store initial snapshots from the ingestion layer
CREATE TABLE IF NOT EXISTS raw_daily_metrics (
    id SERIAL PRIMARY KEY,
    brand_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    source_medium VARCHAR(100),
    metrics JSONB NOT NULL,        -- Dynamic JSON to store varying metrics based on source
    dimensions JSONB NOT NULL,     -- Dynamic JSON for source-specific dimensions
    platform VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for faster querying
CREATE INDEX IF NOT EXISTS idx_brand_platform ON brand_integrations(brand_id, platform);
CREATE INDEX IF NOT EXISTS idx_metrics_date_brand ON raw_daily_metrics(date, brand_id);
