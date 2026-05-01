# SQL Specs

Coloque aqui DDL versionado e modelos fisicos aprovados.

## Regras
- Toda tabela temporal deve explicitar colunas de referencia e disponibilidade quando aplicavel
- Dados multiusuario precisam carregar chaves de tenant
- Fatos de mercado, noticias e auditoria devem ser append-only por padrao
