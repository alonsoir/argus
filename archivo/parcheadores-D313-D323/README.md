# Parcheadores DAY313-DAY323 (archivo)

Scripts de un solo uso que aplicaron los cambios de los PR del plano de control
(DEBT-ETCD-HA-TLS-RAFT-001, PR1 `feat/etcd-mtls-vault`, PR #153) y de la
documentación de esos días. Nunca estuvieron en `main`: sus efectos sí, en los
commits que cita cada uno.

Se guardan aquí, en una rama de archivo que no se mergea, solo como material de
investigación (cómo se llegó a cada cambio). No se ejecutan: el código vigente
está en `main`, y volver a lanzarlos sobre `main` de hoy no tiene sentido.

Estructura: la misma ruta que tenían en el repo, bajo
`archivo/parcheadores-D313-D323/` (`scripts/…` y `scripts/etcd_ha/…`).

Consultar sin cambiar de rama:

    git fetch origin archivo/parcheadores-d313-d323
    git ls-tree -r --name-only origin/archivo/parcheadores-d313-d323 -- archivo/
    git show origin/archivo/parcheadores-d313-d323:archivo/parcheadores-D313-D323/scripts/etcd_ha/d323_mitre_ventana.py

Archivado el DAY324 (12-nov-2026).
