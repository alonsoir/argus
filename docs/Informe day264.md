# Informe final — DAY264: Fase 2 arrancada. Cabeza DDoS por-flujo sobre CICDDoS2019

## 1. Objetivo del día
Pasar de "reparar el método sobre el generador sintético de Betas" a **entrenar una cabeza
detectora DDoS real** con features reales y labels reales, usando CICDDoS2019 como sustrato.
Todo por medición; cero código de producción; `main` protegida sin tocar. Los siete scripts
producidos viven untracked en `ml-training/scripts/ddos_detection/`.

## 2. Giro estratégico y el fork A/B
Al abrir Fase 2 apareció una bifurcación de arquitectura:

- **Path A** — reconstruir las 9 features sintéticas de aRGus offline y entrenar sobre ellas
  (entraría directa en el extractor serve actual).
- **Path B** — entrenar sobre features nativas CICFlowMeter y servirlas por el extractor
  BASE (las 102+ base network features, linaje CICIDS/XGBoost, mismo linaje que
  CICFlowMeter-V3 que produce CICDDoS2019).

Dos mediciones empujaron a Path B, no una opinión:
1. `source_ip_dispersion` degenera bajo flood: el cap de 10000 del ring buffer muerde en el
   **~95% de las lecturas** (`event_count` clavado en 10000) → la fórmula
   `log2(uniq+1)/log2(event_count+2)` se vuelve constante en el denominador y deja de ser un
   ratio de dispersión. Apoyar un detector real sobre el contrato sintético-9 es construir
   sobre arena.
2. Ninguna de las features que resultaron transferibles (ver §3) es una sintético-9. La
   señal DDoS real de CICFlowMeter vive en otro sitio.

## 3. Cadena de mediciones (lo que de verdad dijeron los datos)

**Censo del dataset.** 50.063.112 filas train (01-12) / 20.364.525 test (03-11). Benigno
≈0,16% del total (0,11% en train, 0,28% en test) → desbalance severo, a pesar de clases.
Trampa de naming cazada: `DrDoS_LDAP` (train) y `LDAP` (test) son el MISMO ataque de
reflexión; LDAP/MSSQL/NetBIOS/UDP NO son inéditos. El único held-out limpio real es
**Portmap**.

**Salud de columnas.** Inf confinado a `Flow Bytes/s` y `Flow Packets/s` (cols 22-23),
confirmado. Constantes por-fichero (12 en Portmap) — a decidir sobre TODOS los ficheros, no
sobre uno.

**Barrido AUC cross-ataque (la disciplina anti-atajo).** El AUC de una feature en un fichero
roza lo perfecto por puro atajo de herramienta; el criterio válido es la ESTABILIDAD del AUC
a través de muchos ataques (`sep_min`). Resultado:
- Atajo confirmado: `Min Packet Length` / `Fwd Packet Length Min` — sep_min 0,55, max 1,00,
  portmap 0,996. La estrella de Portmap era un espejismo de herramienta.
- Núcleo transferible: familia de estadísticos **backward** (`Bwd IAT *`, `Bwd Packet
  Length *`, `Total Backward Packets`, `Bwd Header Length`) + **agregados de tamaño**
  (`Average/Max/Packet Length Mean`, `Fwd Packet Length Max`). Asimetría física real:
  backward transfiere, forward no.
- `Inbound` (sep_min 0,886) domina pero es leakage de ENTORNO (todo el ataque va a una
  víctima fija) → no física de DDoS.

**Entrenamiento honesto (RF, split cruzado por día, Portmap held-out, ablación de Inbound).**
- Quitar `Inbound` casi no mueve el PR-AUC (delta +0,0006) → la señal transferible se
  sostiene sola; no era leakage de entorno. Path B tiene piernas.
- Portmap held-out: recall **0,998**. Generalización cross-ataque real, dentro de la familia
  reflexión/amplificación.
- SYN: recall se hunde a 0,59.

**Punto de operación.** El FPR de 7,86% a umbral 0,5 era artefacto del corte arbitrario. A
**umbral 0,647: FPR benigno 0,95%, recall global 88,8%, Portmap 99,7%.** Para
reflexión/amplificación, ESTO es un detector con punto de trabajo deployable. Los falsos
positivos del benigno son un **clúster coherente** (carga forward ~0, 1 paquete backward,
URG=1 — control/teardown o flujos degenerados), no ruido difuso → addressable.

**SYN: intento de rescate fallido y diagnóstico.**
- Añadir flags (SYN/ACK/RST + `syn_ack_ratio`) NO rescató SYN (delta −0,0047); el RF los
  ignoró.
- `SYN Flag Count` está al **100% en cero** en el dataset → CICFlowMeter-V3 no puebla el flag
  SYN en CICDDoS2019, así que `syn_ack_ratio` es irreconstruible aquí (hallazgo de calidad de
  dataset).
- **Pero H2 (techo fundamental por-flujo) queda REFUTADA:** al aislar el SYN escapado (38,7%)
  y preguntar qué lo separa del benigno, `ACK Flag Count` da **AUC 0,90**, y las features de
  tamaño lo separan en dirección INVERTIDA (0,82).

## 4. La corrección honesta (medir, no votar, aplicado a mí mismo)
Durante dos sesiones sostuve la hipótesis "SYN es un fenómeno de tasa que solo las features
de ventana (grieta B) pueden cazar". **Los datos la matan.** El SYN escapado SÍ tiene señal
por-flujo. El modelo conjunto la entierra por dos causas medibles:
1. **Conflicto de signo entre familias:** reflexión = paquete grande = ataque; SYN = paquete
   diminuto = ataque. Un único RF no puede dar signos opuestos a la misma feature de forma
   global, así que aprende el signo de la familia dominante (reflexión) y activamente
   malclasifica el SYN de paquete pequeño como benigno.
2. **SYN es masa minoritaria:** pierde el voto frente a las 4 reflexiones que dominan el
   train, y la feature que lo salvaría (`ACK Flag Count`) quedó fuera del conjunto base
   porque nuestra propia disciplina cross-ataque la excluyó como atajo. El atajo era, para
   SYN, exactamente lo que hacía falta.

Conclusión: el punto ciego de SYN **no es techo de datos, es arquitectura de entrenamiento.**
Y grieta B queda DEGRADADA de "requisito de cobertura de SYN" a hilo independiente (sigue
siendo un bug real del cap, pero ya no está en el camino crítico de esta cabeza).

## 5. Veredicto por vía
- **Cabeza por-flujo (Path B) para reflexión/amplificación: VIABLE.** Punto de operación
  medido y deployable. Recomendación: continuar.
- **Cobertura de SYN: alcanzable, pendiente de arquitectura.** No requiere ventana; requiere
  entrenamiento consciente de clase (o cabeza dedicada).

## 6. Riesgos y caveats (para no sobre-vender)
- El benigno es escaso y homogéneo (misma captura) → los números son un TECHO, no garantía de
  despliegue. El FPR real con benigno diverso probablemente sube.
- `ACK Flag Count` separando SYN puede ser un TERCER atajo (que el benigno tenga ACK=0 es
  sospechoso). Verificar antes de confiar.
- La generalización probada es DENTRO de la familia reflexión/amplificación (Portmap). No hay
  evidencia de generalización a física de ataque nueva.
- La huella dominante es el TAMAÑO de paquete → evadible por un adversario que varíe tamaños.

## 7. Decisión para mañana (árbol)
1. **Verificar `ACK Flag Count`** como señal robusta y no artefacto: repetir el AUC
   SYN-vs-benigno sobre `01-12/Syn.csv` (captura independiente). Si aguanta en ambos días,
   es señal; si solo en uno, es atajo.
2. **Si aguanta → probar cabeza SYN-aware:** o (a) entrenar solo SYN-vs-benigno con
   `ACK Flag Count` + tamaño para confirmar que una segunda vía caza el escapado, o
   (b) reponderar/oversamplear SYN en el modelo conjunto y medir si sube el recall de SYN
   sin cargarse Portmap ni el FPR. Diseño resultante probable: dos vías (backward/tamaño para
   reflexión, ACK para SYN).
3. **Cruce de servibilidad (gating de Path B):** intersectar {23 transferibles + ACK} contra
   la lista de 102+ base features servibles. Las presentes son Path B cableable; las
   ausentes son deuda de extractor. **Falta ese input (header/proto de las base).**
4. **Grieta B:** hilo aparte. Revisitar solo si se quiere detección volumétrica/tasa real más
   allá de lo que da la cabeza por-flujo; el bug del cap sigue vivo pero fuera del crítico.

## 8. Inventario (scripts nuevos, untracked)
`offline_source_ip_dispersion.py` (análogo offline de la feature serve; midió la
degeneración del cap) · `profile_cicddos.py` (censo + salud + AUC por feature) ·
`cross_attack_auc.py` (matriz AUC feature×fichero; transferible vs atajo) ·
`train_ddos_head.py` (RF cruzado por día, ablación Inbound) · `operating_point.py`
(barrido de umbral + autopsia de falsos positivos) · `syn_rescue.py` (baseline vs +flags) ·
`syn_diagnostic.py` (salud de flags + qué separa el SYN escapado).
Artefactos de datos: `auc_matrix.csv` / `auc_matrix_summary.csv`, `portmap_disp.parquet`.