# Dominio: Ingestao de Mercado

## Missao
Receber, normalizar, validar, versionar e distribuir dados de mercado B3 para os demais dominios sem perder semantica temporal.

## Entradas
- Ticks e candles intraday
- Historico diario
- Eventos de ajuste corporativo e calendarios de mercado
- Metadados de instrumentos

## Saidas
- Eventos canonicos de mercado em `specs/events/`
- Dados persistidos com versionamento temporal
- Indicadores operacionais de qualidade e latencia

## Regras invariantes
- Nenhum dado historico pode ser sobrescrito.
- Todo evento deve incluir origem, horario do evento, horario de captura e identificador do instrumento.
- Fallback para provedor secundario deve ser auditavel.
- Qualquer transformacao deve preservar campo suficiente para reconstrucao forense.

## Riscos principais
- Drift de schema do provedor
- Duplicidade de ticks
- Furos temporais e atrasos
- Ajustes corporativos aplicados fora de tempo
