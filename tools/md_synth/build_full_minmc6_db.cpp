#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <unordered_set>
#include <zlib.h>
#include <kitty/dynamic_truth_table.hpp>
#include <kitty/spectral.hpp>
#include <kitty/print.hpp>
#include <mockturtle/algorithms/detail/minmc_xags.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/utils/index_list/index_list.hpp>
#include <mockturtle/algorithms/simulation.hpp>

mockturtle::xag_network::signal parse_linear(
    mockturtle::xag_network& xag,
    const std::vector<mockturtle::xag_network::signal>& pis,
    const std::vector<mockturtle::xag_network::signal>& ands,
    const std::string& expr) {
  auto res = xag.get_constant(false);
  std::istringstream ss(expr);
  std::string term;
  while (std::getline(ss, term, '+')) {
    // trim whitespace
    while (!term.empty() && (term.front() == ' ' || term.front() == '(')) term.erase(term.begin());
    while (!term.empty() && (term.back() == ' ' || term.back() == ')')) term.pop_back();
    if (term.empty()) continue;
    if (term == "1") {
      res = xag.create_xor(res, xag.get_constant(true));
    } else if (term[0] == 'x') {
      int idx = std::stoi(term.substr(1)) - 1;
      if (idx >= 0 && idx < 6) res = xag.create_xor(res, pis[idx]);
    } else if (term[0] == 'a') {
      int idx = std::stoi(term.substr(1));
      if (idx >= 0 && idx < static_cast<int>(ands.size())) res = xag.create_xor(res, ands[idx]);
    }
  }
  return res;
}

int main(int argc, char** argv) {
  std::string out_path = argc > 1 ? argv[1] : "artifacts/post190_nist_catalog/nist_6cut_db.txt";
  int max_blocks = argc > 2 ? std::stoi(argv[2]) : 5000;
  std::ofstream out(out_path);
  std::unordered_set<uint64_t> seen;
  uint32_t count = 0;

  // 1. Embed all functions from minmc_xags (0..5 variables) into 6 variables
  for (uint32_t num_vars = 0; num_vars < mockturtle::detail::minmc_xags.size(); ++num_vars) {
    for (auto const& [cls, word, repr, expr] : mockturtle::detail::minmc_xags[num_vars]) {
      kitty::dynamic_truth_table tt(6u);
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
        mockturtle::xag_index_list orig_il{ repr };
        mockturtle::xag_network xag;
        decode(xag, orig_il);
        mockturtle::xag_network xag6;
        std::vector<mockturtle::xag_network::signal> pis;
        for (int i = 0; i < 6; ++i) pis.push_back(xag6.create_pi());
        std::vector<mockturtle::xag_network::signal> leaves;
        for (uint32_t i = 0; i < orig_il.num_pis(); ++i) leaves.push_back(pis[i]);
        mockturtle::insert(xag6, leaves.begin(), leaves.end(), orig_il, [&](auto const& f) {
          xag6.create_po(f);
        });

        mockturtle::xag_index_list il6;
        mockturtle::encode(il6, xag6);
        auto raw = il6.raw();
        out << kitty::to_hex(canon_tt) << " 0 0 ";
        for (size_t i = 0; i < raw.size(); ++i) out << (i ? "," : "") << raw[i];
        out << "\n";
        ++count;
      }
    }
  }
  std::cout << "Added " << count << " sub-6 functions." << std::endl;

  // 2. Add 6-input AND: x1x2x3x4x5x6
  {
    mockturtle::xag_network x6;
    std::vector<mockturtle::xag_network::signal> pis;
    for (int i = 0; i < 6; ++i) pis.push_back(x6.create_pi());
    auto g0 = x6.create_and(pis[0], pis[1]);
    auto g1 = x6.create_and(pis[2], pis[3]);
    auto g2 = x6.create_and(pis[4], pis[5]);
    auto g3 = x6.create_and(g0, g1);
    auto g4 = x6.create_and(g3, g2);
    x6.create_po(g4);
    kitty::dynamic_truth_table tt(6u);
    tt._bits[0] = 0x8000000000000000ULL;
    std::vector<kitty::detail::spectral_operation> trans;
    auto canon_tt = kitty::hybrid_exact_spectral_canonization(tt, [&](auto const& ops) { trans = ops; });
    uint64_t canon_repr = *canon_tt.cbegin();
    if (seen.insert(canon_repr).second) {
      mockturtle::xag_index_list il;
      mockturtle::encode(il, x6);
      auto raw = il.raw();
      out << kitty::to_hex(canon_tt) << " 0 0 ";
      for (size_t i = 0; i < raw.size(); ++i) out << (i ? "," : "") << raw[i];
      out << "\n";
      ++count;
    }
  }

  // 3. Parse explicit SLPs from n6_slp_mc5.txt.gz
  gzFile gz = gzopen("artifacts/post190_nist_catalog/n6_slp_mc5.txt.gz", "rb");
  if (gz) {
    char buf[65536];
    std::string leftover;
    int blocks_parsed = 0;
    while (int len = gzread(gz, buf, sizeof(buf) - 1)) {
      buf[len] = '\0';
      std::string data = leftover + buf;
      size_t pos = 0;
      while (true) {
        size_t next_block = data.find("\n\n", pos);
        if (next_block == std::string::npos) {
          leftover = data.substr(pos);
          break;
        }
        std::string block = data.substr(pos, next_block - pos);
        pos = next_block + 2;

        std::istringstream bstream(block);
        std::string line;
        mockturtle::xag_network xag;
        std::vector<mockturtle::xag_network::signal> pis;
        for (int i = 0; i < 6; ++i) pis.push_back(xag.create_pi());
        std::vector<mockturtle::xag_network::signal> ands;
        mockturtle::xag_network::signal po_sig = xag.get_constant(false);
        bool has_po = false;

        while (std::getline(bstream, line)) {
          // strip comment
          auto hash_pos = line.find('#');
          if (hash_pos != std::string::npos) line = line.substr(0, hash_pos);
          auto eq_pos = line.find('=');
          if (eq_pos == std::string::npos) continue;
          std::string lhs = line.substr(0, eq_pos);
          std::string rhs = line.substr(eq_pos + 1);
          while (!lhs.empty() && (lhs.front() == ' ' || lhs.front() == '\t')) lhs.erase(lhs.begin());
          while (!lhs.empty() && (lhs.back() == ' ' || lhs.back() == '\t')) lhs.pop_back();

          if (lhs[0] == 'a') {
            auto mul_pos = rhs.find('*');
            if (mul_pos != std::string::npos) {
              std::string l_expr = rhs.substr(0, mul_pos);
              std::string r_expr = rhs.substr(mul_pos + 1);
              auto l_sig = parse_linear(xag, pis, ands, l_expr);
              auto r_sig = parse_linear(xag, pis, ands, r_expr);
              ands.push_back(xag.create_and(l_sig, r_sig));
            }
          } else if (lhs[0] == 'f' && lhs.size() <= 2) {
            po_sig = parse_linear(xag, pis, ands, rhs);
            has_po = true;
          }
        }

        if (has_po) {
          xag.create_po(po_sig);
          auto simulated = mockturtle::simulate<kitty::static_truth_table<6u>>(xag)[0];
          kitty::dynamic_truth_table tt(6u);
          tt._bits[0] = *simulated.cbegin();
          std::vector<kitty::detail::spectral_operation> trans;
          auto canon_tt = kitty::hybrid_exact_spectral_canonization(tt, [&](auto const& ops) { trans = ops; });
          uint64_t canon_repr = *canon_tt.cbegin();

          if (seen.insert(canon_repr).second) {
            mockturtle::xag_index_list il;
            mockturtle::encode(il, xag);
            auto raw = il.raw();
            out << kitty::to_hex(canon_tt) << " 0 0 ";
            for (size_t i = 0; i < raw.size(); ++i) out << (i ? "," : "") << raw[i];
            out << "\n";
            ++count;
          }
          ++blocks_parsed;
          if (blocks_parsed >= max_blocks) break;
        }
      }
      if (blocks_parsed >= max_blocks) break;
    }
    gzclose(gz);
    std::cout << "Parsed " << blocks_parsed << " SLP blocks, database now has " << count << " unique canonical functions." << std::endl;
  }
  return 0;
}
