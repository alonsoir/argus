# DEBT-ODR-CI-GATE-001 — Gate CI para ODR Verification con LTO

**Estado:** BACKLOG
**Prioridad:** P1 — pre-FEDER
**Bloqueado por:** servidor CI/CD disponible (FEDER hardware)
**Estimación:** 1 sesión
**Fecha de registro:** 2026-05-03 (DAY 140)

## Descripción

El build diario usa `PROFILE=debug` (sin LTO) — no detecta ODR violations.
La verificación ODR requiere `PROFILE=production` (con `-flto`).

El gap actual permite que una ODR violation introducida hoy no se detecte
hasta el próximo build production manual. En infraestructura crítica esto
es inaceptable (Consejo 8/8 unánime DAY 140).

## Implementación

### Gate pre-merge (Jenkinsfile)

```groovy
stage('ODR Verification') {
    when { changeRequest() }  // En PRs
    steps {
        sh 'make PROFILE=production all'
        sh 'make test-all'
    }
}
```

### Nightly (Jenkinsfile)

```groovy
triggers { cron('0 3 * * 0') }  // Domingo 3AM
stage('Nightly ODR Check') {
    steps {
        sh 'make PROFILE=production all'
        sh 'make test-all'
    }
}
```

### Target Makefile (disponible ahora)

```makefile
check-odr:
    @echo "ODR verification (PROFILE=production + LTO)..."
    $(MAKE) PROFILE=production all
    @echo "ODR check PASSED"
```

## Hardware requerido

El servidor CI/CD es el mismo hardware del FEDER (BACKLOG-BENCHMARK-CAPACITY-001).
Mientras no esté disponible: ejecutar manualmente `make PROFILE=production all`
antes de cada merge a main.

## Test de cierre

`make check-odr` verde en el servidor CI/CD sin intervención manual.

## Referencias

- Consejo DAY 140 (8/8 unánime): gap inaceptable para infraestructura crítica
- BACKLOG-FEDER-001 — el servidor es prerequisito
- DEBT-EMECAS-AUTOMATION-001 — automatización EMECAS relacionada
