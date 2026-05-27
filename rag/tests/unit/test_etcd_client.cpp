#include <gtest/gtest.h>
#include "rag/etcd_client.hpp"
#include <thread>
#include <chrono>

class EtcdClientTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Usar endpoint de etcd local para testing
        client = std::make_unique<Rag::EtcdClient>("http://localhost:2379");
    }

    void TearDown() override {
        client.reset();
    }

    std::unique_ptr<Rag::EtcdClient> client;
};

TEST_F(EtcdClientTest, BasicPutGet) {
    bool putResult = client->put("/test/key1", "value1");
    EXPECT_TRUE(putResult);

    auto [success, value] = client->get("/test/key1");
    EXPECT_TRUE(success);
    EXPECT_EQ(value, "value1");
}

TEST_F(EtcdClientTest, GetNonExistentKey) {
    auto [success, value] = client->get("/test/nonexistent");
    EXPECT_FALSE(success);
    EXPECT_TRUE(value.empty());
}

TEST_F(EtcdClientTest, ListKeysWithPrefix) {
    client->put("/test/list/key1", "value1");
    client->put("/test/list/key2", "value2");
    client->put("/test/other/key3", "value3");

    auto keys = client->listKeys("/test/list/");
    EXPECT_GE(keys.size(), 2);

    bool foundKey1 = false, foundKey2 = false;
    for (const auto& key : keys) {
        if (key == "/test/list/key1") foundKey1 = true;
        if (key == "/test/list/key2") foundKey2 = true;
    }

    EXPECT_TRUE(foundKey1);
    EXPECT_TRUE(foundKey2);
}