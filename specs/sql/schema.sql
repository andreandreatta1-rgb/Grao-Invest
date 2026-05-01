CREATE TABLE IF NOT EXISTS tenants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  mfa_secret TEXT,
  mfa_enabled INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE TABLE IF NOT EXISTS login_attempt_states (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  failed_attempts INTEGER NOT NULL DEFAULT 0,
  lock_level INTEGER NOT NULL DEFAULT 0,
  locked_until TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  accepted_terms INTEGER NOT NULL,
  accepted_privacy INTEGER NOT NULL,
  consented_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS suitability_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  investor_profile TEXT NOT NULL,
  time_horizon TEXT NOT NULL,
  risk_tolerance TEXT NOT NULL,
  liquidity_need TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS market_ticks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  instrument TEXT NOT NULL,
  provider TEXT NOT NULL,
  event_time TEXT NOT NULL,
  ingest_time TEXT NOT NULL,
  price REAL NOT NULL,
  volume INTEGER NOT NULL,
  currency TEXT NOT NULL,
  source_payload_id TEXT
);

CREATE TABLE IF NOT EXISTS market_provider_states (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider_name TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL,
  status TEXT NOT NULL,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  last_event_time TEXT NOT NULL,
  failover_threshold INTEGER NOT NULL DEFAULT 3,
  is_active INTEGER NOT NULL DEFAULT 0,
  details TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS indicator_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  instrument TEXT NOT NULL,
  reference_time TEXT NOT NULL,
  availability_time TEXT NOT NULL,
  sma_5 REAL NOT NULL,
  sma_10 REAL NOT NULL,
  sma_20 REAL NOT NULL DEFAULT 0.0,
  ema_5 REAL NOT NULL,
  ema_12 REAL NOT NULL DEFAULT 0.0,
  ema_26 REAL NOT NULL DEFAULT 0.0,
  rsi_14 REAL NOT NULL,
  volatility_10 REAL NOT NULL DEFAULT 0.0,
  momentum_5 REAL NOT NULL DEFAULT 0.0,
  macd REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  instrument TEXT NOT NULL,
  reference_time TEXT NOT NULL,
  availability_time TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT NOT NULL,
  anti_hype_score REAL NOT NULL DEFAULT 100.0,
  xai_payload TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS paper_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  signal_id INTEGER NOT NULL,
  instrument TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  reference_price REAL NOT NULL,
  execution_price REAL NOT NULL,
  gross_amount REAL NOT NULL,
  estimated_cost REAL NOT NULL,
  estimated_tax REAL NOT NULL,
  risk_status TEXT NOT NULL DEFAULT 'accepted',
  risk_notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (signal_id) REFERENCES signals(id)
);

CREATE TABLE IF NOT EXISTS portfolio_positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  instrument TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  average_price REAL NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(user_id, instrument),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  event_type TEXT NOT NULL,
  details TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  instrument TEXT NOT NULL,
  headline TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  credibility_score REAL NOT NULL,
  anti_hype_score REAL NOT NULL,
  published_at TEXT NOT NULL,
  captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_analysis_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  news_article_id INTEGER NOT NULL,
  instrument TEXT NOT NULL,
  sector TEXT NOT NULL,
  theme TEXT NOT NULL,
  sentiment_label TEXT NOT NULL,
  sentiment_score REAL NOT NULL,
  magnitude_score REAL NOT NULL,
  model_confidence REAL NOT NULL,
  source_url TEXT,
  language TEXT NOT NULL DEFAULT 'pt-BR',
  availability_time TEXT NOT NULL,
  FOREIGN KEY (news_article_id) REFERENCES news_articles(id)
);

CREATE TABLE IF NOT EXISTS fundamental_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  instrument TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_type TEXT NOT NULL,
  reference_time TEXT NOT NULL,
  availability_time TEXT NOT NULL,
  pe_ratio REAL NOT NULL,
  pb_ratio REAL NOT NULL,
  ev_ebitda REAL NOT NULL,
  dividend_yield REAL NOT NULL,
  roe REAL NOT NULL,
  net_margin REAL NOT NULL,
  revenue_growth REAL NOT NULL,
  payout_ratio REAL NOT NULL,
  version_tag TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS circuit_breaker_states (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  instrument TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  reason TEXT NOT NULL,
  triggered_at TEXT NOT NULL,
  released_at TEXT
);

CREATE TABLE IF NOT EXISTS risk_decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  signal_id INTEGER NOT NULL,
  instrument TEXT NOT NULL,
  decision TEXT NOT NULL,
  notes TEXT NOT NULL,
  decided_at TEXT NOT NULL,
  portfolio_exposure REAL NOT NULL DEFAULT 0.0,
  projected_exposure REAL NOT NULL DEFAULT 0.0,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (signal_id) REFERENCES signals(id)
);

CREATE TABLE IF NOT EXISTS kill_switch_states (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope_type TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  status TEXT NOT NULL,
  reason TEXT NOT NULL,
  triggered_at TEXT NOT NULL,
  released_at TEXT
);

CREATE TABLE IF NOT EXISTS backtest_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  instrument TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT NOT NULL,
  trade_count INTEGER NOT NULL,
  accepted_trade_count INTEGER NOT NULL,
  rejected_trade_count INTEGER NOT NULL,
  win_rate REAL NOT NULL,
  total_return_pct REAL NOT NULL,
  max_drawdown_pct REAL NOT NULL,
  summary TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS backtest_trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  instrument TEXT NOT NULL,
  signal_time TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  confidence REAL NOT NULL,
  anti_hype_score REAL NOT NULL,
  entry_price REAL NOT NULL,
  exit_price REAL NOT NULL,
  pnl_pct REAL NOT NULL,
  risk_decision TEXT NOT NULL,
  rationale TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES backtest_runs(id)
);

CREATE TABLE IF NOT EXISTS alert_rules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  rule_type TEXT NOT NULL,
  instrument TEXT,
  threshold_value REAL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS alert_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  alert_rule_id INTEGER,
  event_type TEXT NOT NULL,
  instrument TEXT,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (alert_rule_id) REFERENCES alert_rules(id)
);
