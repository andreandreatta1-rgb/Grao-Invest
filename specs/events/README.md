# Event Specs

Coloque aqui os contratos canonicos de eventos do barramento.

## Prioridades iniciais
- `market_tick`
- `fundamental_snapshot`
- `market_candle`
- `signal_generated`
- `paper_order_submitted`
- `paper_order_filled`
- `risk_decision`
- `tax_cost_applied`
- `audit_event`

## Convencoes
- Prefira Protobuf ou Avro e versione os eventos
- Cada evento deve carregar metadados de origem e tempo
- Eventos historicos ou corrigidos devem ser versionados, nao sobrescritos
