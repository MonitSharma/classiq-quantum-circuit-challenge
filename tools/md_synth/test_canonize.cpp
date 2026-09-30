#include <iostream>
#include <chrono>
#include <vector>
#include <kitty/dynamic_truth_table.hpp>
#include <kitty/spectral.hpp>

int main() {
  std::cout << "Testing spectral canonization speed..." << std::endl;
  kitty::dynamic_truth_table tt(6u);
  auto start = std::chrono::high_resolution_clock::now();
  for (uint64_t i = 0; i < 20000; ++i) {
    tt._bits[0] = i * 0x9e3779b97f4a7c15ULL;
    std::vector<kitty::detail::spectral_operation> trans;
    auto repr = kitty::hybrid_exact_spectral_canonization(tt, [&](auto const& ops) { trans = ops; });
  }
  auto end = std::chrono::high_resolution_clock::now();
  auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
  std::cout << "20,000 canonizations took " << ms << " ms (" << (ms * 1000.0 / 20000) << " us per function)" << std::endl;
  return 0;
}
