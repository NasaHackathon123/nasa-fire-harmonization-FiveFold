-- Migration design only; not executed or connected to the current API.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE data_sources (id text PRIMARY KEY, checksum text NOT NULL, metadata jsonb NOT NULL);
CREATE TABLE raw_observations (id bigserial PRIMARY KEY, source_id text REFERENCES data_sources(id), attributes jsonb NOT NULL);
CREATE TABLE grid_cells (cell_id text PRIMARY KEY, geom geometry(Polygon,32749) NOT NULL);
CREATE INDEX grid_cells_geom_idx ON grid_cells USING gist(geom);
CREATE TABLE clean_observations (id bigserial PRIMARY KEY, source_id text REFERENCES data_sources(id), timestamp_utc timestamptz NOT NULL, sensor text NOT NULL, collection text NOT NULL, confidence_native text NOT NULL, geom geometry(Point,4326) NOT NULL, cell_id text REFERENCES grid_cells(cell_id), attributes jsonb NOT NULL);
CREATE INDEX observations_geom_idx ON clean_observations USING gist(geom);
CREATE INDEX observations_source_time_idx ON clean_observations(source_id,timestamp_utc);
CREATE TABLE cell_daily_activity (cell_id text REFERENCES grid_cells(cell_id), source text NOT NULL, collection text NOT NULL, day date NOT NULL, policy text NOT NULL, detections bigint NOT NULL, PRIMARY KEY(cell_id,source,collection,day,policy));
CREATE TABLE monthly_summaries (region text NOT NULL, source text NOT NULL, collection text NOT NULL, month date NOT NULL, policy text NOT NULL, method text NOT NULL, metrics jsonb NOT NULL, PRIMARY KEY(region,source,collection,month,policy,method));
CREATE TABLE harmonization_models (id text PRIMARY KEY, validated boolean NOT NULL DEFAULT false, metadata jsonb NOT NULL);
CREATE TABLE harmonized_activity (model_id text REFERENCES harmonization_models(id), region text NOT NULL, month date NOT NULL, estimate double precision, PRIMARY KEY(model_id,region,month));
