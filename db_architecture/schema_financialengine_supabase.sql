-- financialengine schema (cleaned local pg_dump)
-- Removed: psql \restrict/\unrestrict (invalid in Supabase SQL editor).
-- Removed: ALTER ... OWNER TO ... (local role salehyahya does not exist on Supabase).
--
-- Apply in Supabase → SQL → New query:
--   1) Run this entire script.
--   2) Then run: db_architecture/migration_v2_user_cursor_removed.sql
--

--
-- PostgreSQL database dump
--


-- Dumped from database version 14.19 (Homebrew)
-- Dumped by pg_dump version 14.19 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: account_status; Type: TYPE; Schema: public; Owner: salehyahya
--

CREATE TYPE public.account_status AS ENUM (
    'open',
    'closed',
    'frozen'
);



--
-- Name: account_type; Type: TYPE; Schema: public; Owner: salehyahya
--

CREATE TYPE public.account_type AS ENUM (
    'debit',
    'credit',
    'not_fetched',
    'depository'
);



--
-- Name: charge_status; Type: TYPE; Schema: public; Owner: salehyahya
--

CREATE TYPE public.charge_status AS ENUM (
    'pending',
    'posted'
);



--
-- Name: item_status; Type: TYPE; Schema: public; Owner: salehyahya
--

CREATE TYPE public.item_status AS ENUM (
    'active',
    'inactive',
    'error'
);



--
-- Name: stock_trade_type; Type: TYPE; Schema: public; Owner: salehyahya
--

CREATE TYPE public.stock_trade_type AS ENUM (
    'buy',
    'sell',
    'dividend',
    'transfer'
);



SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: account_transactions; Type: TABLE; Schema: public; Owner: salehyahya
--

CREATE TABLE public.account_transactions (
    id integer NOT NULL,
    account_id integer NOT NULL,
    plaid_transaction_id character varying(255) NOT NULL,
    amount numeric(15,2) NOT NULL,
    date date NOT NULL,
    transaction_time time without time zone,
    merchant_name character varying(255),
    category character varying(100),
    status public.charge_status DEFAULT 'posted'::public.charge_status NOT NULL,
    iso_currency_code character varying(3) DEFAULT 'USD'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: account_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: salehyahya
--

CREATE SEQUENCE public.account_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: account_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: salehyahya
--

ALTER SEQUENCE public.account_transactions_id_seq OWNED BY public.account_transactions.id;


--
-- Name: accounts; Type: TABLE; Schema: public; Owner: salehyahya
--

CREATE TABLE public.accounts (
    id integer NOT NULL,
    plaid_item_id integer NOT NULL,
    plaid_account_id character varying(255) NOT NULL,
    bank character varying(100),
    name character varying(100),
    mask character varying(4),
    account_type public.account_type DEFAULT 'not_fetched'::public.account_type,
    current_balance numeric(15,2),
    balance_owed numeric(15,2),
    credit_limit numeric(15,2),
    currency_code character varying(3) DEFAULT 'USD'::character varying,
    status public.account_status DEFAULT 'open'::public.account_status,
    last_synced_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_credit_balance_owed CHECK (((account_type <> 'credit'::public.account_type) OR (balance_owed IS NOT NULL))),
    CONSTRAINT chk_credit_limit CHECK (((account_type <> 'credit'::public.account_type) OR (credit_limit IS NOT NULL)))
);



--
-- Name: accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: salehyahya
--

CREATE SEQUENCE public.accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: salehyahya
--

ALTER SEQUENCE public.accounts_id_seq OWNED BY public.accounts.id;


--
-- Name: daily_balances; Type: TABLE; Schema: public; Owner: salehyahya
--

CREATE TABLE public.daily_balances (
    id integer NOT NULL,
    account_id integer NOT NULL,
    date date NOT NULL,
    balance numeric(15,2) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: daily_balances_id_seq; Type: SEQUENCE; Schema: public; Owner: salehyahya
--

CREATE SEQUENCE public.daily_balances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: daily_balances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: salehyahya
--

ALTER SEQUENCE public.daily_balances_id_seq OWNED BY public.daily_balances.id;


--
-- Name: plaid_items; Type: TABLE; Schema: public; Owner: salehyahya
--

CREATE TABLE public.plaid_items (
    id integer NOT NULL,
    plaid_item_id character varying(255) NOT NULL,
    bank character varying(100),
    name character varying(100),
    access_token character varying(255),
    status public.item_status DEFAULT 'active'::public.item_status,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: plaid_items_id_seq; Type: SEQUENCE; Schema: public; Owner: salehyahya
--

CREATE SEQUENCE public.plaid_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: plaid_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: salehyahya
--

ALTER SEQUENCE public.plaid_items_id_seq OWNED BY public.plaid_items.id;


--
-- Name: stock_accounts; Type: TABLE; Schema: public; Owner: salehyahya
--

CREATE TABLE public.stock_accounts (
    id integer NOT NULL,
    account_id integer NOT NULL,
    brokerage_name character varying(100) NOT NULL,
    buying_power numeric(15,2) DEFAULT 0.00,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);



--
-- Name: stock_accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: salehyahya
--

CREATE SEQUENCE public.stock_accounts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: stock_accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: salehyahya
--

ALTER SEQUENCE public.stock_accounts_id_seq OWNED BY public.stock_accounts.id;


--
-- Name: stock_transactions; Type: TABLE; Schema: public; Owner: salehyahya
--

CREATE TABLE public.stock_transactions (
    id integer NOT NULL,
    stock_account_id integer NOT NULL,
    symbol character varying(10) NOT NULL,
    trade_type public.stock_trade_type NOT NULL,
    quantity numeric(18,8),
    price_per_share numeric(18,4),
    total_amount numeric(15,2) NOT NULL,
    date date NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_stock_trade_logic CHECK ((((trade_type = ANY (ARRAY['buy'::public.stock_trade_type, 'sell'::public.stock_trade_type])) AND (quantity > (0)::numeric) AND (price_per_share > (0)::numeric)) OR ((trade_type = 'dividend'::public.stock_trade_type) AND ((quantity IS NULL) OR (quantity = (0)::numeric)) AND ((price_per_share IS NULL) OR (price_per_share = (0)::numeric))) OR (trade_type = 'transfer'::public.stock_trade_type)))
);



--
-- Name: stock_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: salehyahya
--

CREATE SEQUENCE public.stock_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: stock_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: salehyahya
--

ALTER SEQUENCE public.stock_transactions_id_seq OWNED BY public.stock_transactions.id;


--
-- Name: account_transactions id; Type: DEFAULT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.account_transactions ALTER COLUMN id SET DEFAULT nextval('public.account_transactions_id_seq'::regclass);


--
-- Name: accounts id; Type: DEFAULT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.accounts ALTER COLUMN id SET DEFAULT nextval('public.accounts_id_seq'::regclass);


--
-- Name: daily_balances id; Type: DEFAULT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.daily_balances ALTER COLUMN id SET DEFAULT nextval('public.daily_balances_id_seq'::regclass);


--
-- Name: plaid_items id; Type: DEFAULT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.plaid_items ALTER COLUMN id SET DEFAULT nextval('public.plaid_items_id_seq'::regclass);


--
-- Name: stock_accounts id; Type: DEFAULT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.stock_accounts ALTER COLUMN id SET DEFAULT nextval('public.stock_accounts_id_seq'::regclass);


--
-- Name: stock_transactions id; Type: DEFAULT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.stock_transactions ALTER COLUMN id SET DEFAULT nextval('public.stock_transactions_id_seq'::regclass);


--
-- Name: account_transactions account_transactions_account_id_plaid_tx_id_key; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.account_transactions
    ADD CONSTRAINT account_transactions_account_id_plaid_tx_id_key UNIQUE (account_id, plaid_transaction_id);


--
-- Name: account_transactions account_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.account_transactions
    ADD CONSTRAINT account_transactions_pkey PRIMARY KEY (id);


--
-- Name: account_transactions account_transactions_plaid_transaction_id_key; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.account_transactions
    ADD CONSTRAINT account_transactions_plaid_transaction_id_key UNIQUE (plaid_transaction_id);


--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- Name: accounts accounts_plaid_account_id_key; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_plaid_account_id_key UNIQUE (plaid_account_id);


--
-- Name: accounts accounts_plaid_item_account_unique; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_plaid_item_account_unique UNIQUE (plaid_item_id, plaid_account_id);


--
-- Name: daily_balances daily_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.daily_balances
    ADD CONSTRAINT daily_balances_pkey PRIMARY KEY (id);


--
-- Name: plaid_items plaid_items_pkey; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.plaid_items
    ADD CONSTRAINT plaid_items_pkey PRIMARY KEY (id);


--
-- Name: plaid_items plaid_items_plaid_item_id_key; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.plaid_items
    ADD CONSTRAINT plaid_items_plaid_item_id_key UNIQUE (plaid_item_id);


--
-- Name: stock_accounts stock_accounts_account_id_key; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.stock_accounts
    ADD CONSTRAINT stock_accounts_account_id_key UNIQUE (account_id);


--
-- Name: stock_accounts stock_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.stock_accounts
    ADD CONSTRAINT stock_accounts_pkey PRIMARY KEY (id);


--
-- Name: stock_transactions stock_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.stock_transactions
    ADD CONSTRAINT stock_transactions_pkey PRIMARY KEY (id);


--
-- Name: daily_balances unique_account_day; Type: CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.daily_balances
    ADD CONSTRAINT unique_account_day UNIQUE (account_id, date);


--
-- Name: idx_accounts_plaid_item; Type: INDEX; Schema: public; Owner: salehyahya
--

CREATE INDEX idx_accounts_plaid_item ON public.accounts USING btree (plaid_item_id);


--
-- Name: idx_daily_balances_account_date; Type: INDEX; Schema: public; Owner: salehyahya
--

CREATE INDEX idx_daily_balances_account_date ON public.daily_balances USING btree (account_id, date);


--
-- Name: idx_stock_symbol_date; Type: INDEX; Schema: public; Owner: salehyahya
--

CREATE INDEX idx_stock_symbol_date ON public.stock_transactions USING btree (symbol, date);


--
-- Name: idx_transactions_account_date; Type: INDEX; Schema: public; Owner: salehyahya
--

CREATE INDEX idx_transactions_account_date ON public.account_transactions USING btree (account_id, date);


--
-- Name: idx_transactions_account_status; Type: INDEX; Schema: public; Owner: salehyahya
--

CREATE INDEX idx_transactions_account_status ON public.account_transactions USING btree (account_id, status);


--
-- Name: account_transactions fk_account_link; Type: FK CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.account_transactions
    ADD CONSTRAINT fk_account_link FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: daily_balances fk_balance_account; Type: FK CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.daily_balances
    ADD CONSTRAINT fk_balance_account FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: accounts fk_plaid_item; Type: FK CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT fk_plaid_item FOREIGN KEY (plaid_item_id) REFERENCES public.plaid_items(id) ON DELETE CASCADE;


--
-- Name: stock_accounts fk_stock_account_link; Type: FK CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.stock_accounts
    ADD CONSTRAINT fk_stock_account_link FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: stock_transactions fk_stock_account_tx; Type: FK CONSTRAINT; Schema: public; Owner: salehyahya
--

ALTER TABLE ONLY public.stock_transactions
    ADD CONSTRAINT fk_stock_account_tx FOREIGN KEY (stock_account_id) REFERENCES public.stock_accounts(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


