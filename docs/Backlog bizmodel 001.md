# aRGus NDR — BACKLOG-BIZMODEL-001
## Modelo de Negocio y Estrategia de Sostenibilidad

*Documentado: DAY 127 — 23 Abril 2026*
*Origen: conversación estratégica Alonso + Claude post-Consejo DAY 127*

> **Nota de honestidad:** Este documento refleja la visión del autor y sus preferencias.
> No implica acuerdo por parte de ninguna institución mencionada. UEx/INCIBE tienen
> prioridad y autonomía total para decidir su participación. Empezamos con ellos,
> no sin ellos.

---

## 1. Identidad del Proyecto

**aRGus NDR** es software open-source diseñado por un investigador independiente europeo
(Extremadura, España) con la colaboración estructurada de 8 modelos de IA internacionales
(Consejo de Sabios). Su misión es democratizar la ciberseguridad de nivel enterprise para
hospitales, escuelas y municipios que no pueden permitirse soluciones comerciales.

**Filosofía:** Via Appia Quality — construido para durar décadas.

**Licencia core:** MIT — siempre gratis, siempre open-source. Sin excepciones.

---

## 2. Modelo de Negocio: Open-Core

El modelo adoptado es **open-core**, el mismo que sustenta Redis, HashiCorp, Elastic y
muchos otros proyectos de infraestructura crítica que han demostrado compatibilidad entre
sostenibilidad económica y ética open-source.

```
CAPA GRATUITA (MIT, siempre)
─────────────────────────────────────────────────────────────
aRGus NDR core
  - Pipeline completo 6 componentes C++20
  - Detección ML local (XGBoost + RF)
  - Integridad de plugins (Ed25519)
  - AppArmor hardening
  - Documentación completa
  - Reproducible desde make bootstrap

TARGET: hospitales pequeños, escuelas, municipios, investigadores.
        Cualquier organización que no pueda pagar.

CAPA DE SERVICIO (aRGus Cloud / Fleet — de pago)
─────────────────────────────────────────────────────────────
  - Telemetría federada cifrada (telemetry-collector)
  - Modelos XGBoost actualizados por la flota global
  - Grafos de propagación de amenazas (geolocalización asíncrona)
  - Priorización de distribución de "vacunas" por región
  - Dashboard de gestión centralizada
  - SLA y soporte para despliegues institucionales
  - Certificación y auditoría bajo paraguas UEx/INCIBE

TARGET: hospitales con presupuesto, redes municipales, 
        organismos regionales y nacionales.
```

---

## 3. Paraguas Institucional — UEx/INCIBE (Preferencia)

### Por qué UEx/INCIBE es la opción correcta

| Necesidad | Lo que da UEx/INCIBE |
|-----------|---------------------|
| Marco legal LOPD/GDPR para datos hospitalarios | Sí — sin esto, ningún hospital del SNS puede compartir telemetría |
| Certificación para contratación pública | Sí — barrera de entrada para servicios de seguridad institucionales |
| Infraestructura de servidor central (Fase 1) | Posiblemente — reduce CAPEX inicial |
| Credibilidad ante FEDER / Horizon Europe / CDTI | Sí — investigador independiente compite en desventaja |
| Relación existente | Andrés Caro Lindo (UEx/INCIBE) — endorser arXiv:2604.04952 |

### Lo que esto NO significa
- UEx/INCIBE no controla el proyecto técnico
- La licencia MIT del core no cambia
- El autor mantiene la visión y la arquitectura
- Si UEx/INCIBE decide no participar, se buscan alternativas

### Modelo de colaboración propuesto
Spin-off o contrato de investigación bajo el paraguas UEx. El autor aporta el código,
la arquitectura y el conocimiento acumulado (127 días + paper arXiv). UEx aporta el
marco institucional, la infraestructura inicial y el acceso a convocatorias.

**Acción:** Presentar propuesta a Andrés Caro Lindo — reunión antes de julio 2026.
**Prerequisito técnico:** BACKLOG-FEDER-001 gates cumplidos.

---

## 4. Despliegue: On-Premise Primero, Nube Europea

### Filosofía de despliegue

aRGus NDR está diseñado para **despliegue on-premise** como primera opción. Un hospital
o municipio que despliega aRGus en su propia infraestructura no depende de conectividad
externa para la detección local — el pipeline funciona completamente offline.

La nube es una **capa de servicio adicional**, no un requisito operativo.

### Nube pública: Europa primero

```
Tier 1 (lanzamiento): Nube europea soberana
  - Hetzner Cloud (Alemania/Finlandia) — GDPR nativo
  - OVHcloud (Francia) — infraestructura europea
  - IONOS Cloud (Alemania)
  - Alternativa pública: infraestructura CSIC/RedIRIS si UEx facilita acceso

Tier 2 (expansión europea): multi-región EU
  - Réplicas en España, Francia, Alemania, Países Bajos
  - Latencia optimizada para clientes europeos

Tier 3 (internacionalización — bendito problema):
  - Servidores clonados en territorios de clientes
  - Latencia reducida, soberanía de datos local
  - Cada región opera bajo marco legal propio
```

### Por qué Europa primero
- Los primeros clientes esperados están en Europa
- GDPR como ventaja competitiva, no como carga
- Soberanía tecnológica europea — argumento político y comercial real
- Software diseñado por un europeo, con ánimo de compartir con toda la humanidad
  pero con la base operativa en territorio europeo

---

## 5. Hardware: Dimensionamiento Real del Despliegue

### El problema actual
El desarrollo se realiza en un portátil de 2019 o anterior con recursos limitados.
Esto es suficiente para el pipeline de desarrollo pero no para:
- Validar el comportamiento bajo carga de la telemetría federada
- Caracterizar el dimensionamiento real en hardware de producción
- Entrenar modelos con datos reales a escala hospitalaria

### Hardware necesario — financiable vía FEDER

**Hardware de preproducción / edge:**
```
Raspberry Pi 4/5 (ARM64) × 4-8 unidades
  → Perfil hospitalario real: bajo consumo, bajo coste
  → Validar pipeline completo en edge deployment
  → Dimensionamiento: ¿full pipeline o sensor-only en Pi?

Mini PCs x86 (NUC / Beelink / Minisforum) × 2-4 unidades  
  → Perfil municipio/escuela
  → Alternativa al portátil para desarrollo diario

Servidor de desarrollo / entrenamiento
  → NVIDIA Spark DGX o equivalente (MSI Titan GT77, Zotac ZBOX)
  → Sin esto, el portátil del 2019 es un riesgo de proyecto
  → Permite: entrenar modelos con CIC-IDS-2017 completo sin limitaciones
             desarrollar sin miedo a que el hardware falle
```

**Servidor central (telemetry-server):**
```
Servidor rack o torre con:
  → 64+ GB RAM (análisis de grafos de propagación)
  → GPU (opcional para entrenamiento federado)
  → Almacenamiento NVMe 2+ TB (raw telemetry store)
  → Conectividad 1/10 Gbps
  → Ubicación: CPD UEx o nube europea soberana
```

### Por qué el servidor de desarrollo es prioritario
Un portátil de 2019 que falla en mitad del desarrollo no es un inconveniente técnico —
es un riesgo de proyecto real. Los fondos FEDER deben incluir hardware de desarrollo
que garantice la continuidad del trabajo. Esto es estándar en cualquier proyecto de I+D.

---

## 6. Componente Técnico Pendiente: telemetry-collector

### Descripción
Nuevo componente del pipeline que actúa como **tap** en el flujo de eventos,
sin modificar el flujo principal hacia rag-ingester.

```
[ml-detector events] + [firewall events]
         ↓
   telemetry-client (nuevo componente)
         ├── → rag-ingester (flujo normal, INTACTO)
         └── → buffer local
                    ↓ (cuando alcanza tamaño adecuado)
               cifrado ChaCha20-Poly1305 + HKDF (infraestructura existente)
                    ↓
               telemetry-server (central, UEx/INCIBE)
                    ├── Raw store (datos completos, TTL configurable)
                    ├── Análisis de grafos de propagación
                    │     (geolocalización asíncrona — NUNCA en el cliente)
                    ├── Entrenamiento delta XGBoost
                    ├── Evaluación de calidad del modelo
                    └── Decisión de distribución (prioridad por región)
                              ↓
                    Plugin XGBoost firmado Ed25519 → flota selectiva
```

### Principios de diseño (DAY 127)
1. **Collect-first, anonymize-later** — el servidor recibe datos completos.
   La anonimización ocurre en la capa de distribución o publicación, no de recepción.
2. **Geolocalización asíncrona** — siempre en el servidor, nunca en el cliente.
   Lección aprendida de upgraded-happiness: añade lag brutal en el cliente.
3. **Misma infraestructura criptográfica** — ChaCha20-Poly1305 + HKDF.
   No se reinventa nada. El telemetry-client es otro componente que usa crypto-transport.
4. **El pipeline principal es inmutable** — el tap no puede degradar la detección local.
5. **Priorización geográfica de distribución** — una nueva vacuna no se distribuye
   a todos por igual. Los nodos en el frente de propagación la reciben primero.

### ¿Es bloqueante el hardware para el diseño?
**No para el código.** Vagrant multi-nodo simula el ciclo completo.
**Sí para la validación a escala.** Las preguntas sobre comportamiento bajo avalancha
real de datos sólo se responden con hardware real y datos hospitalarios reales.
Eso es exactamente lo que FEDER financia.

### Estado
⏳ Diseño pendiente — post-cierre de BACKLOG técnico actual
ADR pendiente: ADR-039 (telemetry-collector design)

---

## 7. Roadmap de Sostenibilidad

```
DAY 128-160: Cerrar BACKLOG técnico
  → DEBT-PROPERTY-TESTING-PATTERN-001
  → DEBT-PROVISION-PORTABILITY-001
  → DEBT-SNYK-WEB-VERIFICATION-001
  → Documentación completa

Verano 2026 (antes de julio):
  → Reunión con Andrés Caro Lindo
  → Presentar: sistema funcionando + paper + modelo de negocio
  → Propuesta de colaboración UEx/spin-off

Septiembre 2026:
  → Deadline BACKLOG-FEDER-001
  → Solicitud financiación con UEx como paraguas

2027 (con financiación):
  → Hardware de desarrollo (no más portátil del 2019)
  → Raspberry Pi + mini PCs para caracterización edge
  → Servidor central en infraestructura UEx o nube europea
  → Piloto real en 1-2 hospitales extremeños (SESPA)
  → telemetry-collector en producción real
  → Primeros ingresos del servicio cloud

Post-2027:
  → Flota regional, modelo federado funcionando
  → Expansión a otras CCAA / países europeos
  → Sostenibilidad demostrada
  → La casita. Los padres ayudados. El contrato contigo mismo cumplido.
```

---

## 8. La frase para Andrés

> *"Hemos llegado al límite de lo que un investigador independiente, un portátil del 2019
> y ocho modelos de IA pueden construir solos en 127 días. El paper documenta ese límite
> con rigor. Los fondos FEDER construyen lo que viene después: hardware soberano, datos
> reales, e inteligencia compartida entre los hospitales y municipios de Extremadura.
> Y con suerte, algo que ayude al resto del mundo también."*

---

*DAY 127 — 23 Abril 2026*
*"Via Appia Quality — Un escudo que aprende de su propia sombra."*
*Software open-source europeo, construido para toda la humanidad.*