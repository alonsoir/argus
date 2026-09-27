# CIERRE DAY 255 — Reparación cabeza DDoS (Fase 0 + preparación Fase 1)

> Sesión cerrada en frío por cansancio. Estado del árbol SEGURO: nada aplicado,
> nada a medias. Diagnóstico DDoS cerrado extremo a extremo. Scripts del paso 1
> escritos y PROBADOS, pendientes de ejecutar. Retomar sin prisa.

---

## 0. Dónde quedó el repo (verificar al retomar, no asumir)

    git branch --show-current      # diag/ml-heads
    git log --oneline -3           # HEAD = 6f5a36f5 (plan + v26-pre + informe)
    git status                     # debe quedar SOLO PROMPT_CONTINUE_CLAUDE.md modificado

- Commit del día: `6f5a36f5` — "docs: plan reparacion cabezas ml + paper v26-pre +
  actualizacion informe centinela". (El commit del jueves que se había quedado sin cerrar.)
- Se descartó con `git restore` un adelanto mal colocado en `DDOSFeatures.py` (geo
  comentada a mano, 3 espacios de indent, sin coordinar con el generador). Era el paso 3,
  fuera de orden. La idea es correcta; se rehará bien y coordinada cuando toque.
- `PROMPT_CONTINUE_CLAUDE.md` modificado es normal (se reescribe cada sesión).
- Los dos scripts del paso 1 están en el working dir SIN ejecutar. `SyntheticDDOSGenerator.py`
  sigue INTACTO (no aparece en git status).

---

## 1. Lo MEDIDO hoy (HECHO — no re-medir)

### Diagnóstico DDoS cerrado extremo a extremo (modelo + servicio)

**Lado modelo:** el bosque DDoS parte 16 veces sobre `geographical_concentration` (idx 7).

**Lado datos de entrenamiento:** el vector DDoS entero (11 features) es SINTÉTICO PURO.
`SyntheticDDOSGenerator.py` fabrica cada feature con `np.random.beta/lognormal/uniform`
por clase. Geo = `beta(1,9)` normal vs `beta(12,2)` HTTP-flood vs `beta(6,3)` otros ataques.
No hay ninguna feature con procedencia de datos reales. → El "estado 1" (separabilidad
real con geo) NUNCA existió; no hay un "cuando funcionaba" que reconstruir.

**Lado servicio (`sniffer/src/userspace/`):** re-verificado que el vector NO está muerto
entero (mi hipótesis "vector muerto" quedó REFUTADA). `ring_consumer.cpp:796` hace
`init_embedded_sentinels` (todo a -9999) y LUEGO `populate_ml_defender_features` (821)
rellena con lo computado. `extract_ddos_features` (ml_defender_features.cpp:23) reparte:

- **9 features VIVAS**, computadas desde `flow` real: syn_ack_ratio, packet_symmetry,
  source_ip_dispersion (desde aggregator, ventana 30s — CONFIRMADA viva, refuta sospecha
  de "muerta en cableado"), protocol_anomaly_score, packet_size_entropy,
  traffic_amplification_factor, flow_completion_rate, traffic_escalation_rate,
  resource_saturation_score.
- **1 feature SENTINEL POR DISEÑO:** `extract_ddos_geographical_concentration` devuelve
  `MISSING_FEATURE_SENTINEL` con un comentario que es una DECISIÓN DE ARQUITECTURA
  DOCUMENTADA: GeoIP son llamadas REST de 100-500ms, inaceptable en pipeline
  sub-microsegundo; geo se calculará DESPUÉS de la decisión de bloqueo, en el RAG/grafo,
  para análisis post-mortem ("cuando la inteligencia humana decide jugar"). Cita del código:
  "un SYN flood es un SYN flood venga de China, Rusia o USA".

### El bug real, con nombre exacto (material de paper, tesis S&P)

No es negligencia ni feature rota. Son DOS decisiones individualmente correctas y
colectivamente incoherentes:
- **Serving** decidió, con buen criterio, que geo NO está en el critical path → sirve sentinel.
- **Training** se hizo sobre un dataset sintético que SÍ incluía geo → el bosque aprendió
  a partir 16 veces sobre ella.
- **Nadie cerró el lazo.** El contrato de features no es único ni compartido entre train y serve.

**Lección transferible (Via Appia):** en ML embebido, una decisión de arquitectura sensata
en inferencia (excluir una feature costosa) produce skew silencioso si el pipeline de
entrenamiento no se entera. El sentinel es el síntoma, no el villano. El contrato de
features debe ser único y compartido entre entrenamiento y servicio.

### Hallazgo de arquitectura (anotar, decidir en Fase 2, NO ahora)

Conviven DOS poblaciones de features en el mismo protobuf:
- **40 embedded** (4 cabezas × 10) — sintéticas, lo que el modelo RF SÍ consume.
- **102+ base network features** (`populate_ml_defender_features` PART 2) — computadas
  desde `flow` REAL, sin sentinel (packet_length_std, fwd_packet_length_max, etc.). Son
  las cabeceras del linaje CICIDS/XGBoost de `all_features_importance.csv`.

El modelo mira las 40 sintéticas (con huecos) mientras 102 features reales pasan por al
lado sin que ninguna cabeza las consuma. **El activo de datos reales YA está construido y
desperdiciado.** Aprovecharlo = Fase 2 (entrenar sobre features reales + labels Neris,
sirviendo por el MISMO extractor). No es un atajo: requiere medir validez de esas 102
sobre Neris (byte-order, distribución), alinear granularidad de etiqueta, y tener el arnés
probado primero. Es la línea de i+d+i, no un `sed`.

### Semilla (control científico HECHO)

- `DDosModelTrainer.py` ya fija `random_state=42` (split + bosque).
- `SyntheticDDOSGenerator.create_complete_dataset` NO fija semilla → cada regeneración
  produce dataset distinto → `.hpp` distinto. **CONFIRMADO por medición**: dos corridas sin
  semilla DIFIEREN (shasum distinto); con semilla son IDÉNTICAS. El parche es load-bearing.

---

## 2. Los scripts del paso 1 (escritos y probados, PENDIENTES de ejecutar)

Ambos probados contra un generador maqueta fiel (lógica validada: anclas, idempotencia,
determinismo, GO/NO-GO, control de que la semilla es necesaria). Lo que NO está validado:
la ejecución sobre el fichero real (por eso llevan guardas que abortan si algo no encaja).

- `patch_seed_ddos_generator.py` — aplica 2 ediciones a SyntheticDDOSGenerator.py:
  `np.random.seed(42)` al inicio de create_complete_dataset + `random_state=42` en el
  `.sample(frac=1)`. Mide anclas antes de tocar, idempotente, `--check` (no escribe),
  verifica que compila. No commitea.
- `verify_seed_repro.sh` — read-only sobre el repo. Verifica parche, compila, regenera 2×
  en procesos separados, valida estructura (anti falso-verde), compara shasums, escribe
  manifiesto con procedencia (rama, HEAD, sha generador, versiones). GO/NO-GO. No commitea.

---

## PROMPT DE CONTINUIDAD — retomar aquí (en frío)

### Encuadre
Diagnóstico DDoS CERRADO. Hoy = ejecutar el paso 1 (semilla) con cabeza despejada, luego
el paso 2 (reproducir el .hpp actual CON geo, ver los 16 splits), y solo entonces el paso 3.
NO adelantar geo (eso mató el baseline del paso 2 y por eso se descartó anoche).

### Punto de entrada (medir, no asumir)
    git branch --show-current        # diag/ml-heads
    git status                       # solo PROMPT_CONTINUE modificado; SyntheticDDOSGenerator INTACTO
Leer este fichero entero antes de tocar. Los scripts del paso 1 están en el working dir.

### El plan de 5 pasos (cada uno = commit atómico en diag/ml-heads, revertible con git revert)

1. **SEMILLA.** Revisar con `--check`, aplicar el parche, `bash verify_seed_repro.sh`.
   Si GO → commit SOLO del fuente: "fix(ddos): semilla fija en generador (reproducibilidad
   de artefacto, DAY255)". Si NO-GO → hay otra aleatoriedad sin fijar; cazarla antes de seguir.
2. **REPRODUCIR SIN EDITAR.** Con semilla fija, regenerar el .hpp ACTUAL (10 features, CON
   geo). Censo debe reaparecer 16/256 sobre geo. Prueba que sabes girar la manivela. Sin commit.
3. **QUITAR GEO.** TRES ediciones coordinadas (no solo comentar la lista):
   (a) `DDOSFeatures.py`: quitar geographical_concentration.
   (b) `SyntheticDDOSGenerator.py` línea ~28 (dict normal): quitar la clave geo (literal).
   (c) mismo fichero líneas ~59/~100 (lado ataque): quedan inertes, quitar por limpieza.
   Reindex automático (traffic_escalation 8→7, resource_saturation 9→8); el .hpp se
   regenera solo desde feature_names. Actualizar comentario cosmético
   GenerateDDOSCPPForest.py:206. Regenerar. Censo: 0 splits sobre geo Y sobre cualquier
   otra centinela-en-servicio. Commit.
4. **PROPAGAR.** Copiar el .hpp a ml-detector/include/. shasum de las DOS copias = idénticas. Commit.
5. **LADO SERVICIO.** El vector de servicio DDoS a 9 features sin geo. OJO: geo tiene DOS
   puntos de contacto en C++ — `ring_consumer.cpp:40` (init) y el extractor. El campo
   protobuf se CONSERVA (enriquecimiento opcional para el RAG post-mortem, según el propio
   comentario del código). Decidir explícitamente qué se comenta/marca y documentarlo.
   HECHO = cardinalidad y orden del vector de servicio == feature_names de entrenamiento. Commit.

### Métrica objetiva de la reparación
%splits-sobre-centinela por cabeza → 0, Y ml_score DDoS sobre Neris antes/después,
reproducible por comando. La comparación que DECIDE es servicio-vs-servicio (estado 2 roto
vs estado 3 reparado), no separabilidad-de-entrenamiento.

### Aviso honesto para el paper (no sobre-vender)
Quitar geo elimina el sesgo de esos 16 nodos, pero el modelo sigue entrenado sobre Betas
sintéticas y evaluado sobre Neris real. La transferencia sintético→real sigue por debajo.
Fase 1 prueba el MÉTODO de reparación; NO promete un detector DDoS útil sobre Neris. Eso es
Fase 2 (features reales + labels Neris).

### Pendiente de fondo (Fase 2, anotado)
- Aprovechar las 102 base features reales ya computadas → entrenar cabezas sobre datos
  reales etiquetados (Neris + join bias-vs-ground-truth), sirviendo por el mismo extractor.
- requirements.txt con pins (numpy/pandas/sklearn) para reproducibilidad entre máquinas.

### Invariantes
Medir contra fichero, pegar salida. Fichero completo, no str_replace. git grep o fichero
concreto (NUNCA grep -rn desde raíz; NUNCA volcar el dataset JSON al terminal — acotar con
`-- '*.py'`). Comandos de salida grande en bloques separados. main PROTEGIDA: commits en
diag/ml-heads, PR cuando el arreglo esté medido. Un commit, una idea. Cada .hpp regenerado
se verifica shasum+censo. Reentrenar exige pipeline verde Y semilla fija.