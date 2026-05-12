
-- QuantPilot Schema 

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- USERS (extends Supabase auth.users)

CREATE TABLE public.profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    password_hash TEXT NOT NULL DEFAULT '',
    groq_api_key TEXT,                    -- user's own key (encrypted at app level)
    plan TEXT NOT NULL DEFAULT 'free',    -- free | pro
    backtests_this_month INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email)
  VALUES (NEW.id, NEW.email);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- STRATEGIES

CREATE TABLE public.strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,           -- original NL prompt
    generated_code TEXT,                 -- vectorbt code from LLM
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);


-- BACKTESTS

CREATE TABLE public.backtests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    strategy_id UUID REFERENCES public.strategies(id) ON DELETE SET NULL,
    
    -- Input params
    symbol TEXT NOT NULL,                -- e.g. RELIANCE, NIFTY50
    exchange TEXT NOT NULL DEFAULT 'NSE',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital NUMERIC DEFAULT 100000,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | running | completed | failed
    error_message TEXT,
    
    -- Results (stored as JSONB for flexibility)
    results JSONB,
    /*
    results shape:
    {
      "total_return_pct": 23.4,
      "cagr": 12.1,
      "sharpe_ratio": 1.4,
      "max_drawdown_pct": -18.2,
      "win_rate": 0.58,
      "total_trades": 42,
      "dsr_score": 0.76,         -- deflated sharpe ratio
      "walk_forward": {...},
      "equity_curve": [...],     -- [{date, value}, ...]
      "trades": [...]
    }
    */
    
    -- Audit
    audit_hash TEXT,                     -- SHA-256 of inputs + results
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Index for fast user queries
CREATE INDEX idx_backtests_user_id ON public.backtests(user_id);
CREATE INDEX idx_backtests_status ON public.backtests(status);
CREATE INDEX idx_backtests_created_at ON public.backtests(created_at DESC);


-- AUDIT LOG 

CREATE TABLE public.audit_log (
    id BIGSERIAL PRIMARY KEY,
    backtest_id UUID NOT NULL REFERENCES public.backtests(id),
    event TEXT NOT NULL,                
    payload JSONB,
    hash TEXT NOT NULL,                  -- SHA-256(prev_hash + payload)
    prev_hash TEXT,                      -- chain link
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prevent updates/deletes on audit log
CREATE RULE no_update_audit AS ON UPDATE TO public.audit_log DO INSTEAD NOTHING;
CREATE RULE no_delete_audit AS ON DELETE TO public.audit_log DO INSTEAD NOTHING;


-- OHLCV CACHE (avoid re-fetching same data)
CREATE TABLE public.ohlcv_cache (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL DEFAULT 'NSE',
    date DATE NOT NULL,
    open NUMERIC NOT NULL,
    high NUMERIC NOT NULL,
    low NUMERIC NOT NULL,
    close NUMERIC NOT NULL,
    volume BIGINT NOT NULL,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(symbol, exchange, date)
);

CREATE INDEX idx_ohlcv_symbol_date ON public.ohlcv_cache(symbol, exchange, date);


-- ROW LEVEL SECURITY

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.backtests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ohlcv_cache ENABLE ROW LEVEL SECURITY;

-- Profiles: users see only their own
CREATE POLICY "users_own_profile" ON public.profiles
    FOR ALL USING (auth.uid() = id);

-- Strategies: own + public
CREATE POLICY "users_own_strategies" ON public.strategies
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "public_strategies_readable" ON public.strategies
    FOR SELECT USING (is_public = TRUE);

-- Backtests: own only
CREATE POLICY "users_own_backtests" ON public.backtests
    FOR ALL USING (auth.uid() = user_id);

-- Audit log: readable by backtest owner
CREATE POLICY "audit_readable_by_owner" ON public.audit_log
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.backtests b
            WHERE b.id = audit_log.backtest_id AND b.user_id = auth.uid()
        )
    );

-- OHLCV: readable by all authenticated users
CREATE POLICY "ohlcv_authenticated_read" ON public.ohlcv_cache
    FOR SELECT USING (auth.role() = 'authenticated');

-- Service role can write OHLCV (backend only)
CREATE POLICY "ohlcv_service_write" ON public.ohlcv_cache
    FOR INSERT WITH CHECK (auth.role() = 'service_role');
