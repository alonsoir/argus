Aquí mis respuestas como miembro del Consejo:

---

**P1 — Zombies por fork() sin wait()**

Sí, acumulamos zombies en ataques persistentes. El fix correcto es añadir un `SIGCHLD` handler con `waitpid(-1, WNOHANG)` en `BatchProcessor` al inicializarse:

```cpp
signal(SIGCHLD, [](int){ while(waitpid(-1, nullptr, WNOHANG) > 0); });
```

Una línea. Sin threads adicionales, sin complejidad. Registrar como `DEBT-IRP-SIGCHLD-001` P1 — no bloqueante para FEDER pero sí para producción hospitalaria.

---

**P2 — float vs double para threshold**

Cambiar `threat_score_threshold` a `float` en `IsolateConfig`. Tipos consistentes eliminan el problema de raíz — sin tolerancias, sin comentarios explicativos, sin sorpresas. El JSON admite ambos sin cambio de formato. La tolerancia `1e-6` actual es un parche correcto pero evitable. Registrar como fix menor pre-merge.

---

**P3 — auto_isolate: true por defecto**

Mantener `true` pero añadir un gate de onboarding: si `whitelist_ips` está vacía o contiene solo los defaults de Vagrant, loguear un `WARNING` prominente al arrancar `firewall-acl-agent` indicando que el IRP está activo sin whitelist personalizada. No bloquear — informar. La responsabilidad del administrador es leer los warnings. En hospitales, la configuración de `whitelist_ips` con los activos críticos debe ser parte del checklist de instalación, no del default.

---

**P4 — /tmp glob demasiado permisivo**

Mover a `/var/lib/argus/irp/` con permisos `0700 argus:argus`. Actualizar `IsolateConfig` con `backup_dir: /var/lib/argus/irp` por defecto, crear el directorio en `provision.sh`, y actualizar el AppArmor profile. El glob en `/tmp` es un vector real: cualquier proceso que pueda crear `/tmp/argus-backup-*.nft` puede interferir con el rollback. Registrar como `DEBT-IRP-BACKUP-DIR-001` P1 pre-producción.

---

**P5 — ¿Dos señales AND son suficientes?**

Para FEDER: sí, suficiente. Para producción hospitalaria: no. La arquitectura que recomiendo es una **matriz de decisión con pesos**:

```
señal_1: score >= 0.95           (peso: necesaria, no suficiente)
señal_2: event_type IN lista     (peso: necesaria, no suficiente)
señal_3: src_ip NOT IN whitelist_assets_criticos  (peso: gate de seguridad)
señal_4: confirmación segundo sensor en ±5s      (peso: deseable, no obligatoria)
```

Las señales 1+2+3 son el mínimo aceptable en hospital. La señal 4 (correlación temporal con segundo sensor) es la diferencia entre un NDR de laboratorio y uno que puede desplegarse en un quirófano. Esto es exactamente `DEBT-IRP-MULTI-SIGNAL-001` — diseñar la matriz de decisión cuando tengamos datos reales de MITRE.

---

Las cinco en resumen: **SIGCHLD handler** (deuda P1), **float threshold** (fix pre-merge), **warning sin whitelist** (UX), **backup dir fijo** (deuda P1), **tercera señal whitelist_assets_criticos** (deuda post-FEDER obligatoria para hospital real).