// ============================================================================
// TEST-PLUGIN-INVOKE-1 — invoke_all() smoke test
// Valida: PacketContext sintetico -> invoke_all() -> invocations > 0
// DAY 102 — ADR-012 PHASE 1b prerequisito para firewall-acl-agent
// ============================================================================
#include <cassert>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <cstdlib>

#include "plugin_loader/plugin_loader.hpp"
#include "plugin_loader/plugin_api.h"

static const char* TEST_CONFIG_JSON = R"json(
{
  "plugins": {
    "enabled": [
      {
        "name": "hello",
        "path": "/usr/lib/ml-defender/plugins/libplugin_hello.so",
        "active": true,
        "comment": "TEST-PLUGIN-INVOKE-1"
      }
    ]
  }
}
)json";

int main() {
    printf("[TEST-PLUGIN-INVOKE-1] inicio\n");

    const char* tmp_path = "/tmp/test_plugin_invoke_config.json";
    {
        std::ofstream f(tmp_path);
        assert(f.is_open() && "No se pudo crear config temporal");
        f << TEST_CONFIG_JSON;
    }
    printf("[TEST-PLUGIN-INVOKE-1] config temporal: %s\n", tmp_path);

    ml_defender::PluginLoader loader(tmp_path);
    loader.load_plugins();

    const size_t n = loader.loaded_count();
    printf("[TEST-PLUGIN-INVOKE-1] plugins cargados: %zu\n", n);
    assert(n >= 1 && "Se esperaba al menos 1 plugin cargado (hello)");

    PacketContext ctx{};
    static const uint8_t dummy_bytes[] = {0x45, 0x00, 0x00, 0x28};
    ctx.raw_bytes   = dummy_bytes;
    ctx.length      = sizeof(dummy_bytes);
    ctx.src_ip      = 0xC0A80001;
    ctx.dst_ip      = 0xC0A80002;
    ctx.src_port    = 12345;
    ctx.dst_port    = 80;
    ctx.protocol    = 6;
    ctx.features    = nullptr;
    ctx.alert_queue = nullptr;
    ctx.threat_hint = 0;

    loader.invoke_all(ctx);

    const auto& s = loader.stats();
    assert(s.empty() == false && "stats() vacio tras invoke_all()");

    const auto& hs = s[0];
    printf("[TEST-PLUGIN-INVOKE-1] plugin=%s invocations=%lu errors=%lu overruns=%lu\n",
           hs.name.c_str(), hs.invocations, hs.errors, hs.budget_overruns);

    assert(hs.invocations >= 1 && "FAIL: invocations == 0 tras invoke_all()");
    assert(hs.errors      == 0 && "FAIL: errors > 0");
    assert(hs.budget_overruns == 0 && "FAIL: budget_overruns > 0");

    loader.shutdown();

    printf("[TEST-PLUGIN-INVOKE-1] PASS\n");
    return 0;
}
