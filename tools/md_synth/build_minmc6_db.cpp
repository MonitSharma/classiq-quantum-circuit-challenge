#include <iostream>
#include <fstream>
#include <vector>
#include <unordered_set>
#include <kitty/dynamic_truth_table.hpp>
#include <kitty/spectral.hpp>
#include <kitty/print.hpp>
#include <mockturtle/algorithms/detail/minmc_xags.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/utils/index_list/index_list.hpp>

int main() {
  std::ofstream out("artifacts/post190_nist_catalog/nist_6cut_db.txt");
  std::unordered_set<uint64_t> seen;
  uint32_t count = 0;

  // 1. Embed all functions from minmc_xags (0..5 variables) into 6 variables
  for (uint32_t num_vars = 0; num_vars < mockturtle::detail::minmc_xags.size(); ++num_vars) {
    for (auto const& [cls, word, repr, expr] : mockturtle::detail::minmc_xags[num_vars]) {
      kitty::dynamic_truth_table tt(6u);
      // tile word across 64 bits
      uint64_t full_word = word;
      if (num_vars == 0) full_word = 0;
      else if (num_vars == 1) full_word = (word & 0x3) * 0x5555555555555555ULL;
      else if (num_vars == 2) full_word = (word & 0xf) * 0x1111111111111111ULL;
      else if (num_vars == 3) full_word = (word & 0xff) * 0x0101010101010101ULL;
      else if (num_vars == 4) full_word = (word & 0xffff) * 0x0001000100010001ULL;
      else if (num_vars == 5) full_word = (word & 0xffffffffULL) * 0x0000000100000001ULL;
      tt._bits[0] = full_word;

      std::vector<kitty::detail::spectral_operation> trans;
      auto canon_tt = kitty::hybrid_exact_spectral_canonization(tt, [&](auto const& ops) { trans = ops; });
      uint64_t canon_repr = *canon_tt.cbegin();

      if (seen.insert(canon_repr).second) {
        // Build xag_index_list with 6 primary inputs
        mockturtle::xag_index_list orig_il{ repr };
        // decode original xag
        mockturtle::xag_network xag;
        decode(xag, orig_il);
        // create 6-PI xag
        mockturtle::xag_network xag6;
        std::vector<mockturtle::xag_network::signal> pis;
        for (int i = 0; i < 6; ++i) pis.push_back(xag6.create_pi());
        // insert original xag into xag6
        std::vector<mockturtle::xag_network::signal> leaves;
        for (uint32_t i = 0; i < orig_il.num_pis(); ++i) leaves.push_back(pis[i]);
        mockturtle::insert(xag6, leaves.begin(), leaves.end(), orig_il, [&](auto const& f) {
          xag6.create_po(f);
        });

        mockturtle::xag_index_list il6;
        mockturtle::encode(il6, xag6);
        auto raw = il6.raw();
        out << kitty::to_hex(canon_tt) << " 0 0 ";
        for (size_t i = 0; i < raw.size(); ++i) {
          out << (i ? "," : "") << raw[i];
        }
        out << "\n";
        ++count;
      }
    }
  }

  std::cout << "Embedded " << count << " canonical 6-variable functions into nist_6cut_db.txt" << std::endl;
  return 0;
}
