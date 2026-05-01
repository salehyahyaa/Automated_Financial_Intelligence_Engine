import logging

class DataAutomation:
    """
    Stores Plaid item and account data to the DB. Single responsibility; uses Connection (composition).
    plaid_item_id == represents a susccessful connection to a finaincal institution //not per account you have
    plaid_items_id_colum == holds the PK of the row created by your specific query in your session.
        //saves an extra query to db because insted of getting that most recent row you have that data already held in the felid
    """

    def __init__(self, connection):
        self._connection = connection
        self.logger = logging.getLogger(__name__)


    def store_plaid_item_id(self, plaid_item_id, app_user_id=None):
        """Store plaid_item_id into plaid_items table. Returns the new row id (plaid_items_id_column)."""
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                INSERT INTO plaid_items (plaid_item_id, status, app_user_id)
                VALUES (%s, 'active', %s)
                RETURNING id
                """,
                (plaid_item_id, app_user_id),
            )
            plaid_items_id_column = cur.fetchone()[0]
            self._connection.get_connection().commit()
            return plaid_items_id_column
        except Exception as e:
            self._connection.get_connection().rollback()
            self.logger.error("Error storing plaid item id", exc_info=True)
            raise Exception(f"Failed to store item_id: {str(e)}")
        finally:
            cur.close()

    def get_latest_plaid_item(self, app_user_id=None):
        """Return (plaid_items_id_column, access_token) for the user's most recent linked item, or None."""
        cur = self._connection.cursor()
        try:
            if app_user_id:
                cur.execute(
                    """
                    SELECT id, access_token
                    FROM plaid_items
                    WHERE access_token IS NOT NULL AND app_user_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (app_user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, access_token
                    FROM plaid_items
                    WHERE access_token IS NOT NULL
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                )
            row = cur.fetchone()
            return (row[0], row[1]) if row else None
        finally:
            cur.close()


    def store_access_token(self, access_token, plaid_items_id_column):
        """UPDATE access_token column FROM plaid_items table."""
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                UPDATE plaid_items
                SET access_token = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id
                """,
                (access_token, plaid_items_id_column)
            )
            result = cur.fetchone()
            if result:
                self._connection.get_connection().commit()
                return result[0]
            else:
                raise Exception("No row found to update")
        except Exception as e:
            self._connection.get_connection().rollback()
            self.logger.error("Error storing access token", exc_info=True)
            raise Exception(f"Failed to store access_token: {str(e)}")
        finally:
            cur.close()

    def update_plaid_item_label(self, plaid_items_pk, name=None, bank=None):
        """Persist institution label on plaid_items (varchar 100 in schema)."""
        if name is None and bank is None:
            return
        cur = self._connection.cursor()
        try:
            parts = []
            params = []
            if name is not None:
                n = str(name).strip()[:100]
                if n:
                    parts.append("name = %s")
                    params.append(n)
            if bank is not None:
                b = str(bank).strip()[:100]
                if b:
                    parts.append("bank = %s")
                    params.append(b)
            if not parts:
                return
            params.append(plaid_items_pk)
            cur.execute(
                f"UPDATE plaid_items SET {', '.join(parts)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                tuple(params),
            )
            self._connection.get_connection().commit()
        except Exception as e:
            self._connection.get_connection().rollback()
            self.logger.error("Error updating plaid_items label", exc_info=True)
            raise Exception(f"Failed to update plaid_items label: {str(e)}") from e
        finally:
            cur.close()

    def plaid_item_label_is_blank(self, plaid_items_pk):
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                SELECT COALESCE(NULLIF(TRIM(name), ''), NULLIF(TRIM(bank), '')) IS NULL
                FROM plaid_items
                WHERE id = %s
                """,
                (plaid_items_pk,),
            )
            row = cur.fetchone()
            if not row:
                return True
            return bool(row[0])
        finally:
            cur.close()

    def store_checking_accounts(self, checking_accounts, plaid_items_id_column):
        """INSERT into accounts table, Storing data for checking accounts //mask shows account to user without exposing account number"""
        cur = self._connection.cursor()
        try:
            for account in checking_accounts:
                cur.execute(
                    """
                    INSERT INTO accounts (
                        plaid_item_id, plaid_account_id, bank, name, mask, account_type,
                        current_balance, currency_code, status, last_synced_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (plaid_item_id, plaid_account_id) 
                    DO UPDATE SET
                        bank = EXCLUDED.bank,
                        name = EXCLUDED.name,
                        mask = EXCLUDED.mask,
                        account_type = EXCLUDED.account_type,
                        current_balance = EXCLUDED.current_balance,
                        currency_code = EXCLUDED.currency_code,
                        status = EXCLUDED.status,
                        last_synced_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    """, #when updating the row's data we need to assign the column(variable) its new data(value)
                    (
                        plaid_items_id_column,
                        account.account_id,
                        getattr(account, "bank", None),
                        account.name,
                        getattr(account, "mask", None),
                        account.type.value if hasattr(account.type, "value") else str(account.type),
                        account.balances.current if account.balances else None,
                        account.balances.iso_currency_code if account.balances else "USD",
                        "open",
                    ),
                )
            self._connection.get_connection().commit()
            return len(checking_accounts)
        except Exception as e:
            self._connection.get_connection().rollback()
            raise Exception(f"Failed to store checking accounts: {str(e)}")
        finally:
            cur.close()


    def store_credit_accounts(self, credit_accounts, plaid_items_id_column):
        """INSERT creditC accounts into accounts table."""
        cur = self._connection.cursor()
        try:
            for account in credit_accounts:
                cur.execute(
                    """
                    INSERT INTO accounts (
                        plaid_item_id, plaid_account_id, bank, name, mask, account_type,
                        balance_owed, credit_limit, currency_code, status, last_synced_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (plaid_item_id, plaid_account_id) 
                    DO UPDATE SET 
                    bank = EXCLUDED.bank, 
                    name = EXCLUDED.name,
                    mask = EXCLUDED.mask,
                    account_type = EXCLUDED.account_type,
                    balance_owed = EXCLUDED.balance_owed,
                    credit_limit = EXCLUDED.credit_limit,
                    currency_code = EXCLUDED.currency_code,
                    status = EXCLUDED.status,
                    last_synced_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        plaid_items_id_column,
                        account.account_id,
                        getattr(account, "bank", None),
                        account.name,
                        getattr(account, "mask", None),
                        account.type.value if hasattr(account.type, "value") else str(account.type),
                        account.balances.current if account.balances else None,
                        getattr(account.balances, "limit", None) if account.balances else None,
                        account.balances.iso_currency_code if account.balances else "USD",
                        "open",
                    ),
                )
            self._connection.get_connection().commit()
            return len(credit_accounts)
        except Exception as e:
            self._connection.get_connection().rollback()
            self.logger.error("Error storing credit accounts", exc_info=True)
            raise Exception(f"Failed to store credit accounts: {str(e)}")
        finally:
            cur.close()


    def store_transactions(self, transactions, plaid_items_id_column):
        """INSERT into account_transactions (account_id, plaid_transaction_id, amount, date, transaction_time, merchant_name, category, status, iso_currency_code). transactions: list of dicts with plaid_account_id, plaid_transaction_id, date, amount, transaction_time, merchant_name, category, status, iso_currency_code. Resolves plaid_account_id to account_id. ON CONFLICT DO NOTHING. Returns number inserted."""
        if not transactions:
            return 0
        cur = self._connection.cursor()
        try:
            cur.execute("SELECT id, plaid_account_id FROM accounts WHERE plaid_item_id = %s", (plaid_items_id_column,))
            plaid_to_account_id = {row[1]: row[0] for row in cur.fetchall()}
            inserted = 0
            for t in transactions:
                account_id = plaid_to_account_id.get(t["plaid_account_id"])
                if account_id is None:
                    continue
                cur.execute(
                    """
                    INSERT INTO account_transactions (
                        account_id, plaid_transaction_id, amount, date, transaction_time,
                        merchant_name, category, status, iso_currency_code
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (account_id, plaid_transaction_id) DO NOTHING
                    """,
                    (
                        account_id,
                        t["plaid_transaction_id"],
                        t["amount"],
                        t["date"],
                        t.get("transaction_time"),
                        t.get("merchant_name"),
                        t.get("category"),
                        t.get("status", "posted"),
                        t.get("iso_currency_code") or "USD",
                    ),
                )
                if cur.rowcount:
                    inserted += 1
            self._connection.get_connection().commit()
            return inserted
        except Exception as e:
            self._connection.get_connection().rollback()
            self.logger.error("Error storing transactions", exc_info=True)
            raise Exception(f"Failed to store transactions: {str(e)}")
        finally:
            cur.close()

    def get_transactions_sync_cursor(self, plaid_items_id_column):
        cur = self._connection.cursor()
        try:
            cur.execute(
                "SELECT transactions_sync_cursor FROM plaid_items WHERE id = %s",
                (plaid_items_id_column,),
            )
            row = cur.fetchone()
            return row[0] if row and row[0] else ""
        finally:
            cur.close()

    def set_transactions_sync_cursor(self, plaid_items_id_column, cursor_value):
        if cursor_value is None:
            return
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                UPDATE plaid_items
                SET transactions_sync_cursor = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (cursor_value, plaid_items_id_column),
            )
            self._connection.get_connection().commit()
        except Exception as e:
            self._connection.get_connection().rollback()
            self.logger.error("Error saving sync cursor", exc_info=True)
            raise Exception(f"Failed to save sync cursor: {str(e)}")
        finally:
            cur.close()

    def delete_transactions_by_plaid_ids(self, plaid_items_id_column, plaid_transaction_ids):
        if not plaid_transaction_ids:
            return 0
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                DELETE FROM account_transactions t
                USING accounts a
                WHERE t.account_id = a.id
                  AND a.plaid_item_id = %s
                  AND t.plaid_transaction_id = ANY(%s)
                """,
                (plaid_items_id_column, list(plaid_transaction_ids)),
            )
            deleted = cur.rowcount
            self._connection.get_connection().commit()
            return deleted
        except Exception as e:
            self._connection.get_connection().rollback()
            self.logger.error("Error deleting transactions", exc_info=True)
            raise Exception(f"Failed to delete transactions: {str(e)}")
        finally:
            cur.close()

    def fetch_transactions_for_analytics(self, plaid_items_id_column):
        """Rows as dicts compatible with StatisticalAnalytics (Plaid amount sign)."""
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                SELECT t.plaid_transaction_id, t.amount, t.date, t.transaction_time,
                       t.merchant_name, t.category, t.status::text AS status,
                       t.iso_currency_code, a.plaid_account_id, a.name AS account_name,
                       a.account_type::text AS account_type
                FROM account_transactions t
                JOIN accounts a ON a.id = t.account_id
                WHERE a.plaid_item_id = %s
                ORDER BY t.date ASC, t.id ASC
                """,
                (plaid_items_id_column,),
            )
            cols = [d[0] for d in cur.description]
            rows = []
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                d["date"] = d["date"].isoformat() if hasattr(d["date"], "isoformat") else str(d["date"])
                if d.get("amount") is not None:
                    d["amount"] = float(d["amount"])
                rows.append(d)
            return rows
        finally:
            cur.close()

    def fetch_account_balances(self, plaid_items_id_column):
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                SELECT plaid_account_id, bank, mask, name, account_type::text,
                       current_balance, balance_owed, credit_limit
                FROM accounts
                WHERE plaid_item_id = %s
                ORDER BY id
                """,
                (plaid_items_id_column,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            cur.close()

    def fetch_plaid_item_meta(self, plaid_items_pk):
        """Institution / item label for dashboards (plaid_items.id = PK)."""
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                SELECT COALESCE(
                       NULLIF(TRIM(pi.name), ''),
                       NULLIF(TRIM(pi.bank), ''),
                       (SELECT NULLIF(TRIM(a.bank), '')
                        FROM accounts a
                        WHERE a.plaid_item_id = pi.id
                          AND NULLIF(TRIM(a.bank), '') IS NOT NULL
                        LIMIT 1),
                       'Linked institution'
                   ),
                       pi.bank,
                       pi.name,
                       pi.plaid_item_id
                FROM plaid_items pi
                WHERE pi.id = %s
                """,
                (plaid_items_pk,),
            )
            row = cur.fetchone()
            if not row:
                return {"display_name": "Linked institution", "bank": None, "name": None, "plaid_item_id": None}
            return {
                "display_name": row[0],
                "bank": row[1],
                "name": row[2],
                "plaid_item_id": row[3],
            }
        finally:
            cur.close()

    def fetch_linked_accounts_for_app_user(self, app_user_id=None):
        """
        All linked accounts visible to this app user (plaid_items.access_token set).
        app_user_id None matches plaid_items.app_user_id IS NULL (legacy single-user DB).
        """
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                SELECT a.id, a.name, a.bank, a.mask, a.account_type::text AS account_type,
                       a.plaid_item_id AS plaid_item_fk,
                       COALESCE(
                           NULLIF(TRIM(pi.name), ''),
                           NULLIF(TRIM(pi.bank), ''),
                           NULLIF(TRIM(a.bank), ''),
                           'Linked institution'
                       ) AS institution
                FROM accounts a
                INNER JOIN plaid_items pi ON pi.id = a.plaid_item_id
                WHERE pi.access_token IS NOT NULL
                  AND pi.app_user_id IS NOT DISTINCT FROM %s
                ORDER BY pi.id DESC, a.id ASC
                """,
                (app_user_id,),
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            cur.close()

    def get_plaid_item_for_account_delink(self, account_db_id, app_user_id=None):
        """
        Return (plaid_items_pk, access_token) if account belongs to an item owned by app_user_id, else None.
        """
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                SELECT pi.id, pi.access_token
                FROM accounts a
                INNER JOIN plaid_items pi ON pi.id = a.plaid_item_id
                WHERE a.id = %s
                  AND pi.app_user_id IS NOT DISTINCT FROM %s
                """,
                (account_db_id, app_user_id),
            )
            row = cur.fetchone()
            return (row[0], row[1]) if row else None
        finally:
            cur.close()

    def delete_plaid_item_row(self, plaid_items_pk):
        """Delete plaid_items row (cascades accounts and dependent rows per FK)."""
        cur = self._connection.cursor()
        try:
            cur.execute("DELETE FROM plaid_items WHERE id = %s RETURNING id", (plaid_items_pk,))
            deleted = cur.fetchone()
            self._connection.get_connection().commit()
            return deleted[0] if deleted else None
        except Exception as e:
            self._connection.get_connection().rollback()
            self.logger.error("Error deleting plaid_items row", exc_info=True)
            raise Exception(f"Failed to delete linked item: {str(e)}") from e
        finally:
            cur.close()

    def fetch_recent_transactions_dashboard(self, plaid_items_id_column, limit=25):
        """Latest transactions for UI (newest first)."""
        cur = self._connection.cursor()
        try:
            cur.execute(
                """
                SELECT t.date, t.amount, t.merchant_name, t.category, t.status::text AS status,
                       a.name AS account_name, a.mask AS account_mask
                FROM account_transactions t
                JOIN accounts a ON a.id = t.account_id
                WHERE a.plaid_item_id = %s
                ORDER BY t.date DESC, t.id DESC
                LIMIT %s
                """,
                (plaid_items_id_column, limit),
            )
            cols = [d[0] for d in cur.description]
            out = []
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                d["date"] = d["date"].isoformat() if hasattr(d["date"], "isoformat") else str(d["date"])
                if d.get("amount") is not None:
                    d["amount"] = float(d["amount"])
                out.append(d)
            return out
        finally:
            cur.close()


"""
plaid_items_id_column:
we store the recent id incremrented count in the vairable plaid_items_id_column to save a hit to the db, this is benficial for performace and scalability
"""