-- v0.2.48 DMS skeleton - tenant tables (schema-per-tenant)
-- Apply with search_path set to tenant schema (e.g., SET search_path TO tenant_<id>, shared, public);

CREATE TABLE IF NOT EXISTS dms_document_types (
  id uuid PRIMARY KEY,
  code varchar(64) NOT NULL UNIQUE,
  domain varchar(16) NOT NULL, -- CAMO | MRO | STORES
  title varchar(128) NOT NULL,
  requires_signature boolean NOT NULL DEFAULT false,
  printable boolean NOT NULL DEFAULT false,
  retention_years integer,
  immutable_after varchar(16) NOT NULL DEFAULT 'ISSUED', -- ISSUED | SIGNED
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dms_documents (
  id uuid PRIMARY KEY,
  type_code varchar(64) NOT NULL REFERENCES dms_document_types(code) ON UPDATE CASCADE ON DELETE RESTRICT,
  status varchar(16) NOT NULL DEFAULT 'DRAFT',
  title varchar(255),
  entity_kind varchar(32), -- AIRCRAFT | WORK_ORDER | PART | OTHER
  entity_id uuid,
  issued_at timestamptz,
  effective_at timestamptz,
  created_by_sub varchar(128),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_dms_doc_status CHECK (status IN ('DRAFT','REVIEW','APPROVED','ISSUED','SIGNED','ARCHIVED'))
);

CREATE INDEX IF NOT EXISTS ix_dms_documents_type_code ON dms_documents(type_code);
CREATE INDEX IF NOT EXISTS ix_dms_documents_status ON dms_documents(status);
CREATE INDEX IF NOT EXISTS ix_dms_documents_entity ON dms_documents(entity_kind, entity_id);

CREATE TABLE IF NOT EXISTS dms_attachments (
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES dms_documents(id) ON DELETE CASCADE,
  filename varchar(255) NOT NULL,
  content_type varchar(128),
  storage_key varchar(512) NOT NULL,
  sha256 varchar(64),
  size_bytes bigint,
  created_by_sub varchar(128),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_dms_attachments_document_id ON dms_attachments(document_id);

CREATE TABLE IF NOT EXISTS dms_signatures (
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL REFERENCES dms_documents(id) ON DELETE CASCADE,
  signed_by_sub varchar(128) NOT NULL,
  signed_role varchar(64) NOT NULL,
  signed_at timestamptz NOT NULL DEFAULT now(),
  signature_hash varchar(64) NOT NULL,
  CONSTRAINT uq_dms_signature_per_role UNIQUE (document_id, signed_role)
);

CREATE INDEX IF NOT EXISTS ix_dms_signatures_document_id ON dms_signatures(document_id);
