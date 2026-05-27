# Recovery Contract — Rotación de Claves (OQ-6 ADR-024)

**Estado:** PHASE 3 (single-node, reinicio controlado)
**Última actualización:** DAY 117 — 14 Abril 2026
**Próxima revisión:** FASE 4 (hot-reload sin downtime)

---

## Cuándo ejecutar este procedimiento

- Seed con antigüedad > 30 días (el RAG alertará al admin)
- Compromiso de claves detectado o sospechado
- Rotación planificada por política de seguridad
- Post-incidente de seguridad

---

## Procedimiento (downtime estimado: ~30 segundos)

**Paso 1 — Parar el pipeline**
```bash
make pipeline-stop
```

**Paso 2 — Rotar todas las claves**
```bash
echo 'RESET' | sudo bash tools/provision.sh --reset
```
→ Genera nuevas keypairs Ed25519 + seed_family compartido para los 6 componentes
→ Backup automático de claves anteriores (máx. 2 por componente)
→ Nueva pubkey MLD_PLUGIN_PUBKEY_HEX registrada en logs

**Paso 3 — Re-firmar plugins**
```bash
make sign-plugins
```

**Paso 4 — Arrancar y verificar**
```bash
make pipeline-start
make test-all
```
→ Criterio de éxito: 6/6 RUNNING + test-all verde

**Paso 5 — Registrar la rotación**
Anotar en el log de operaciones (o commit de git):
- Fecha y hora
- Motivo de la rotación
- Nueva pubkey MLD_PLUGIN_PUBKEY_HEX
- Resultado de make test-all

---

## Invariantes post-rotación

- INVARIANTE-SEED-001: `make test-invariant-seed` PASSED
- 6/6 componentes con seed idéntico
- Todos los plugins firmados con la nueva clave

---

## Problemas conocidos / lecciones aprendidas

| Problema | Causa | Solución |
|---|---|---|
| HKDF MAC fail post-reset | Seeds independientes por componente | INVARIANTE-SEED-001: seed_family compartido (DAY 116) |
| Pipeline fail-closed tras reset | Plugins firmados con clave antigua | Siempre ejecutar `make sign-plugins` tras `--reset` |
| Binarios no recompilados | libplugin_loader.so cambiado | `make pipeline-build` si hay cambios en libs (DAY 114) |

---

---

## Lección aprendida DAY 117 — pubkey hardcoded tras reset

**Problema:** Tras ejecutar `provision.sh --reset` múltiples veces (test de backup
policy), la keypair de firma de plugins rotó. Los binarios tenían la pubkey anterior
hardcoded en `plugin-loader/CMakeLists.txt` → `TEST-INTEG-SIGN FAILED`.

**Síntoma:**
[plugin-loader] CRITICAL: Ed25519 INVALID for 'test-message'
terminate called without an active exception
TEST-INTEG-SIGN FAILED

**Causa raíz:** `MLD_PLUGIN_PUBKEY_HEX` en `plugin-loader/CMakeLists.txt` es un
valor hardcoded en tiempo de compilación (ADR-025 D7). Cada `--reset` rota la
keypair en `/etc/ml-defender/plugins/` pero NO recompila los binarios.

**Solución:**
```bash
# 1. Obtener nueva pubkey
vagrant ssh -c "sudo python3 -c \"
import subprocess, base64
pem = subprocess.run(['cat', '/etc/ml-defender/plugins/plugin_signing.pk'],
    capture_output=True).stdout
raw = base64.b64decode(''.join(pem.decode().strip().split('\n')[1:-1]))
print(raw[-32:].hex())
\""

# 2. Actualizar plugin-loader/CMakeLists.txt con nueva pubkey
# 3. Recompilar
make pipeline-build
# 4. Re-firmar plugins
make sign-plugins
# 5. Verificar
make plugin-integ-test
```

**Regla de oro:** `provision.sh --reset` → siempre `make pipeline-build` +
`make sign-plugins` + `make test-all`.

**Pubkey activa post-reset DAY 117:**
`e51a91e91d72f74fe97e8a4eb883c9c6eb41dd2fc994feaf59d5ba2177720f3d`

## Roadmap

- **PHASE 3 (actual):** Rotación con reinicio controlado. ~30s downtime.
- **FASE 4 (futuro):** Hot-reload sin downtime. Ventana de solapamiento dual-key.
  Coordinación vía RAG subsystem. Ver ENT-4 en backlog.

