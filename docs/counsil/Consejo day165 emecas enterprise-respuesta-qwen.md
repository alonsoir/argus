# Consejo de Sabios — Deliberación y Veredicto (DAY 165)
**Para:** Alonso Isidoro Román (PI, aRGus NDR)  
**De:** Consejo de Sabios — Arquitectura, Seguridad e Integración  
**Estado:** ✅ Deliberación cerrada. Veredicto unánime.

---

## Evaluación General
El trabajo de las FASES 0-4 es técnicamente sólido: la separación de modos (Community/Enterprise), el hot-reload RCU, la coordinación vía etcd y la extensión del wire header están alineados con los principios de sistemas NDR enterprise (cero downtime, rotación efímera, aislamiento criptográfico). La ausencia de un gate formal de validación enterprise es el único impedimento arquitectónico para el merge a `main`.

A continuación, el veredicto estructurado por pregunta.

---

### 🔹 Pregunta 1 — Arquitectura del protocolo
**Veredicto:** `(C) Targets anidados`  
**Fundamento:**
- `make emecas` mantiene la estabilidad del gate OSS existente (sin breaking changes).
- `make emecas++` encapsula explícitamente la extensión enterprise, permitiendo dependencias claras en el Makefile:
  ```makefile
  .PHONY: emecas++ emecas test-enterprise test-e2e-enterprise
  emecas++: emecas test-enterprise test-e2e-enterprise
  ```
- Un solo punto de entrada reduce drift de configuración, facilita la trazabilidad en CI futuro y refleja la jerarquía conceptual: OSS ⊂ Enterprise.  
  **Acción:** Implementar `emecas++` como target compuesto. Documentar en `CONTRIBUTING.md` la semántica de cada nivel.

---

### 🔹 Pregunta 2 — Vault dev como gate suficiente
**Veredicto:** ✅ **Suficiente para gate funcional**, con condición de resiliencia.  
**Fundamento:**
- Vault dev valida correctamente el flujo de provisionado efímero, tokenización, etcd watch y RCU hot-reload.
- No requiere segundo Vagrantfile con Vault server/file para merge a `main` (eso corresponde a validación pre-release/hardware).
- **Condición obligatoria:** Incluir un test de resiliencia básico: `stop vault → verify pipeline retries/token refresh → start vault → verify epoch continuity & zero drops`. Esto captura race conditions y manejo de estado que el modo `dev` no expone por diseño.  
  **Acción:** Añadir `test_vault_resilience_basic` a `test-enterprise`. Dejar `DEBT-VAULT-HA-001` como P1 para validación pre-release.

---

### 🔹 Pregunta 3 — Live epoch rotation en EMECAS
**Veredicto:** `(B) Live rotation con pipeline activo`  
**Fundamento:**
- `FakeEtcdServer` es determinista y rápido, pero no valida la cadena de integración real: latencia de red, ordenamiento de eventos, actualización atómica del `CryptoProviderHandle` via RCU, y sincronización firewall/pipeline.
- El overhead (~5 min) es aceptable y el valor de detección de bugs de integración justifica ampliamente el costo.
- Limitar a 2 ciclos de rotación en vivo es suficiente para el gate.  
  **Acción:** Integrar `test_live_epoch_rotation` en `test-e2e-enterprise`. Validar: `events_processed` continuo, `crypto_errors == 0`, `epoch_id` actualizado en wire header post-rotación.

---

### 🔹 Pregunta 4 — Test negativo (epoch_id incorrecto)
**Veredicto:** ⛔ **Requisito explícito del gate. No diferible.**  
**Fundamento:**
- En criptografía de transporte, el rechazo correcto de mensajes fuera de epoch es una propiedad de seguridad crítica (previene replay, downgrade y bypass de claves).
- Un pipeline que ignora o se bloquea ante `epoch_id` inválido introduce vectores de fallo operativos y de auditoría.  
  **Acción:** Implementar `test_epoch_rejection` como parte de `test-e2e-enterprise`. Validar: `crypto_errors += 1`, pipeline no crash, métricas/logs estructurados. Cerrar cualquier idea de diferirlo como deuda.

---

### 🔹 Pregunta 5 — Gate de Jenkins
**Veredicto:** ✅ **Merge aceptable con gate manual**, sujeto a condiciones.  
**Fundamento:**
- Bloquear una feature validada funcionalmente por infraestructura CI pendiente es anti-TDH.
- El protocolo `make emecas++` es 100% reproducible y determinista en entorno limpio.
- Jenkins debe seguir como `BACKLOG-CI-ENTERPRISE-001 (P1)`, con SLA explícito y responsable asignado.  
  **Condiciones:**
1. Script de gate documentado paso a paso.
2. Ejecución manual registrada en `VALIDATION_LOGS/EMECAS++_DAY165.md`.
3. Jenkins integrado antes del próximo release candidate.  
   **Acción:** Autorizar merge tras validación manual exitosa. Actualizar backlog con hito CI.

---

### 🔹 Pregunta 6 — Naming y documentación
**Veredicto:** `(B) EMECAS++`  
**Fundamento:**
- Mantiene continuidad con el uso informal ya extendido en el equipo.
- Notación académica y de ingeniería reconocible (`++` = extensión/superset).
- Permite definición formal en paper arXiv:
  > *EMECAS (base): validación OSS community.*  
  > *EMECAS++ (enterprise): EMECAS ⊕ crypto efímero ⊕ Vault ⊕ epoch coordination ⊕ live rotation.*
- `TDH-Gate` es abstracto y pierde trazabilidad con la base comunitaria. `EMECAS-E` introduce ambigüedad semántica.  
  **Acción:** Formalizar `EMECAS++` en `README.md`, `docs/VALIDATION_PROTOCOL.md`, y actualizar preprint arXiv `2604.04952` con la nomenclatura y diagrama de flujo.

---

## 📜 Checklist de Merge (Condiciones del Consejo)
| Ítem | Estado | Responsable |
|------|--------|-------------|
| `make emecas++` implementado (target anidado) | ⬜ Pendiente | Dev Lead |
| `test_live_epoch_rotation` integrado (2 ciclos) | ⬜ Pendiente | Crypto Team |
| `test_epoch_rejection` incluido en gate | ⬜ Pendiente | Security QA |
| `test_vault_resilience_basic` añadido | ⬜ Pendiente | Infra Team |
| Documentación EMECAS++ actualizada (README + arXiv) | ⬜ Pendiente | Tech Writer / PI |
| Ejecución manual registrada + log firmado | ⬜ Pendiente | Alonso / QA |
| `BACKLOG-CI-ENTERPRISE-001` marcado P1 con SLA | ⬜ Pendiente | CI Lead |

✅ **Una vez cumplidos los 7 puntos, el Consejo autoriza el merge a `main`.**

---

## 🗣️ Cierre
El diseño de EMECAS++ cierra la brecha de validación enterprise sin comprometer la agilidad del ciclo de desarrollo. Las recomendaciones priorizan seguridad criptográfica, trazabilidad y mantenibilidad a largo plazo, alineadas con la filosofía TDH y los estándares de sistemas NDR de misión crítica.

**El Consejo queda a disposición para revisión de artefactos pre-merge.**  
*Firmado: Consejo de Sabios — Arquitectura, Seguridad e Integración*  
*Fecha: 26 de Mayo 2026*