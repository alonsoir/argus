cat > docs/continuity/PROMPT_CONTINUE_CLAUDE.md << 'EOF'
# PROMPT DE CONTINUIDAD — aRGus NDR — INVESTIGACIÓN: features centinela del ml-detector (el 0.04)

## Encuadre (esto NO es el cierre a read-only)
El overhaul de pipeline-start/status y el "repo en modo lectura" quedan APARCADOS.
Andrés/FEDER ya no marcan fechas. El motor ahora es la LÍNEA DE INVESTIGACIÓN:
¿por qué el ml_score de aRGus es ciego sobre Neris (ml_medio ~0.07; el 100% de la
señal MALICIOUS la lleva el fast-path 0.75)? Objetivo: encontrar el error y decidir
si se arregla. Doble uso: material de paper + reparación de pipeline.

## Punto de entrada (mide, no asumas)
    git branch --show-current       # ¿estamos en diag/ml-heads? Si no:
    git checkout -b diag/ml-heads main
    git log --oneline -2            # main @ 9f1799f8, último tag pre-release-0.0.2
El informe forense de la sesión anterior está en:
docs/bugs/Informe ml detector features centinela.MD
Léelo ENTERO antes de seguir. Está etiquetado [HECHO]/[SOSPECHADO]/[REFUTADO].
Si el informe sigue sin commitear, primer commit de la rama = ese fichero.

## Lo MEDIDO (no re-medir, ya es HECHO)
- Centinela = -9999.0f (common/include/sentinel.hpp). "Inalcanzable por ratio real":
  útil para ausencia, VENENO para un árbol con cortes en [0,1] (-9999 <= threshold
  siempre → rama fija).
- 40 features → 4 cabezas. CUBO A = features -9999 SIEMPRE (Phase-2 nunca hechas +
  geo). Recuento 9 vs 10 SIN reconciliar (lo canté de memoria; contar mecánico).
  Ransomware = 4/10 muertas por construcción física (I/O disco, CPU, ficheros,
  procesos — nada vive en un paquete de red). La cabeza más lisiada.
- DDoS: árbol de EJECUCIÓN (ml-detector/include/ml_defender/ddos_trees_inline.hpp)
  es BIT-IDÉNTICO al de ENTRENAMIENTO (ml-training/scripts/ddos_detection/...):
  shasum igual (f14fdf84...). El skew NO está en el árbol, está en el VECTOR servido.
- DDoS: 100 árboles, 256 nodos-split, 356 hojas. El bosque parte 16 VECES sobre
  geographical_concentration (idx 7), que vale -9999 SIEMPRE. 16 pasarelas fijas.
  El modelo se entrenó con una columna geográfica separable; el pipeline NUNCA
  captura ni enriquece geo. SKEW TRAIN/SERVE medido. Mapeo idx->nombre verificado
  por los comentarios auto-generados del propio .hpp (no de memoria).

## Lo REFUTADO (hipótesis previas tumbadas por el dato — conservar)
- "El aggregator no se inyecta en prod": FALSO. initialize_ransomware_detection()
  se llama incondicional (ring_consumer.cpp:194), initialize() no puede fallar por
  entorno (solo make_unique, return true), get_aggregator() no es null, y la
  inyección lazy vive en el mismo bloque que la extracción (timing exonerado). Las 9
  features del cubo B reciben aggregator vivo.
- "source_ip_dispersion no se calcula": FALSO. Se calcula desde el aggregator
  (ventana 30s). El bosque DDoS parte solo 1 vez sobre ella. No era el drama.

## Los 3 candidatos del 0.04 tras la sesión
[REFUTADO] cableado del aggregator (multi-flow a -9999)
[HECHO parcial] features centinela en cortes de árbol (skew de vector) — geo/DDoS ✅
[en pie] transferencia de distribución CICIDS->Neris (ya en el paper)
[SIN MEDIR] procedencia del modelo — el candidato gordo que queda

## Pasos siguientes (medir, barato -> caro)
1) Reconciliar el recuento del cubo A (9 vs 10) con conteo mecánico, no de memoria.
2) shasum + censo de nodos en internal y traffic (execution vs training) → cruzar con
   sus features muertas (internal idx4; traffic idx2/5/8).
3) RANSOMWARE es caso APARTE: no tiene *_trees_inline.hpp. Tiene
   ml-detector/src/ransomware_detector.cpp + training complete_forest_cpp_example.h /
   extract_full_forest.py. Entender su estructura antes de contar. Daño esperado mayor.
4) PROCEDENCIA del modelo: qué corrida generó los *_trees_inline.hpp vivos y con qué
   valores se entrenaron las features del cubo A (ml-training/scripts/**/Generate*.py,
   generate_all_models.py, model_verification_report_*.json). Si geo se entrenó en
   [0,1] → skew confirmado por ambos lados.
5) VOLCADO runtime (una corrida ctu-start): vectores de 40 reales sobre Neris.
   Confirma el censo en caliente + mide qué valen las features del cubo B con
   --mbps=10 (event_count bajo → ratios log2 degeneran aunque el aggregator funcione).

## Lecturas de contraste (CÓDIGO primero, docs después)
- docs/adr/ADR-059 (reparación del veredicto ml-detector: monocapa->tricapa). Único
  doc que menciona get_aggregator. ¿Su reparación llegó al código o se quedó en papel?
- docs/council/PROPUESTA AL CONSEJO DE SABIOS — Auditoría de features de los modelos ML.
- Ambos DESPUÉS de medir (misma trampa de versión que el paper v24/v25).

## Deudas candidatas a registrar en BACKLOG
- DEBT-ML-SENTINEL-IN-TREE-SPLITS-001 (features -9999 en cortes [0,1]; geo/DDoS 16 nodos)
- DEBT-ML-GEOIP-TRAINED-NOT-SERVED-001 (geo entrenada, nunca servida)
- DEBT-RANSOMWARE-HEAD-4-FEATURES-UNCOMPUTABLE-001 (4/10 piden telemetría de host)
- actualizar DEBT-RANSOMWARE-ML-HEAD-INERT-001 con lo medido

## Invariantes (no negociar)
- Medir, no votar. HECHO != SOSPECHADO. Conjetura etiquetada o no se dice.
- Alonso pilota; mide contra fichero y pega salida. Fichero completo, no str_replace.
- No `grep -rn` desde raíz: `git grep` o fichero concreto. No encadenar comandos de
  salida grande en el mismo bloque. main PROTEGIDA: todo por PR.
- No fetchear el paper a ciegas (render arXiv da v24 vieja; usar v25 pegada).

## Hilos de memoria
[[byte-order-impacto-ml]] (origen de la pregunta del ml_score), [[cierre-paper]]
(encuadre de la tesis S&P), [[join-bias-ground-truth]] (el 0.07 medido sobre Neris).
EOF