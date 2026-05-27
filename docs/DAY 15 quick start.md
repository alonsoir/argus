# 🎯 DAY 15 - RESUMEN EJECUTIVO

## ✅ LO QUE FUNCIONA HOY
- RAGLogger compilado e integrado
- Logs en JSON Lines: `/vagrant/logs/rag/events/YYYY-MM-DD.jsonl`
- Artifacts: `.pb` (protobuf) + `.json` (legible)
- Filtrado: score >= 0.70 OR divergence >= 0.30

## 🚀 SECUENCIA RÁPIDA MAÑANA

### 1. Verificar Sistema (5 min)
```bash
# Dependencias
vagrant ssh defender -c "dpkg -l | grep -E 'libssl-dev|nlohmann-json3-dev|jq'"

# Directorios
make rag-init

# Config
cat config/rag_logger_config.json
```

### 2. Test SmallFlows (10 min)
```bash
make rag-clean
make test-replay-small
make rag-status
make rag-analyze

# Expected: ~80-100 eventos RAG
```

### 3. Test Neris (45 min)
```bash
# Preparar
make rag-clean

# Opcional: Deshabilitar artifacts en config (más rápido)
# save_protobuf_artifacts: false
# save_json_artifacts: false

# Ejecutar
make test-replay-neris  # 492K eventos, ~30-45 min

# Monitorear
tail -f /vagrant/logs/rag/events/$(date +%Y-%m-%d).jsonl | jq .

# Analizar
make rag-analyze
```

### 4. Análisis Botnet IPs
```bash
# IPs del botnet Neris
BOTNET_IPS="147.32.84.165 147.32.84.191 147.32.84.192"

# Eventos de botnet en RAG
cat /vagrant/logs/rag/events/*.jsonl | \
  jq -r 'select(.network.five_tuple.src_ip == "147.32.84.165" or 
                .network.five_tuple.src_ip == "147.32.84.191" or 
                .network.five_tuple.src_ip == "147.32.84.192")' | \
  wc -l

# Scores de botnet
cat /vagrant/logs/rag/events/*.jsonl | \
  jq -r 'select(.network.five_tuple.src_ip | IN("147.32.84.165", "147.32.84.191", "147.32.84.192")) | 
         [.network.five_tuple.src_ip, .detection.scores.fast_detector, .detection.scores.ml_detector, .detection.scores.final_score] | @csv'
```

## 🤔 DECISIÓN CLAVE: ¿Qué Guardar?

### OPCIÓN A: Solo Interesantes (ACTUAL)
- Score >= 0.70 OR divergence >= 0.30
- **2-3% del total** (~15K de 492K en Neris)
- **75 MB** logs para Neris
- ✅ **RECOMENDADO** para producción

### OPCIÓN B: Todo para F1-Score
- Flag `testing: true` en config
- **100% eventos** (492K en Neris)
- **2.5 GB** logs para Neris
- ⚠️ Solo para validation runs

### MI RECOMENDACIÓN:
```json
{
  "mode": "production",  // Cambiar a "testing" solo para F1-score
  "min_score_to_log": 0.70,
  "min_divergence_to_log": 0.30,
  "save_protobuf_artifacts": false,  // OFF para testing rápido
  "save_json_artifacts": false       // JSON ya está en .jsonl
}
```

## 📊 RESULTADOS ESPERADOS

### SmallFlows (1.2K eventos)
- RAG events: **~80-100**
- Logs: **~500 KB**
- Tiempo: **<1 minuto**

### Neris (492K eventos)
- RAG events: **~10,000-15,000**
- Botnet IPs en RAG: **~500-1,000**
- Logs: **~75 MB** (sin artifacts)
- Tiempo: **30-45 minutos**

## ⚠️ TROUBLESHOOTING

### Si no aparecen logs RAG:
```bash
# 1. Ver logs detector
tail -f /vagrant/logs/ml-detector/ml-detector.log | grep RAG

# 2. Verificar permisos
ls -la /vagrant/logs/rag/

# 3. Recompilar si necesario
make detector

# 4. Ver estadísticas en destructor
# Al cerrar el detector, debería mostrar:
# 📊 RAG Statistics: ... events logged
```

### Si Makefile roto:
```bash
# Ver los targets disponibles
make help

# Si falta algo, añadir manualmente targets RAG del documento principal
```

## 🎯 OBJETIVO DAY 15
✅ Validar RAGLogger funciona  
✅ Ejecutar Neris completo  
✅ Obtener primeros F1-scores  
✅ Decidir estrategia logging definitiva  
✅ Preparar Day 16 (RAG ingestion)

---

**Quick Start Tomorrow:**
```bash
make rag-init && make rag-clean && make test-replay-small && make rag-analyze
```

**LISTO PARA DAY 15** 🚀