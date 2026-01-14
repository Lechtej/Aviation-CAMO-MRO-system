-- 2026-01-14_01_stock_transactions_idempotency_tenant_scoped
-- Goal:
--  - replace global UNIQUE(idempotency_key) with tenant-scoped UNIQUE(tenant_id, idempotency_key)
-- Safe to re-run (IF EXISTS / IF NOT EXISTS).

BEGIN;

ALTER TABLE public.stock_transactions
  DROP CONSTRAINT IF EXISTS uq_stock_transactions_idempotency;

DROP INDEX IF EXISTS public.uq_stock_transactions_idempotency;

CREATE UNIQUE INDEX IF NOT EXISTS ux_stock_tx_tenant_idem
ON public.stock_transactions (tenant_id, idempotency_key);

COMMIT;
