CREATE TABLE IF NOT EXISTS weather_logs(
    id          BIGSERIAL PRIMARY KEY,
    station     TEXT,
    ts          TIMESTAMPTZ,
    temp        NUMERIC(4,1),
    rh          INTEGER,
    pres        NUMERIC(6,2),
    wind        INTEGER,
    rain        NUMERIC(5,2),
    received_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(station, ts)
);
CREATE INDEX idx_station_ts ON weather_logs(station, ts);