-- v0.2.7 Inventory skeleton - shared dictionaries
CREATE SCHEMA IF NOT EXISTS shared;

CREATE TABLE IF NOT EXISTS shared.uom (
  id uuid PRIMARY KEY,
  code varchar(16) NOT NULL UNIQUE,
  name varchar(64) NOT NULL
);
