#include <gtest/gtest.h>

TEST(WhitelistTest, BasicAssertions) {
    EXPECT_TRUE(true);
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}