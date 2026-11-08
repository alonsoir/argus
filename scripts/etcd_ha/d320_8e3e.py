#!/usr/bin/env python3
# [ETCD-CLIENTE-KV-D320] DEBT-FW-MANIFIESTO-PROTEGIDOS-001 (ADR-060, F-I), paso 8e.3e.
# Borra de etcd-client todo lo que pide /kv/... (rutas que el etcd-server no tiene: siempre 404):
#   set, get, del, list_keys, y los 6 que se apoyan en ellos (decisión de Alonso DAY320, tras medir que borrar solo
#   los 4 rompe la compilación de la librería): save_config_master, save_config_active, get_config_master,
#   get_config_active, get_component_config y rollback_config.
# Medido DAY320 con git grep (por palabra): nadie los llama fuera de la librería (sniffer, ml-detector, firewall,
# tools, tests) y ningún envoltorio los expone. Se queda put_config (va por put_config_impl, sí funciona) y el
# mutex_ (lo usan otros métodos). El título "Config Management" de la cabecera pierde "(Master + Active ...)".
#
# Uso, desde la raíz del repo:
#   python3 -I scripts/etcd_ha/d320_8e3e.py --check
#   python3 -I scripts/etcd_ha/d320_8e3e.py --apply
# Todo o nada: comprueba el sha256 de cada fichero antes de escribir ninguno. Idempotente: si los dos ficheros ya
# tienen el sha256 de después, no toca nada. Salidas: 0 aplicable/aplicado/ya aplicado, 1 no aplicable, 2 uso.
import hashlib, json, os, sys, tempfile

CAMBIOS = json.loads(r'''[
 {
  "ruta": "etcd-client/include/etcd_client/etcd_client.hpp",
  "antes": "e1831c1b810983d042618ed35365f1e87a5024acc5dea8ce001687fdf09c3552",
  "despues": "ef5d7bdd33ed314f53f7fd4da545dd8407d53bfd83619680507ed8fce67efc15",
  "bloques": [
   {
    "viejo": "    // ========================================================================\n    // Key-Value Operations\n    // (encryption/compression applied automatically based on config)\n    // ========================================================================\n\n    bool set(const std::string& key, const std::string& value);\n    std::string get(const std::string& key);\n    bool del(const std::string& key);\n    std::vector<std::string> list_keys(const std::string& prefix = \"\");\n\n",
    "nuevo": ""
   },
   {
    "viejo": "    // ========================================================================\n    // Config Management (Master + Active copies for rollback)\n    // ========================================================================\n\n    // Save master config (immutable, original)\n    bool save_config_master(const std::string& config_json);\n\n    // Save active config (mutable, working copy)\n    bool save_config_active(const std::string& config_json);\n\n    // Get master config\n    std::string get_config_master();\n\n    // Get active config\n    std::string get_config_active();\n\n    std::string get_component_config(const std::string& component_name);\n\n",
    "nuevo": "    // ========================================================================\n    // Config Management\n    // ========================================================================\n\n"
   },
   {
    "viejo": "\n    // Rollback active to master\n    bool rollback_config();\n",
    "nuevo": ""
   }
  ]
 },
 {
  "ruta": "etcd-client/src/etcd_client.cpp",
  "antes": "3873467cd8664e857b0720bb0b9176e9d30ad68fb671f75cd9269e0402564ef3",
  "despues": "39cf298b62e7be8e07c312a91409a18b5e606e4ef7702e7ed9fe37666199d2bb",
  "bloques": [
   {
    "viejo": "// Key-value operations\nbool EtcdClient::set(const std::string& key, const std::string& value) {\n    std::lock_guard<std::mutex> lock(pImpl->mutex_);\n\n    try {\n        // Process data (compress + encrypt)\n        std::string processed_value = value;\n\n        // Build JSON payload\n        json payload = {\n            {\"key\", key},\n            {\"value\", processed_value},\n            {\"original_size\", value.size()}\n        };\n\n        // Send to etcd-server\n        auto response = pImpl->transporte_.peticion(\"POST\", \"/kv/set\", payload.dump());\n\n        if (response.exito) {\n            std::cout << \"✅ Key set: \" << key << std::endl;\n            return true;\n        }\n\n        std::cerr << \"❌ Failed to set key: \" << key << std::endl;\n        return false;\n\n    } catch (const std::exception& e) {\n        std::cerr << \"❌ Exception in set(): \" << e.what() << std::endl;\n        return false;\n    }\n}\n\nstd::string EtcdClient::get(const std::string& key) {\n    std::lock_guard<std::mutex> lock(pImpl->mutex_);\n\n    try {\n        // Request from etcd-server\n        auto response = pImpl->transporte_.peticion(\"GET\", \"/kv/get?key=\" + key);\n\n        if (!response.exito) {\n            std::cerr << \"❌ Failed to get key: \" << key << std::endl;\n            return \"\";\n        }\n\n        // Parse response\n        json j = json::parse(response.body);\n        std::string value = j.value(\"value\", \"\");\n        // original_size = j.value(\"original_size\", 0);\n\n        // Process data (decrypt + decompress)\n        std::string processed_value = value;\n\n        std::cout << \"✅ Key retrieved: \" << key << std::endl;\n        return processed_value;\n\n    } catch (const std::exception& e) {\n        std::cerr << \"❌ Exception in get(): \" << e.what() << std::endl;\n        return \"\";\n    }\n}\n\nbool EtcdClient::del(const std::string& key) {\n    std::lock_guard<std::mutex> lock(pImpl->mutex_);\n\n    auto response = pImpl->transporte_.peticion(\"DELETE\", \"/kv/delete?key=\" + key);\n\n    if (response.exito) {\n        std::cout << \"✅ Key deleted: \" << key << std::endl;\n        return true;\n    }\n\n    std::cerr << \"❌ Failed to delete key: \" << key << std::endl;\n    return false;\n}\n\nstd::vector<std::string> EtcdClient::list_keys(const std::string& prefix) {\n    std::lock_guard<std::mutex> lock(pImpl->mutex_);\n\n    std::vector<std::string> keys;\n\n    try {\n        std::string path = \"/kv/list\";\n        if (!prefix.empty()) {\n            path += \"?prefix=\" + prefix;\n        }\n\n        auto response = pImpl->transporte_.peticion(\"GET\", path);\n\n        if (response.exito) {\n            json j = json::parse(response.body);\n            if (j.contains(\"keys\") && j[\"keys\"].is_array()) {\n                for (const auto& key : j[\"keys\"]) {\n                    keys.push_back(key.get<std::string>());\n                }\n            }\n        }\n\n    } catch (const std::exception& e) {\n        std::cerr << \"❌ Exception in list_keys(): \" << e.what() << std::endl;\n    }\n\n    return keys;\n}\n\n",
    "nuevo": ""
   },
   {
    "viejo": "bool EtcdClient::save_config_master(const std::string& config_json) {\n    return set(\"/config/\" + pImpl->config_.component_name + \"/master\", config_json);\n}\n\nbool EtcdClient::save_config_active(const std::string& config_json) {\n    return set(\"/config/\" + pImpl->config_.component_name + \"/active\", config_json);\n}\n\nstd::string EtcdClient::get_config_master() {\n    return get(\"/config/\" + pImpl->config_.component_name + \"/master\");\n}\n\nstd::string EtcdClient::get_config_active() {\n    return get(\"/config/\" + pImpl->config_.component_name + \"/active\");\n}\n\n",
    "nuevo": ""
   },
   {
    "viejo": "bool EtcdClient::rollback_config() {\n    std::string master = get_config_master();\n    if (master.empty()) {\n        std::cerr << \"❌ No master config found for rollback\" << std::endl;\n        return false;\n    }\n\n    bool result = save_config_active(master);\n    if (result) {\n        std::cout << \"✅ Config rolled back to master\" << std::endl;\n    }\n\n    return result;\n}\n\n",
    "nuevo": ""
   },
   {
    "viejo": "\nstd::string EtcdClient::get_component_config(const std::string& component_name) {\n    return get(\"/config/\" + component_name + \"/active\");\n}\n\n",
    "nuevo": ""
   }
  ]
 }
]''')

def sha(b): return hashlib.sha256(b).hexdigest()

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--check", "--apply"):
        print("uso: d320_8e3e.py --check|--apply  (desde la raíz del repo)", file=sys.stderr); return 2
    aplicar = sys.argv[1] == "--apply"
    estados, nuevos = [], {}
    for c in CAMBIOS:
        if not os.path.isfile(c["ruta"]):
            print(f"[NO APLICABLE] no existe {c['ruta']} (¿estás en la raíz del repo?)"); return 1
        b = open(c["ruta"], "rb").read(); s = sha(b)
        if s == c["despues"]:
            estados.append("hecho"); print(f"[YA APLICADO] {c['ruta']} sha256={s}"); continue
        if s != c["antes"]:
            print(f"[NO APLICABLE] {c['ruta']} sha256={s}\n  esperado antes  ={c['antes']}\n  esperado después={c['despues']}")
            return 1
        t = b.decode("utf-8"); borradas = 0
        for i, bl in enumerate(c["bloques"], 1):
            v = bl["viejo"]
            if t.count(v) != 1:
                print(f"[NO APLICABLE] {c['ruta']}: el bloque {i} aparece {t.count(v)} veces"); return 1
            t = t.replace(v, bl["nuevo"]); borradas += v.count(chr(10)) - bl["nuevo"].count(chr(10))
        n = t.encode("utf-8")
        if sha(n) != c["despues"]:
            print(f"[NO APLICABLE] {c['ruta']}: el resultado no da el sha256 esperado"); return 1
        estados.append("pendiente"); nuevos[c["ruta"]] = n
        print(f"[APLICABLE] {c['ruta']} {s[:16]} -> {c['despues'][:16]} ({len(c['bloques'])} bloques, {borradas} líneas menos)")
    if "hecho" in estados and "pendiente" in estados:
        print("[NO APLICABLE] estado mezclado: un fichero ya aplicado y otro no; no se toca nada"); return 1
    if not nuevos:
        print("[YA APLICADO] nada que hacer"); return 0
    if not aplicar:
        print("[CHECK] todo aplicable; nada escrito"); return 0
    for ruta, n in nuevos.items():
        modo = os.stat(ruta).st_mode & 0o7777
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ruta), prefix=".d320.")
        with os.fdopen(fd, "wb") as f: f.write(n); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, modo); os.replace(tmp, ruta)
    for c in CAMBIOS:
        s = sha(open(c["ruta"], "rb").read())
        if s != c["despues"]:
            print(f"[ERROR] {c['ruta']} quedó con sha256={s}"); return 1
        print(f"[APLICADO] {c['ruta']} sha256={s}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
