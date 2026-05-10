cat > /tmp/ADR-038-federated-learning.md << 'MDEOF'
# ADR-038 — Federated Learning Distribuido para aRGus NDR

**Estado:** BORRADOR — DAY 120  
**Autor:** Alonso Isidoro Román  
**Revisores:** Consejo de Sabios (pendiente)  
**Fecha:** 17 Abril 2026  
**Branch:** investigación — no implementar hasta merge feature/adr026-xgboost

---

## Contexto

aRGus NDR protege infraestructura crítica de bajo presupuesto (hospitales, municipios, escuelas) en entornos donde los datasets académicos no representan el tráfico real local. Un hospital en Extremadura tiene patrones de tráfico únicos — sus propios dispositivos médicos, sus propios horarios, sus propios vectores de ataque.

El problema central: **el conocimiento sobre ataques reales está distribuido y es privado**. Cuando un ransomware golpea un hospital en Pekín, los hospitales de Badajoz no se enteran hasta que les golpea a ellos. Las soluciones comerciales federadas cuestan millones. No existen para infraestructura crítica de bajo presupuesto.

Esta ADR propone un **sistema inmune distribuido**: cada nodo aRGus aprende de su entorno local, contribuye ese aprendizaje de forma anónima y verificada a la red, y la red entera se hace más resistente con cada ataque que ocurre en cualquier punto del planeta.

---

## Decisión

Crear un nuevo componente `ml-trainer` que implemente un ciclo de aprendizaje federado asíncrono, seguro y verificable, integrado en la arquitectura existente de aRGus NDR.

---

## Arquitectura del componente ml-trainer

┌─────────────────────────────────────────────────────────────────┐
│                    ml-trainer (nuevo componente)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  FASE 1 — Ingesta (asíncrona, bajo consumo)                     │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Consume CSVs de ml-detector + firewall-acl-agent         │   │
│  │ (mismo patrón que rag-ingester — file watcher)           │   │
│  │ Detecta ventana de baja actividad (CPU < 20%, scheduler) │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         ↓                                        │
│  FASE 2 — Anonimización                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Elimina IPs (reemplaza por hash con salt rotante)        │   │
│  │ Normaliza puertos a categorías (well-known/ephemeral)    │   │
│  │ Agrega temporalmente (ventanas 5min, no timestamps)      │   │
│  │ Privacidad diferencial: ruido calibrado (ε-differential) │   │
│  │ DPIA compliance: ningún dato re-identificable            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         ↓                                        │
│  FASE 3 — Entrenamiento local XGBoost                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Warm-start sobre modelo base actual                      │   │
│  │ Límite de árboles (poda automática si size > threshold)  │   │
│  │ Holdout local: F1 + Precision + FPR medidos              │   │
│  │ Si métricas < baseline → no distribuir modelo            │   │
│  │ Metadatos siempre viajan (valor estadístico federado)    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         ↓                                        │
│  FASE 4 — Empaquetado y distribución                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Paquete: modelo.ubj + dataset_anon.parquet + metadata    │   │
│  │ Firma Ed25519 del nodo emisor (keypair local)            │   │
│  │ Cifrado ChaCha20-Poly1305 con clave pública nodo central │   │
│  │ Compresión zstd                                          │   │
│  │ Entrega a cola cliente BitTorrent local                  │   │
│  │ (distribución asíncrona — no bloquea pipeline principal) │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
↓
┌─────────────────────────────────────────────────────────────────┐
│                    Nodos centrales aRGus                         │
├─────────────────────────────────────────────────────────────────┤
│  Recepción → verificación firma Ed25519 del nodo emisor          │
│  Validación gates G1-G5:                                         │
│    G1: Firma válida + certificado nodo en web-of-trust           │
│    G2: Métricas locales dentro de rango aceptable                │
│    G3: KL-divergence dataset vs distribución global < umbral     │
│    G4: Sandbox 24h con golden test suite                         │
│    G5: Human-in-the-loop para modelos con delta F1 > 0.01        │
│  Si pasa: agrega al modelo global + redistribuye a la red        │
│  Si falla: metadatos se incorporan al knowledge base federado    │
│  Rollback automático si F1 global cae > 2% post-actualización    │
└─────────────────────────────────────────────────────────────────┘
↓
Toda la red aRGus aprende

---

## Scheduler de entrenamiento — reglas críticas

El entrenamiento local ocurre SOLO si se cumplen TODAS las condiciones:

CPU_LOAD < 20% durante 10 minutos continuos
RAM_FREE > 512MB
NO_ALERTS_ACTIVE (ml-detector en estado normal)
HORA_LOCAL in ventana_configurada (ej: 02:00-05:00)
DIAS_DESDE_ULTIMO_ENTRENAMIENTO >= umbral_minimo (ej: 7 días)

En un hospital, la misión crítica siempre tiene prioridad. El scheduler cede CPU inmediatamente ante cualquier alerta del pipeline principal.

---

## Valor del modelo federado aunque falle

Un modelo local que no supera los gates de calidad no se distribuye, **pero sus metadatos sí**. Esos metadatos incluyen:

- Distribución estadística de features (sin datos raw)
- Tipos de tráfico dominantes en el período
- Anomalías detectadas y frecuencias
- Performance del modelo base en tráfico local

Esto permite a los nodos centrales:
- Detectar correlaciones globales entre incidentes
- Identificar si múltiples hospitales están viendo el mismo patrón
- Decidir si mezclar datasets de distintos nodos mejora un modelo global
- Alertar a la red ante patrones emergentes antes de que se conviertan en ataques masivos

**Un ransomware que golpea Pekín hoy deja metadatos en la red aRGus. Badajoz los recibe antes de que el ataque llegue.**

---

## Variantes de seguridad (sinergias con ADR-029)

| Variante | Seguridad modelo | Seguridad entrenamiento | Viabilidad |
|----------|-----------------|------------------------|------------|
| Debian + AppArmor + eBPF/XDP | Alta | ml-trainer bajo perfil AppArmor dedicado | DAY 121+ |
| Debian + AppArmor + libpcap | Alta | Igual | DAY 121+ |
| seL4 + libpcap | Máxima | Proceso ml-trainer en partición seL4 aislada | Investigación |

La variante seL4 es la más potente: el entrenamiento ocurre en una partición formalmente verificada, con acceso mínimo al filesystem, imposible de comprometer desde otros procesos. El modelo entrenado cruza la frontera de partición por un canal verificado formalmente. Esto es **cifrado militar + verificación formal + aprendizaje federado** — una combinación que no existe hoy en ningún producto comercial asequible.

---

## Preguntas abiertas (I+D necesario)

**P1 — Anonimización:** ¿Qué nivel de privacidad diferencial (epsilon) garantiza que el dataset anonimizado no re-identifica dispositivos médicos? 

SUPERSEDED — ver ADR-0043 D2/D3 y D4

**P2 — Web-of-trust:** ¿Cómo se establece la identidad de un nodo aRGus central? ¿Quién firma los certificados? ¿Modelo descentralizado (similar a PGP) o PKI jerarquizada?

**P3 — Agregación federada:** ¿Promedio de modelos (FedAvg), stacking, o selección del mejor? Para XGBoost los árboles no se promedian trivialmente. Revisar literatura: XGBoost-Fed, SecureBoost.

**P4 — Scheduler hospitalario:** ¿Cómo detectar "baja actividad segura" en un entorno médico? ¿Integración con sistemas HIS/RIS para saber si hay procedimientos activos?

**P5 — Incentivos:** ¿Por qué un hospital compartiría sus datos, aunque anónimos? Necesita un modelo de gobernanza claro — quizás acceso preferente a modelos globales mejorados.

---

## Dependencias y secuenciación

feature/adr026-xgboost MERGED (P0 — prerequisito)
↓
ADR-029 variantes hardened (AppArmor + seL4)
↓
RESEARCH-FEDERATED-001 (I+D anonimización + web-of-trust)
↓
ADR-038 implementación ml-trainer
↓
ADR-038 nodos centrales aRGus
↓
Piloto controlado (1 hospital, 1 nodo central, red aislada)

**Target realista: Q4 2026 para prototipo. Producción: 2027.**

---

## Impacto en el paper arXiv:2604.04952

Esta ADR eleva la contribución del paper de:

> *"NDR de bajo coste para infraestructura crítica"*

a:

> *"Propuesta de sistema inmune distribuido con aprendizaje federado para infraestructura crítica global — implementación de referencia open-source"*

Sección recomendada: §6 Future Work / §7 Vision, con diagrama de arquitectura federada y análisis de viabilidad técnica. No como trabajo especulativo, sino como extensión arquitectónica fundamentada con los componentes ya existentes.

---

## Conclusión

aRGus NDR ya tiene los cimientos: cifrado militar (ChaCha20-Poly1305 + Ed25519), plugin architecture extensible, pipeline reproducible, modelos XGBoost ligeros. La arquitectura federada no es un cambio de dirección — es la evolución natural del sistema hacia su potencial completo.

Un escudo que aprende. Un escudo que comparte. Un escudo que nunca olvida un ataque.

*"Via Appia Quality — un escudo, nunca una espada."*

---

*Borrador DAY 120 — 17 Abril 2026*  
*Pendiente: revisión Consejo de Sabios DAY 121+*
MDEOF
cp /tmp/ADR-038-federated-learning.md /Users/aironman/CLionProjects/test-zeromq-docker/docs/adr/ADR-038-federated-learning-draft.md
echo "✅ ADR-038 borrador creado"