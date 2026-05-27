# DEBT-SYSTEMD-001 — Notas de producción systemd units
# Redactado: DAY 115, domingo 12 abril 2026, ~06:00
# Contexto: units creados en Vagrant/debug. Cuando lleguen las Raspberry Pi
# (estimado: 1-2 meses), leer esto ANTES de tocar nada.

---

## DEBT-RAG-BUILD-001 — rag/build no sigue convención build-debug/build-release

**Componente:** rag-security  
**Problema:** Los otros 5 componentes usan `build-debug/` y `build-release/`.
`rag` solo tiene `build/`. El script `set-build-profile.sh` lo excluye.  
**Impacto actual:** `ml-defender-rag-security.service` usa `/vagrant/rag/build/` hardcodeado.  
**Fix real:** Modificar `rag/CMakeLists.txt` para respetar `CMAKE_BUILD_TYPE` y
producir `build-debug/` o `build-release/` según el perfil. Luego eliminar la
excepción en `set-build-profile.sh`.  
**Prioridad:** Antes de despliegue en Raspberry Pi.

---

## Notas críticas para despliegue en producción (Raspberry Pi / Debian 13)

### 1. Paths: de /vagrant a /usr o /opt

En Vagrant todo está en `/vagrant/`. En Debian empaquetado los binarios
irán a otro lugar. Antes de desplegar en RPi, decidir y documentar:

```
Opción A (recomendada para paquetes .deb):
  Binarios:  /usr/bin/ml-defender-{component}
  Config:    /etc/ml-defender/{component}.json
  Libs:      /usr/lib/ml-defender/
  Plugins:   /usr/lib/ml-defender/plugins/
  Logs:      /var/log/ml-defender/
  Datos:     /var/lib/ml-defender/

Opción B (instalación manual, más rápida para primeras RPis):
  Todo en:   /opt/ml-defender/{component}/
  Symlinks:  /usr/bin/ml-defender-{component} → /opt/...
```

**Acción pendiente:** Decidir Opción A o B antes de crear paquetes .deb.
Impacta todos los units, provision.sh, y los JSON de configuración.

### 2. set-build-profile.sh en producción

En RPi con paquetes .deb, `build-active` no tiene sentido — los binarios
ya están compilados para ARM64. El script `set-build-profile.sh` **no se
usa en producción**. Los units en producción referencian directamente los
binarios instalados (sin symlinks de build).

**Acción pendiente:** Crear variante de los units para producción con paths
absolutos reales. Sugerencia: directorio `etcd-server/config/production/`
con los 6 units de producción separados de los de desarrollo.

### 3. LD_LIBRARY_PATH en producción

En Vagrant: `LD_LIBRARY_PATH=/usr/local/lib` (libsodium compilada desde fuente).  
En Debian 13 ARM64: libsodium 1.0.19 debe estar disponible como paquete del
sistema o compilada e instalada en `/usr/local/lib`. Verificar antes:

```bash
# En la RPi:
ldconfig -p | grep libsodium
# Si no aparece 1.0.19, compilar desde fuente igual que en Vagrant:
# (ver provision.sh — sección libsodium)
```

### 4. Capabilities eBPF en Raspberry Pi OS / Debian 13 ARM64

`CAP_BPF` requiere kernel ≥ 5.8. Raspberry Pi 4/5 con kernel actual (6.x) ✅.  
Verificar antes:

```bash
uname -r  # debe ser >= 5.8
# Y que CONFIG_BPF=y en el kernel:
zcat /proc/config.gz | grep CONFIG_BPF
```

### 5. Usuario dedicado ml-defender

En Vagrant: todo corre como root (aceptable para desarrollo).  
En producción RPi: **crear usuario dedicado `ml-defender`** sin shell:

```bash
useradd --system --no-create-home --shell /usr/sbin/nologin ml-defender
```

Excepciones que DEBEN seguir siendo root:
- `ml-defender-sniffer` (CAP_BPF, CAP_SYS_ADMIN para eBPF/XDP)
- `ml-defender-firewall-acl-agent` (CAP_NET_ADMIN para iptables)

Los otros 4 (etcd-server, rag-security, rag-ingester, ml-detector) pueden
correr como `ml-defender` con permisos apropiados en sus directorios.

### 6. WorkingDirectory en producción

Los units actuales usan `WorkingDirectory=/vagrant/{component}/build-active`.
En producción cambiar a la ruta del binario instalado. Si se usa Opción A:

```ini
WorkingDirectory=/var/lib/ml-defender/{component}
```

### 7. provision.sh --reset (DEBT-ADR025-D11, deadline 18 Apr)

`provision.sh --reset` debe funcionar correctamente antes de despliegue en RPi.
Esto incluye regenerar seed.bin, keypairs Ed25519, y (cuando ADR-024 esté
implementado) keypairs X25519 para Noise_IKpsk3.

### 8. Plugin paths en producción

En Vagrant: `/usr/lib/ml-defender/plugins/` (ya correcto).  
En RPi Debian: mismo path — no cambia. ✅  
Verificar que los JSON de config referencian este path absoluto (no relativo).

### 9. Logs en producción

En Vagrant: `/vagrant/logs/lab/`.  
En RPi: `StandardOutput=journal` en los units (ya configurado ✅).  
Acceso: `journalctl -u ml-defender-sniffer -f`  
Para logs persistentes añadir a `/etc/systemd/journald.conf`:
```ini
Storage=persistent
```

### 10. Checklist pre-despliegue RPi (cuando lleguen)

```
[ ] Debian 13 ARM64 instalado, kernel >= 5.8
[ ] libsodium 1.0.19 compilada e instalada
[ ] usuario ml-defender creado
[ ] Decidir Opción A o B para paths
[ ] Compilar todos los componentes con PROFILE=release para ARM64
[ ] DEBT-RAG-BUILD-001 resuelto (rag/CMakeLists.txt)
[ ] provision.sh --reset funciona (DEBT-ADR025-D11)
[ ] Crear units de producción (paths /usr o /opt, no /vagrant)
[ ] Plugin .so + .sig firmados con clave de producción (ADR-032 Fase B: YubiKey)
[ ] allowed_static_keys en deployment.yml (OQ-5, cuando ADR-024 implementado)
[ ] Benchmark Noise handshake < 50ms en ARMv8 (OQ-8, R10)
[ ] TEST-PROVISION-1 (CI gate) validado
[ ] AppArmor profiles instalados (PHASE 3 ítem 5)
[ ] nftables rate-limiting configurado (OQ-7 mitigación)
[ ] make plugin-integ-test: 12/12 PASSED en hardware real
```

---

*Redactado: DAY 115, 2026-04-12 — feature/phase3-hardening*  
*No perder esto. Costó una mañana de domingo construirlo.*