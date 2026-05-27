# 🛡️ ML Defender - Troubleshooting Guide

Guía completa de resolución de problemas para ML Defender Platform con RAG + 4 detectores ML.

---

## 🔍 Índice

- [Build Issues](#build-issues)
- [Runtime Issues](#runtime-issues)
- [eBPF/XDP Issues](#ebpfxdp-issues)
- [ZMQ Communication Issues](#zmq-communication-issues)
- [ML Detector Issues](#ml-detector-issues)
- [RAG System Issues](#rag-system-issues)
- [Vagrant/VM Issues](#vagrantvm-issues)
- [Debug Tools](#debug-tools)
- [Emergency Recovery](#emergency-recovery)

---

## Build Issues

### ❌ Error: `libbpf-dev` not found

**Síntoma:**
```
E: Package 'libbpf-dev' has no installation candidate
```

**Solución:**
```bash
# Dentro de la VM
sudo apt-get update
sudo apt-get install -y libbpf-dev

# Verificar instalación
dpkg -l | grep libbpf
```

---

### ❌ Error: `llama_integration_real.cpp` compilation fails

**Síntoma:**
```
error: ‘llama_kv_cache_clear’ was not declared in this scope
```

**Causa:** Función no disponible en nuestra versión de llama.cpp.

**Solución:** Usar workaround implementado:
```cpp
// En llama_integration_real.cpp, usar:
void clear_kv_cache() {
    llama_batch batch = llama_batch_init(1, 0, 1);
    batch.n_tokens = 0;
    llama_decode(ctx, batch);
    llama_batch_free(batch);
}
```

---

### ❌ Error: Missing nlohmann/json

**Síntoma:**
```
fatal error: nlohmann/json.hpp: No such file or directory
```

**Solución:**
```bash
sudo apt-get install -y nlohmann-json3-dev
```

---

### ❌ Error: Protobuf compilation fails

**Síntoma:**
```
protoc: command not found
```

**Solución:**
```bash
sudo apt-get install -y \
    protobuf-compiler \
    libprotobuf-dev \
    libprotobuf32

# Verificar
protoc --version  # Debe mostrar: libprotoc 3.21.12
```

---

## Runtime Issues

### ❌ Error: "KV Cache Inconsistency" en RAG System

**Síntoma:**
```
init: the tokens of sequence 0 in the input batch have inconsistent sequence positions:
 - the last position stored in the memory module of the context (i.e. the KV cache) for sequence 0 is X = 213
 - the tokens for sequence 0 in the input batch have a starting position of Y = 0
```

**Estado:** 🔄 WORKAROUND IMPLEMENTADO

**Solución:**
```bash
# Reiniciar servicio RAG (workaround temporal)
sudo systemctl restart ml-defender-rag

# Verificar que el workaround está en el código
grep "clear_kv_cache" /opt/rag-security/src/llama_integration_real.cpp
```

---

### ❌ Error: ML Detector no recibe datos

**Síntoma:** No hay inferencias en los logs del ml-detector.

**Diagnóstico:**
```bash
# Verificar conectividad ZMQ
sudo netstat -tlnp | grep 5571
sudo netstat -tlnp | grep 5572

# Verificar que sniffer está enviando
sudo tail -f /var/log/ml-defender/sniffer-stdout.log | grep "ZMQ"

# Verificar que detector está escuchando
sudo tail -f /var/log/ml-defender/detector-stdout.log | grep "Received"
```

**Solución:**
```bash
# Reiniciar servicios en orden
sudo systemctl restart ml-defender-sniffer
sudo systemctl restart ml-defender-detector

# Verificar configuración de endpoints
grep -A 5 "zmq" /etc/sniffer/sniffer.json
grep -A 5 "zmq" /etc/ml-detector/ml_detector_config.json
```

---

### ❌ Error: Alto uso de memoria

**Síntoma:** Uso de memoria >4 GB en Raspberry Pi.

**Diagnóstico:**
```bash
# Identificar componente que usa más memoria
ps aux --sort=-%mem | grep -E "(sniffer|ml-detector|rag)" | head -5

# Monitorear crecimiento
watch -n 5 'ps aux | grep -E "(sniffer|ml-detector|rag)" | grep -v grep'
```

**Soluciones:**

1. **Reducir contexto RAG:**
```json
// En /etc/rag-security/system_config.json
{
  "llama": {
    "context_size": 512  // Reducir de 1024
  }
}
```

2. **Reiniciar servicio RAG:**
```bash
sudo systemctl restart ml-defender-rag
```

3. **Verificar memory leaks:**
```bash
# Ejecutar health check
/usr/local/bin/ml-defender-health-check
```

---

### ❌ Error: RAG System no responde

**Síntoma:** Comandos `rag ask_llm` no retornan respuesta.

**Diagnóstico:**
```bash
# Verificar que el servicio está activo
sudo systemctl status ml-defender-rag

# Verificar logs de error
sudo tail -f /var/log/ml-defender/rag-stderr.log

# Probar conectividad al puerto
telnet localhost 9090
```

**Soluciones:**

1. **Verificar modelo LLAMA:**
```bash
# Verificar que el modelo existe
ls -lh /opt/rag-security/models/tinyllama-1.1b-chat-v1.0.Q4_0.gguf

# Verificar permisos
sudo chmod 644 /opt/rag-security/models/*.gguf
```

2. **Reiniciar servicio:**
```bash
sudo systemctl restart ml-defender-rag
```

3. **Ejecutar en modo debug:**
```bash
cd /opt/rag-security/build
./rag-security --config /etc/rag-security/system_config.json --debug
```

---

## eBPF/XDP Issues

### ❌ Error: "Failed to load eBPF program"

**Síntoma:**
```
[ERROR] Failed to load eBPF object from sniffer.bpf.o
```

**Diagnóstico:**
```bash
# Verificar kernel support
ls -l /sys/kernel/btf/vmlinux

# Verificar que el archivo existe
ls -lh /usr/local/lib/sniffer/sniffer.bpf.o

# Verificar permisos
sudo chmod 644 /usr/local/lib/sniffer/sniffer.bpf.o
```

**Soluciones:**

1. **Recompilar programa eBPF:**
```bash
cd /opt/ml-defender/sniffer/build
make clean && make -j$(nproc)
sudo cp sniffer.bpf.o /usr/local/lib/sniffer/
```

2. **Verificar versión del kernel:**
```bash
uname -r  # Debe ser >= 6.1
```

---

### ❌ Error: No se capturan paquetes

**Síntoma:** Sniffer arranca pero no procesa eventos.

**Diagnóstico:**
```bash
# Verificar programa eBPF cargado
sudo bpftool prog show | grep sniffer

# Verificar adjunto a interfaz
ip link show eth0 | grep xdp

# Generar tráfico de prueba
ping -c 5 8.8.8.8

# Ver logs del sniffer
sudo tail -f /var/log/ml-defender/sniffer-stdout.log
```

**Soluciones:**

1. **Verificar interfaz:**
```json
// En /etc/sniffer/sniffer.json
{
  "interface": "eth0"  // ← Debe coincidir con tu interfaz
}
```

2. **Desactivar filtros temporalmente:**
```json
{
  "filter": {
    "mode": "passthrough"
  }
}
```

---

## ZMQ Communication Issues

### ❌ Error: "Address already in use"

**Síntoma:**
```
Address already in use (zmq_bind)
```

**Solución:**
```bash
# Ver qué está usando los puertos
sudo netstat -tlnp | grep -E "(5571|5572|9090)"

# Matar procesos anteriores
sudo pkill -f "sniffer\|ml-detector\|rag-security"

# Reiniciar servicios
sudo systemctl restart ml-defender-sniffer
sudo systemctl restart ml-defender-detector
sudo systemctl restart ml-defender-rag
```

---

### ❌ Error: Detector no recibe mensajes

**Síntoma:** Sniffer envía pero detector no procesa.

**Verificación de endpoints:**
```bash
# Sniffer debe enviar a 5571
grep "output_endpoint" /etc/sniffer/sniffer.json

# Detector debe recibir de 5571 y enviar a 5572  
grep -A 3 "zmq" /etc/ml-detector/ml_detector_config.json
```

**Solución:**
```json
// En /etc/sniffer/sniffer.json
{
  "zmq": {
    "output_endpoint": "tcp://127.0.0.1:5571"
  }
}

// En /etc/ml-detector/ml_detector_config.json
{
  "zmq": {
    "input_endpoint": "tcp://127.0.0.1:5571",
    "output_endpoint": "tcp://127.0.0.1:5572"
  }
}
```

---

## ML Detector Issues

### ❌ Error: Modelos no cargan

**Síntoma:**
```
[ERROR] Failed to load ML model
```

**Solución:**
```bash
# Verificar que los modelos existen
ls -lh /opt/ml-defender/models/

# Verificar configuración
grep "model_path" /etc/ml-detector/ml_detector_config.json

# Verificar permisos
sudo chmod 644 /opt/ml-defender/models/*.bin
```

---

### ❌ Error: Baja precisión en detecciones

**Síntoma:** Falsos positivos o negativos altos.

**Solución:** Ajustar thresholds en configuración:
```json
{
  "ml_defender": {
    "thresholds": {
      "ddos": 0.90,        // Aumentar para menos falsos positivos
      "ransomware": 0.95,  // Aumentar para ransomware
      "traffic": 0.75,     // Disminuir para más sensibilidad
      "internal": 0.80     // Ajustar según red interna
    }
  }
}
```

---

## RAG System Issues

### ❌ Error: "LLAMA model failed to load"

**Síntoma:**
```
[ERROR] Failed to load LLAMA model
```

**Diagnóstico:**
```bash
# Verificar que el modelo existe
ls -lh /opt/rag-security/models/tinyllama-1.1b-chat-v1.0.Q4_0.gguf

# Verificar tamaño (debe ser ~1.5GB)
du -h /opt/rag-security/models/tinyllama-1.1b-chat-v1.0.Q4_0.gguf

# Verificar configuración
grep "model_path" /etc/rag-security/system_config.json
```

**Solución:**
```bash
# Re-descargar modelo si está corrupto
cd /opt/rag-security/models
rm tinyllama-1.1b-chat-v1.0.Q4_0.gguf
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_0.gguf
```

---

### ❌ Error: Respuestas incoherentes del LLAMA

**Síntoma:** El modelo genera respuestas sin sentido.

**Solución:** Mejorar el prompt de sistema:
```cpp
// En llama_integration_real.cpp, verificar:
std::string enhanced_prompt =
    "<|system|>\n"
    "Eres un asistente especializado en seguridad informática...\n"
    "<|user|>\n" + prompt + "\n"
    "<|assistant|>\n";
```

---

### ❌ Error: Timeout en consultas RAG

**Síntoma:** Las consultas tardan demasiado o timeout.

**Solución:**
```json
// En /etc/rag-security/system_config.json
{
  "llama": {
    "max_tokens": 128,  // Reducir longitud máxima
    "temperature": 0.3  // Reducir para respuestas más concisas
  },
  "security": {
    "request_timeout_sec": 60  // Aumentar timeout
  }
}
```

---

## Vagrant/VM Issues

### ❌ Error: VM no arranca

**Síntoma:**
```
VBoxManage: error: Failed to create the host-only adapter
```

**Solución:**
```bash
# En host, recrear VM
cd /vagrant
vagrant destroy -f
vagrant up

# Verificar recursos asignados
# Mínimo: 4GB RAM, 4 CPUs, 10GB disco
```

---

### ❌ Error: Shared folder no montado

**Síntoma:**
```
/vagrant: No such file or directory
```

**Solución:**
```bash
# Reinstalar Guest Additions
vagrant plugin install vagrant-vbguest
vagrant reload

# Verificar
vagrant ssh -c "ls /vagrant"
```

---

## Debug Tools

### Health Check Integral

```bash
# Ejecutar health check completo
/usr/local/bin/ml-defender-health-check

# Verificar estado individual de componentes
sudo systemctl status ml-defender-sniffer
sudo systemctl status ml-defender-detector  
sudo systemctl status ml-defender-rag

# Ver logs en tiempo real
sudo journalctl -u ml-defender-sniffer -f
sudo tail -f /var/log/ml-defender/rag-stdout.log
```

### Monitoreo de Rendimiento

```bash
# Ver uso de recursos
/usr/local/bin/ml-defender-monitor

# Ver procesos específicos
ps aux | grep -E "(sniffer|ml-detector|rag)" | grep -v grep

# Ver memoria detallada
cat /proc/$(pgrep rag-security)/status | grep -E "VmSize|VmRSS"
```

### Verificación BPF/eBPF

```bash
# Ver programas eBPF cargados
sudo bpftool prog show | grep sniffer

# Ver maps eBPF
sudo bpftool map list | grep sniffer

# Ver estadísticas
sudo bpftool prog show id $(sudo bpftool prog show | grep sniffer | head -1 | awk '{print $1}')
```

### Test de Comunicación

```bash
# Test ZMQ endpoints
nc -zv 127.0.0.1 5571
nc -zv 127.0.0.1 5572  
nc -zv 127.0.0.1 9090

# Test RAG system interactivo
telnet localhost 9090
# Luego ejecutar: rag show_config
```

---

## Emergency Recovery

### Reset Completo del Sistema

```bash
# Parar todos los servicios
sudo systemctl stop ml-defender-rag
sudo systemctl stop ml-defender-detector
sudo systemctl stop ml-defender-sniffer

# Limpiar procesos residuales
sudo pkill -f "sniffer\|ml-detector\|rag-security"

# Limpiar logs
sudo rm -f /var/log/ml-defender/*.log

# Reiniciar servicios en orden
sudo systemctl start ml-defender-sniffer
sudo systemctl start ml-defender-detector
sudo systemctl start ml-defender-rag

# Verificar estado
/usr/local/bin/ml-defender-health-check
```

### Nuclear Option: Reinstalación Completa

```bash
# En host
cd /vagrant
vagrant destroy -f
vagrant up

# Reinstalar ML Defender
/vagrant/scripts/install-ml-defender.sh
```

---

## Common Patterns & Solutions

### Pattern: "Funcionaba y dejó de funcionar"

**Checklist:**
1. ✅ Verificar recursos: `free -h && df -h`
2. ✅ Reiniciar servicios: `sudo systemctl restart ml-defender-*`
3. ✅ Verificar logs: `sudo journalctl -u ml-defender-rag --since "1 hour ago"`
4. ✅ Health check: `/usr/local/bin/ml-defender-health-check`

### Pattern: Alta latencia en RAG

**Soluciones:**
1. Reducir `max_tokens` en configuración RAG
2. Reducir `context_size` si no se necesita contexto largo
3. Verificar que no hay múltiples instancias ejecutándose

### Pattern: Falsos positivos en ML

**Ajustes recomendados:**
```json
{
  "thresholds": {
    "ddos": 0.90,
    "ransomware": 0.95, 
    "traffic": 0.85,
    "internal": 0.88
  }
}
```

---

## Getting Help

Si los problemas persisten:

1. **Recolectar información de debug:**
```bash
cd /opt/ml-defender
./scripts/collect_debug_info.sh > ml_defender_debug_$(date +%Y%m%d).txt
```

2. **Verificar documentación:**
- `README.md` - Visión general del sistema
- `ARCHITECTURE.md` - Diseño arquitectónico
- `DEPLOYMENT.md` - Guía de despliegue
- `AUTHORS.md` - Equipo de desarrollo

3. **Reportar issues:**
- Incluir salida del health check
- Incluir logs relevantes
- Describir pasos para reproducir

---

<div align="center">

**🛡️ ML Defender Troubleshooting Guide 🛡️**

*Sistema RAG + 4 Detectores ML • Actualizado: Noviembre 20, 2025*

**¡Base sólida establecida! Próximo objetivo: Estabilidad 100% 🚀**

</div>