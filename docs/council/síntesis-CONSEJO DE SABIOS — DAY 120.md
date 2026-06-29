## 🔬 INVESTIGACIÓN — ADR-038 Federated Learning (largo plazo)

**Estado:** BORRADOR ITERATIVO — No implementar hasta ADR-026 mergeado + I+D completado
**Potencial:** Sistema inmune distribuido global para infraestructura crítica
**Prioridad:** BAJA ahora — ALTA cuando los cimientos estén listos

### Consenso Consejo DAY 120 (7/7 unánime)

**Aprobado como visión. Bloqueado como implementación.**

Correcciones no negociables antes de abrir feature branch:

| ID | Corrección | Estado |
|----|-----------|--------|
| DEBT-FED-001 | Agregación XGBoost: NO FedAvg. V1 = Federated Model Selection (mejor modelo validado → redistribuye). SecureBoost → V2. | ⏳ I+D |
| DEBT-FED-002 | Distribución: NO BitTorrent. Push central firmado + PKI jerárquica (step-ca). Kimi propone libp2p como alternativa. | ⏳ I+D |
| DEBT-FED-003 | Identidad: PKI jerárquica Nivel 0/1/2 (nodo → CCN-CERT → central multi-firma). NO Web-of-Trust. | ⏳ I+D |
| DEBT-FED-004 | ε-DP calibrado: ε≤0.1 features, ε≤1.0 contadores. DPIA obligatoria. Experto externo requerido. | ⏳ I+D |
| DEBT-FED-005 | Scheduler: cgroups v2 + systemd.slice + hook ml-detector. NO solo CPU/RAM. | ⏳ diseño |
| DEBT-FED-006 | Metadatos también re-identifican. k-anonimidad ≥5 + delay 7 días antes de publicar. | ⏳ I+D |

### Arquitectura V1 acordada
ml-trainer (nuevo componente — último en el pipeline)
← CSVs de ml-detector + firewall-acl-agent
→ anonimiza (DP calibrada + k-anon)
→ entrena XGBoost warm-start local
→ mide F1/Precision en holdout local
→ empaqueta modelo + metadatos + dataset anon
→ firma Ed25519 nodo emisor + cifra ChaCha20
→ push a nodo central aRGus (PKI jerárquica)
→ validación gates G1-G6 (+ G6: backdoor detection)
→ Federated Model Registry: rankea por F1+KL_penalty
→ redistribuye top-1 a la red
→ metadatos van SIEMPRE aunque modelo falle

### Secuenciación acordada

feature/adr026-xgboost MERGED          ← prerequisito
↓
ADR-029 variantes hardened             ← AppArmor + seL4
↓
RESEARCH-FEDERATED-001 (3-6 meses I+D)
├─ SecureBoost / Federated Model Selection literatura
├─ ε-DP calibración con experto privacidad
├─ PoC PKI step-ca o libp2p
├─ Modelo federación confianza Nivel 0/1/2
└─ DPIA pre-piloto
↓
ADR-038 v2 (post I+D) → revisión Consejo
↓
Piloto controlado: 1 hospital + 1 nodo central
↓
Evaluación 6 meses
↓
Producción: 2027

### seL4 → ADR-039 (investigación separada)

La variante seL4 para ml-trainer es el "Santo Grial" (Gemini): entrenamiento en partición formalmente verificada, imposible de comprometer desde otros procesos. No bloquea V1 en Debian. ADR-039 abre cuando ADR-038 V1 esté validado.

### Por qué importa

Un ransomware que golpea Pekín hoy deja metadatos en la red aRGus. Badajoz los recibe antes de que el ataque llegue. La red entera se inmuniza con cada incidente en cualquier punto del planeta. Esto no existe hoy para infraestructura crítica de bajo presupuesto.

*"La inteligencia distribuida sin gobernanza central es caos. La gobernanza sin aprendizaje es obsolescencia."* — DeepSeek, DAY 120

MDEOF
echo "✅ ADR-038 añadido al BACKLOG"