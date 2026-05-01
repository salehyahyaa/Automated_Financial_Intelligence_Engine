-- =============================================================================
-- migration_v2 — plaid_items: multi-user + Plaid sync cursor
-- =============================================================================
-- Why: schema_v1 has no per-app-user key on plaid_items, so every link looks
--      the same to the DB. app_user_id lets you attach each bank link to a
--      real user (e.g. Supabase auth sub) so the database can support many users.
--      transactions_sync_cursor stores Plaid /transactions/sync next_cursor so
--      syncs can be incremental instead of replaying from empty cursor every time.
-- Apply: run once on existing DBs after schema_v1.sql. Backend must still set
--        app_user_id on link and query by user — this file only adds columns.
-- =============================================================================

ALTER TABLE plaid_items
  ADD COLUMN IF NOT EXISTS app_user_id TEXT NULL,
  ADD COLUMN IF NOT EXISTS transactions_sync_cursor TEXT NULL;

COMMENT ON COLUMN plaid_items.app_user_id IS 'Supabase auth user id (sub) or other app user key; NULL until auth is wired.';
COMMENT ON COLUMN plaid_items.transactions_sync_cursor IS 'Last Plaid /transactions/sync next_cursor for incremental updates.';

CREATE INDEX IF NOT EXISTS idx_plaid_items_app_user ON plaid_items(app_user_id);
