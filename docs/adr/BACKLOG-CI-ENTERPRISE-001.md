# BACKLOG-CI-ENTERPRISE-001 — Jenkins gate `make emecas++`

**Prioridad:** P1 post-merge  
**Creado:** DAY 166

## Descripción

Integrar `make emecas++` como gate obligatorio en el pipeline Jenkins de aRGus NDR.

## Canal de notificación DAY 166 (B3 implementado)

`vault-fault-inject` emite una línea JSON estructurada parseable por Jenkins:

```json
{"event":"vault_fault_inject","status":"passed","acto":"III",
 "component":"etcd-server","vault_fault":"token_revoked",
 "result":"autonomous_cache_rcu"}
```

Jenkins puede detectar pass/fail con exit code (ya funciona) y parsear
el JSON con `jq` para métricas adicionales.

## Trabajo pendiente

- [ ] Añadir stage `emecas++` en `Jenkinsfile.dev`
- [ ] Añadir `make vault-dev-start` como prerequisito del stage
- [ ] Parsear JSON de `vault-fault-inject` con `jq` y publicar métricas
- [ ] Vault HA (RPi5/N100) — sustituir Vault dev por Vault prod (ADR-049)

## Dependencias

- Hardware lab: RPi5x2 + N100 miniPCx2 (FEDER septiembre 2026)
- ADR-049 Vault HA Raft autounseal
