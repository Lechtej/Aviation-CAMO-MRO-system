-- v0.2.7 Inventory skeleton - tenant tables (schema-per-tenant)
-- Apply with search_path set to tenant schema (e.g., SET search_path TO tenant_<id>, shared, public);

CREATE TABLE IF NOT EXISTS parts (
  id uuid PRIMARY KEY,
  part_number varchar(64) NOT NULL UNIQUE,
  description varchar(255),
  part_type varchar(16) NOT NULL,
  uom_code varchar(16),
  is_pool_item boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS warehouses (
  id uuid PRIMARY KEY,
  code varchar(32) NOT NULL UNIQUE,
  name varchar(128) NOT NULL,
  is_active boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS locations (
  id uuid PRIMARY KEY,
  warehouse_id uuid NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
  code varchar(64) NOT NULL,
  name varchar(128),
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_locations_warehouse_code UNIQUE (warehouse_id, code)
);

CREATE TABLE IF NOT EXISTS stock_items (
  id uuid PRIMARY KEY,
  part_id uuid NOT NULL REFERENCES parts(id) ON DELETE RESTRICT,
  location_id uuid NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
  serial_number varchar(64),
  condition varchar(16) NOT NULL DEFAULT 'SERVICEABLE',
  owner varchar(128) NOT NULL DEFAULT 'TENANT',
  qty_on_hand numeric(14,3) NOT NULL DEFAULT 0,
  qty_reserved numeric(14,3) NOT NULL DEFAULT 0,
  qty_in_transit numeric(14,3) NOT NULL DEFAULT 0,
  CONSTRAINT uq_stock_part_loc_sn UNIQUE (part_id, location_id, serial_number),
  CONSTRAINT ck_stock_qty_on_hand_nonneg CHECK (qty_on_hand >= 0),
  CONSTRAINT ck_stock_qty_reserved_nonneg CHECK (qty_reserved >= 0),
  CONSTRAINT ck_stock_qty_in_transit_nonneg CHECK (qty_in_transit >= 0)
);
