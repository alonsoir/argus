#include <gtest/gtest.h>

// Test básico para verificar que GTest funciona
TEST(BasicTest, Configuration) {
    EXPECT_EQ(1 + 1, 2);
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}