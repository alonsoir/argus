# Day 8 Postmortem - Dual-NIC Validation

## Timeline

**09:00** - Inicio: libbpf 1.1.2, iface_configs no carga
**10:30** - Diagnóstico: Struct map loading bug confirmado
**11:00** - Solución: Upgrade a libbpf 1.4.6
**12:00** - Validación: Mapa carga correctamente
**14:00** - Auditoría: Código eBPF → userspace
**15:30** - Breakthrough: [DUAL-NIC] logs confirman metadata flow
**16:00** - VALIDADO: Phase 1 Day 8 complete

## Root Cause

libbpf 1.1.2 tenía bug con BTF encoding de structs en mapas.
iface_configs (hash map con struct interface_config values) fallaba al cargar.

## Evidence
```bash
# Antes (libbpf 1.1.2)
bpftool map list | grep iface  # → (vacío)

# Después (libbpf 1.4.6)
bpftool map list | grep iface  # → 7: hash name iface_configs
bpftool map dump name iface_configs  # → {ifindex:3, mode:1, is_wan:1}
```

## Lessons Learned

1. **eBPF versioning matters** - Minor libbpf versions have critical bugs
2. **Systematic debugging wins** - Auditoría completa reveló la verdad
3. **Logs are gold** - [DUAL-NIC] debug logs salvaron el día
4. **Via Appia Quality** - No asumir, validar con evidencia

## Next Steps

Day 9: Gateway mode con MAWI dataset
