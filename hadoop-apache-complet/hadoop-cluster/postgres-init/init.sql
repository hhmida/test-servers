-- Create database and user for Hue
CREATE DATABASE hue;
CREATE USER hue WITH PASSWORD 'hue';
GRANT ALL PRIVILEGES ON DATABASE hue TO hue;

-- Ensure hive user can use the metastore database (already created by POSTGRES_DB)
GRANT ALL PRIVILEGES ON DATABASE metastore TO hive;
