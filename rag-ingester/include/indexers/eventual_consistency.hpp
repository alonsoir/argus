#pragma once

#include <string>

namespace rag_ingester {

struct CommitResult {
    int successful_commits{0};
    int failed_commits{0};
    
    bool any_success() const { return successful_commits > 0; }
    bool all_success() const { return failed_commits == 0; }
};

} // namespace rag_ingester
