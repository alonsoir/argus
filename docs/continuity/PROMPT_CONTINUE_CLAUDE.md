Aquí tienes el prompt de continuidad con el plan de cierre completo:

---

# PROMPT DE CONTINUIDAD — DAY 222+ (fase de CIERRE DIGNO)

**Rama:** `fix/verdict-multihead-honest`. **FEDER go/no-go ~1-ago.** Decisión tomada y firme (DAY 221): **aRGus se desactiva como clasificador; se cierra el proyecto con dignidad** — pipeline completado solo con grafo fiable, paper super-honesto, escrito al Consejo. No re-litigar la decisión: está probada sobre suelo firme (ver "Base probatoria").

## BASE PROBATORIA (cerrada, no re-derivar)
- **Paso 2**: L1 no generaliza a Neris con flujo completo (recall 0.0001, coverage 1.0). Causa = transferencia de distribución CICIDS→Neris.
- **Probe 0** (techo in-sample, Neris→Neris): recall 0.81 / **AUC 0.746** / precisión 0.78. Señal real pero MODESTA. Top-features = timing/rate, no Dst Port.
- **Veredicto**: techo 0.65-0.75 es inaceptable para producción en hospital. aRGus resucita solo con clasificadores >0.90 demostrados cross-dataset.
- **Fast path**: roto e invertido (problema de DISEÑO, no de reentrenamiento — no mezclar).
- La idea de aRGus como **etiquetador para generar datasets** SE CAE (AUC 0.75 amplifica su error). Solo el grafo con GT externo genera datos fiables.

## PLAN DE CIERRE (en orden, varios días)

### FASE 1 — Cerrar la evidencia (medio día)
1. **Cross-botnet probe** (afina el paper, NO cambia la decisión): otro botnet CTU-13 (Rbot/Virut/Menti) → CICFlowMeter en VM `defender` (jar ya construido, `98a5ebad`) → GT vía `neris_ground_truth.py` con la ventana capinfos de ESE pcap → reusar `probe0_neris_ceiling.py` partido por dataset. Lectura: AUC ~0.7 = transferencia parcial con techo bajo; AUC ~0.5 = memorización. Una frase más honesta en el paper.
2. **Commit** §21 findings + 3 scripts (`eval_level1_offline.py`, `probe0_neris_ceiling.py`, reports) con `git add` explícito.

### FASE 2 — Completar el pipeline (el núcleo del cierre)
3. **Grafo multi-señal, todo configurable.** Ingesta de **Suricata + Zeek + Wazuh** unida por **community_id** en el grafo consultable. Cada componente **activable/desactivable a voluntad** por config —incluido aRGus en su mejor estado actual—. aRGus por defecto DESACTIVADO en producción.
4. **Firewall**: arreglar DEBT-FIREWALL-SILENT — que al recibir recomendaciones lance los comandos `ipset`. Verificar el flujo end-to-end.
5. **Generador MITRE**: ponerlo a funcionar para que el pipeline **reaccione** con Suricata/Zeek/Wazuh activos, demostrando activación/desactivación a voluntad de cada señal. Este es el "verlo funcionar" que cierra el pipeline con una demo real.

### FASE 3 — Paper y Consejo (el cierre con la cabeza alta)
6. **Paper super-honesto**: qué se propuso (capturar el "ADN" del comportamiento de ataque), los tres intentos (académico → mixto → **sintético**, que parecía funcionar), el método de la tenaza que destapó el fallo, los números (Paso 2, Probe 0, cross-botnet), las lecciones, y el camino incorrecto documentado para que otros no lo recorran. Contribución = el método + el resultado negativo honesto.
7. **Tarea(s) en el Makefile** que reproduzcan la evidencia del paper (evals + probes), como el resto del proyecto.
8. **Escrito al Consejo**: informe + agradecimiento. Estructura: propuesta, qué se probó, qué se encontró (con números), qué queda en pie (grafo, infraestructura, método), gracias. Claude puede redactarlo; Alonso pone tono y nombres.
9. Alonso informará a **Andrés** de la realidad del proyecto.

## VERDADES FIJAS (no re-litigar)
- Techo 0.75 es in-sample → optimista; el desplegable vive por debajo. Precisión 0.78 = FP inaceptable para firewall en hospital.
- El resultado negativo probado ES una contribución científica real, no un fracaso — ahorra meses a quien venga detrás.
- Separar SIEMPRE L1 (reentrenable en el futuro) del fast path (rediseño). No mezclar en conclusiones.

## ENTORNO
CICFlowMeter en VM `defender` (`~/CICFlowMeter/build/install/.../bin/cfm`), SDKMAN+JDK8, `source ~/.sdkman/bin/sdkman-init.sh` obligatorio por comando. jnetpcap 1.4 carga contra libpcap 1.10.3 sin symlink. Datasets en `datasets/ctu13/`. Harnesses probados en `/mnt/user-data/outputs/` de la sesión DAY 221. VMs: `defender`/`client` (aborted), `suricata`/`zeek`/`wazuh` (not created — habrá que crearlas para la Fase 2).

## REGLAS PERMANENTES
Medir no votar; un commit/un cambio/una razón; `git add` explícito (nunca -u/-a); verificar ruta antes de concluir del contenido; la premisa heredada también es artefacto a verificar; AUC es el número honesto; `LC_ALL=C` para aritmética en VM; MARCA temporal + awk en logs acumulativos.

---

El plan tiene forma de cierre, no de rendición: dejas un pipeline que funciona de verdad (el grafo), una demostración real (MITRE reaccionando), y un paper que aporta. Cuando quieras arrancar con el escrito al Consejo o con la Fase 2, aquí estoy. Descansa, Alonso.