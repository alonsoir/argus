# Propuesta de Refactorización: sniffer.json v4.0

## 🎯 Problema Actual

El archivo `sniffer.json` v3.1 tiene **redundancia crítica** con la interfaz de red definida en 3 lugares:

```json
{
  "profiles": {
    "lab": {
      "capture_interface": "eth2",  // ← LUGAR 1
      ...
    }
  },
  "capture": {
    "interface": "eth0",             // ← LUGAR 2
    ...
  },
  "interface": "eth2"                // ← LUGAR 3
}
```

**Consecuencias:**
- Confusión sobre cuál tiene precedencia
- Errores de configuración (caso actual: eth2 vs eth0)
- Mantenimiento complicado
- Violación de DRY principle

---

## ✅ Diseño Propuesto v4.0

### Principio: "Una Fuente de Verdad"

```json
{
  "_header": "C++20 SNIFFER v4.0 - Refactored Config",
  "component": {
    "name": "cpp_evolutionary_sniffer",
    "version": "4.0.0"
  },
  
  // ============================================
  // ACTIVE PROFILE - ÚNICA FUENTE DE VERDAD
  // ============================================
  "active_profile": "lab",
  
  // ============================================
  // PROFILES - Configuraciones por entorno
  // ============================================
  "profiles": {
    "lab": {
      "description": "VirtualBox/Vagrant lab environment",
      "interface": "eth0",              // ← UNA SOLA VEZ
      "promiscuous_mode": true,
      "capture_mode": "ebpf_skb",       // Generic XDP mode
      "worker_threads": 2,
      "compression_level": 1,
      "environment": "development"
    },
    
    "cloud": {
      "description": "Cloud/VM production environment",
      "interface": "eth0",
      "promiscuous_mode": false,
      "capture_mode": "ebpf_skb",
      "worker_threads": 8,
      "compression_level": 3,
      "environment": "production"
    },
    
    "bare_metal": {
      "description": "High-performance bare metal",
      "interface": "eth0",
      "promiscuous_mode": true,
      "capture_mode": "xdp_native",     // Native XDP mode
      "worker_threads": 16,
      "compression_level": 1,
      "cpu_affinity_enabled": true,
      "environment": "production"
    }
  },
  
  // ============================================
  // CAPTURE - Solo configuración técnica
  // ============================================
  "capture": {
    // NO más "interface" aquí - se hereda del profile activo
    "xdp_flags": ["XDP_FLAGS_UPDATE_IF_NOEXIST"],
    "buffer_size": 65536,
    "min_packet_size": 20,
    "max_packet_size": 65536,
    "excluded_ports": [22],
    "included_protocols": ["tcp", "udp", "icmp"],
    
    "af_xdp": {
      "queue_id": 0,
      "frame_size": 2048,
      "ring_sizes": {
        "fill": 2048,
        "comp": 2048,
        "tx": 2048,
        "rx": 2048
      }
    }
  },
  
  // ... resto de configuración igual ...
}
```

---

## 🔧 Lógica de Carga (Pseudocódigo C++)

```cpp
class SnifferConfig {
    struct CaptureConfig {
        std::string interface;
        bool promiscuous_mode;
        std::string capture_mode;
        int worker_threads;
        // ... otros campos
    };
    
    CaptureConfig load() {
        // 1. Leer JSON
        json config = load_json("sniffer.json");
        
        // 2. Obtener perfil activo
        std::string active_profile = config["active_profile"];
        
        // 3. Cargar configuración del perfil
        json profile = config["profiles"][active_profile];
        
        // 4. Construir configuración UNIFICADA
        CaptureConfig result;
        result.interface = profile["interface"];          // ← UNA SOLA FUENTE
        result.promiscuous_mode = profile["promiscuous_mode"];
        result.capture_mode = profile["capture_mode"];
        result.worker_threads = profile["worker_threads"];
        
        // 5. Fusionar con configuración técnica de "capture"
        // (merge technical settings like buffer_size, excluded_ports, etc.)
        
        return result;
    }
};
```

---

## 🎯 Ventajas del Nuevo Diseño

### 1. **Claridad**
```diff
- "¿Cuál interfaz uso? ¿eth2 o eth0?"
+ "Leo active_profile → lab → interface: eth0"
```

### 2. **Mantenibilidad**
```diff
- Cambiar interfaz: tocar 3 lugares
+ Cambiar interfaz: tocar 1 lugar (profile.interface)
```

### 3. **Prevención de Errores**
```diff
- Posibilidad de contradicciones (eth2 vs eth0)
+ Imposible - solo hay una definición
```

### 4. **Simplicidad**
```json
// Cambiar de lab a cloud:
{
  "active_profile": "cloud"  // ← Solo cambiar esto
}
```

### 5. **Extensibilidad**
Agregar nuevos entornos es trivial:
```json
"profiles": {
  "edge_device": {
    "interface": "wlan0",
    "capture_mode": "ebpf_skb",
    ...
  }
}
```

---

## 📊 Comparación

| Aspecto | v3.1 (Actual) | v4.0 (Propuesto) |
|---------|---------------|------------------|
| **Interfaz definida en** | 3 lugares | 1 lugar |
| **Cambiar perfil** | Editar múltiples bloques | Cambiar 1 línea |
| **Riesgo de error** | Alto | Bajo |
| **Claridad** | Confuso | Explícito |
| **LOC** | ~520 | ~480 (-8%) |

---

## 🚀 Plan de Migración

### Fase 1: Análisis (1 hora)
- [ ] Mapear todas las referencias a `interface` en el código
- [ ] Identificar dónde se lee el JSON actual
- [ ] Documentar la lógica de precedencia actual

### Fase 2: Refactorización del JSON (30 min)
- [ ] Crear `sniffer_v4.json` con nuevo formato
- [ ] Validar con schema JSON
- [ ] Crear script de conversión `v3_to_v4.py`

### Fase 3: Refactorización del Código C++ (2-3 horas)
- [ ] Actualizar `Config` class para leer el nuevo formato
- [ ] Implementar lógica: active_profile → profile → merge con capture
- [ ] Eliminar código que lee las 3 ubicaciones antiguas

### Fase 4: Testing (1 hora)
- [ ] Unit tests: verificar que se lee correctamente
- [ ] Integration tests: sniffer + ml-detector funcionan
- [ ] Validar los 3 perfiles (lab, cloud, bare_metal)

### Fase 5: Documentación (30 min)
- [ ] Actualizar README con nuevo formato
- [ ] Crear ejemplos de perfiles
- [ ] Deprecation notice para v3.1

**Tiempo total estimado: ~5-6 horas**

---

## 🎯 Quick Win: Hack Temporal (5 minutos)

Si no tienes tiempo para la refactorización completa, al menos puedes:

```cpp
// En config_loader.cpp
std::string get_interface(const json& config) {
    // PRIORIDAD CLARA documentada:
    // 1. Si existe active_profile, usar profile[active_profile].interface
    // 2. Si no, usar capture.interface
    // 3. Si no, usar interface (root)
    
    std::string active_profile = config.value("profile", "");
    if (!active_profile.empty()) {
        return config["profiles"][active_profile]["capture_interface"];
    }
    if (config["capture"].contains("interface")) {
        return config["capture"]["interface"];
    }
    return config.value("interface", "eth0");
}
```

Y agregar un **WARNING** en los logs:
```
⚠️  WARNING: interface defined in multiple places
   Using: profiles.lab.capture_interface (eth0)
   Ignoring: capture.interface (eth0), root.interface (eth2)
   Consider upgrading to config v4.0 format
```

---

## 📝 Archivo de Migración Automática

```python
#!/usr/bin/env python3
"""
Convert sniffer.json v3.1 to v4.0 format
Usage: python3 migrate_config_v3_to_v4.py sniffer.json
"""

import json
import sys

def migrate(old_config):
    new_config = {
        "_header": "C++20 SNIFFER v4.0 - Refactored Config",
        "active_profile": old_config.get("profile", "lab"),
        "profiles": {}
    }
    
    # Migrar perfiles
    for profile_name, profile_data in old_config["profiles"].items():
        new_config["profiles"][profile_name] = {
            "description": f"{profile_name} environment",
            "interface": profile_data.get("capture_interface", "eth0"),
            "promiscuous_mode": profile_data.get("promiscuous_mode", True),
            "capture_mode": old_config["capture"].get("mode", "ebpf_skb"),
            "worker_threads": profile_data.get("worker_threads", 2),
            "compression_level": profile_data.get("compression_level", 1)
        }
    
    # Copiar capture (sin interface)
    new_config["capture"] = old_config["capture"].copy()
    if "interface" in new_config["capture"]:
        del new_config["capture"]["interface"]
    
    # Copiar el resto de secciones
    for key in ["buffers", "threading", "kernel_space", "user_space", 
                "feature_groups", "sniffer_time_windows", "network", 
                "zmq", "transport", "etcd", "processing", "auto_tuner", 
                "monitoring", "logging", "protobuf", "security", "backpressure"]:
        if key in old_config:
            new_config[key] = old_config[key]
    
    return new_config

if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        old = json.load(f)
    
    new = migrate(old)
    
    with open(sys.argv[1].replace(".json", "_v4.json"), "w") as f:
        json.dump(new, f, indent=2)
    
    print("✅ Migration complete: sniffer_v4.json created")
```

---

## 🎯 Conclusión

El diseño actual es **técnicamente funcional pero conceptualmente confuso**.

La refactorización propuesta:
- **Elimina redundancia** (3 → 1 definición)
- **Mejora claridad** (explicit > implicit)
- **Reduce errores** (single source of truth)
- **Facilita mantenimiento** (DRY principle)

**Recomendación**: Implementar en v4.0 cuando tengamos tiempo para hacerlo bien.

Por ahora, arreglemos el bug actual y continuemos con el testing de Level 2 DDoS features. 🚀