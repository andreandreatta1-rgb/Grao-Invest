# Runbook: Release Readiness

## Gate minimo
- Testes automatizados verdes
- Cobertura minima atingida nos modulos alterados
- Lint, formatacao e typecheck sem erros
- Contract tests verdes para contratos afetados
- Verificacao da politica anti-recomendacao verde
- Teste de leakage point-in-time verde
- Revisao de seguranca e compliance quando houver impacto

## Checklist operacional
- Confirmar versoes de specs e ADRs referenciadas no release
- Validar migracoes e rollback
- Confirmar dashboards e alertas
- Confirmar changelog e release notes
- Registrar risco residual conhecido

## Criticos para este produto
- Nenhum texto proibido em UIs e narrativas
- Nenhum acesso a dados historicos sem `as_of`
- Nenhuma integracao de execucao real habilitada na Fase 1
- Falhas sustentadas do provedor primario devem gerar failover auditavel antes de qualquer release operacional
- Snapshots fundamentalistas precisam manter `reference_time`, `availability_time` e `version_tag` auditaveis
- Noticias enriquecidas devem armazenar apenas metadado, link e classificacao, sem redistribuir corpo protegido por copyright
