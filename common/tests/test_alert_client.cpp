#include <gtest/gtest.h>
#include <nlohmann/json.hpp>
#include "alert_client.hpp"
#include <chrono>

using json = nlohmann::json;

static json make_config(bool global_enabled = true) {
    std::string en = global_enabled ? "true" : "false";
    std::string s = R"({"alerting":{"enabled":)" + en + R"(,"providers":[{"type":"discord","enabled":true,"webhook_url":"https://discord.com/api/webhooks/TEST/TEST"},{"type":"telegram","enabled":false,"bot_token":"BOT","chat_id":"CID"}]}})";
    return json::parse(s);
}

static argus::SosPayload make_payload() {
    return argus::SosPayload{
        .node            = "defender-edge-01",
        .component       = "etcd-server",
        .event           = "AUTONOMOUS_STATE_ACTIVATED",
        .pipeline_status = "6/6 RUNNING"
    };
}

TEST(AlertClient, ParsesConfigCorrectly) {
    argus::AlertClient client(make_config());
    EXPECT_TRUE(client.is_enabled());
    EXPECT_EQ(client.provider_count(), 2);
    EXPECT_EQ(client.enabled_provider_count(), 1);
}

TEST(AlertClient, GlobalDisabledSkipsAll) {
    argus::AlertClient client(make_config(false));
    EXPECT_FALSE(client.is_enabled());
    EXPECT_NO_THROW(client.send_sos(make_payload()));
}

TEST(AlertClient, DisabledProviderIsSkipped) {
    argus::AlertClient client(make_config());
    EXPECT_EQ(client.enabled_provider_count(), 1);
}

TEST(AlertClient, DiscordPayloadFormat) {
    auto j = argus::AlertClient::build_discord_payload(make_payload());
    ASSERT_TRUE(j.contains("content"));
    std::string c = j["content"];
    EXPECT_NE(c.find("defender-edge-01"), std::string::npos);
    EXPECT_NE(c.find("AUTONOMOUS_STATE_ACTIVATED"), std::string::npos);
    EXPECT_NE(c.find("6/6 RUNNING"), std::string::npos);
}

TEST(AlertClient, TelegramPayloadFormat) {
    auto j = argus::AlertClient::build_telegram_payload("CHAT_ID", make_payload());
    ASSERT_TRUE(j.contains("chat_id"));
    ASSERT_TRUE(j.contains("text"));
    EXPECT_EQ(j["chat_id"], "CHAT_ID");
    std::string t = j["text"];
    EXPECT_NE(t.find("defender-edge-01"), std::string::npos);
    EXPECT_NE(t.find("AUTONOMOUS_STATE_ACTIVATED"), std::string::npos);
}

TEST(AlertClient, SendSosReturnsQuickly) {
    std::string s = R"({"alerting":{"enabled":true,"providers":[{"type":"discord","enabled":true,"webhook_url":"https://127.0.0.1:19999/none"}]}})";
    argus::AlertClient client(json::parse(s));
    auto t0 = std::chrono::steady_clock::now();
    client.send_sos(make_payload());
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - t0).count();
    EXPECT_LT(ms, 50) << "send_sos bloqueo " << ms << "ms";
}


// ── Test 7: node y component distintos aparecen en Discord ───────────────────

TEST(AlertClient, PayloadIncludesNodeAndComponent) {
    argus::SosPayload pl{
        .node            = "rpi5-hospital-01",
        .component       = "firewall-acl-agent",
        .event           = "AUTO_ISOLATE_TRIGGERED",
        .pipeline_status = "src_ip=10.0.0.99"
    };
    auto jd = argus::AlertClient::build_discord_payload(pl);
    std::string c = jd["content"];
    EXPECT_NE(c.find("rpi5-hospital-01"), std::string::npos);
    EXPECT_NE(c.find("firewall-acl-agent"), std::string::npos);
    EXPECT_NE(c.find("AUTO_ISOLATE_TRIGGERED"), std::string::npos);
    EXPECT_NE(c.find("src_ip=10.0.0.99"), std::string::npos);

    auto jt = argus::AlertClient::build_telegram_payload("CID", pl);
    std::string t = jt["text"];
    EXPECT_NE(t.find("rpi5-hospital-01"), std::string::npos);
    EXPECT_NE(t.find("firewall-acl-agent"), std::string::npos);
}

// ── Test 8: AlertClient cargado desde JSON en disco ───────────────────────────

TEST(AlertClient, LoadFromFileDisabledReturnsNoOp) {
    // Simula lo que hace etcd-server: parsear JSON desde disco
    std::string json_str = R"({"alerting":{"enabled":false,"providers":[]}})";
    auto cfg = nlohmann::json::parse(json_str);
    argus::AlertClient client(cfg);
    EXPECT_FALSE(client.is_enabled());
    EXPECT_EQ(client.provider_count(), 0);
    EXPECT_NO_THROW(client.send_sos({
        .node = "node-test",
        .component = "etcd-server",
        .event = "AUTONOMOUS_STATE_ACTIVATED",
        .pipeline_status = "vault_unreachable"
    }));
}

// ── Test 9: provider_count y enabled_provider_count son independientes ────────

TEST(AlertClient, ProviderCountsAreIndependent) {
    auto cfg = nlohmann::json::parse(R"({
        "alerting": {
            "enabled": true,
            "providers": [
                {"type":"discord",  "enabled":true,  "webhook_url":"https://x.com"},
                {"type":"telegram", "enabled":true,  "bot_token":"T", "chat_id":"C"},
                {"type":"discord",  "enabled":false, "webhook_url":"https://y.com"}
            ]
        }
    })");
    argus::AlertClient client(cfg);
    EXPECT_EQ(client.provider_count(), 3);
    EXPECT_EQ(client.enabled_provider_count(), 2);
}

// ── Test 10: send_sos con todos providers desactivados → retorno inmediato ────

TEST(AlertClient, AllProvidersDisabledReturnsImmediately) {
    auto cfg = nlohmann::json::parse(R"({
        "alerting": {
            "enabled": true,
            "providers": [
                {"type":"discord",  "enabled":false, "webhook_url":"https://x.com"},
                {"type":"telegram", "enabled":false, "bot_token":"T", "chat_id":"C"}
            ]
        }
    })");
    argus::AlertClient client(cfg);
    EXPECT_TRUE(client.is_enabled());
    EXPECT_EQ(client.enabled_provider_count(), 0);
    auto t0 = std::chrono::steady_clock::now();
    client.send_sos({
        .node = "n", .component = "c",
        .event = "E", .pipeline_status = "p"
    });
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - t0).count();
    EXPECT_LT(ms, 5) << "deberia retornar instantaneamente, bloqueo=" << ms << "ms";
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
