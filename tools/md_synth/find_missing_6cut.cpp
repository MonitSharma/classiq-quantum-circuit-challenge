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
  std::unordered_set<uint64_t> targets = {
    0xa222222208888888ULL,
    0x0080808080000000ULL,
    0x8808080800808080ULL,
    0x0880808088000000ULL,
    0x2a80808080808080ULL,
    0x2888a8080a008a80ULL,
    0x888a088a2220a220ULL
  };

  // Load seen from nist_6cut_db.txt
  std::unordered_set<uint64_t> seen;
  std::ifstream existing("artifacts/post190_nist_catalog/nist_6cut_db.txt");
  std::string line;
  while (std::getline(existing, line)) {
    if (line.size() >= 16) {
      uint64_t repr = std::stoull(line.substr(0, 16), nullptr, 16);
      seen.insert(repr);
    }
  }
  std::cout << "Loaded " << seen.size() << " existing canonical functions." << std::endl;
  for (auto t : targets) {
    if (seen.count(t)) {
      std::cout << "Target 0x" << std::hex << t << " already in DB!" << std::dec << std::endl;
    }
  }

  std::ofstream out("artifacts/post190_nist_catalog/nist_6cut_db.txt", std::ios::app);
  uint32_t found = 0;

  gzFile gz = gzopen("artifacts/post190_nist_catalog/n6_slp_mc5.txt.gz", "rb");
  if (!gz) {
    std::cerr << "Cannot open n6_slp_mc5.txt.gz" << std::endl;
    return 1;
  }

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
      mockturtle::xag_network xag;
      std::vector<mockturtle::xag_network::signal> pis;
      for (int i = 0; i < 6; ++i) pis.push_back(xag.create_pi());
      std::vector<mockturtle::xag_network::signal> ands;
      mockturtle::xag_network::signal po_sig = xag.get_constant(false);
      bool has_po = false;

      while (std::getline(bstream, line)) {
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
        uint64_t sim_word = *simulated.cbegin();
        int pop = __builtin_popcountll(sim_word);

        // Fast popcount check: target popcounts are {4, 6, 8, 10, 14, 16} and complements
        if (pop == 4 || pop == 60 ||
            pop == 6 || pop == 58 ||
            pop == 8 || pop == 56 ||
            pop == 10 || pop == 54 ||
            pop == 14 || pop == 50 ||
            pop == 16 || pop == 48) {
          kitty::dynamic_truth_table tt(6u);
          tt._bits[0] = sim_word;
          std::vector<kitty::detail::spectral_operation> trans;
          auto canon_tt = kitty::hybrid_exact_spectral_canonization(tt, [&](auto const& ops) { trans = ops; });
          uint64_t canon_repr = *canon_tt.cbegin();

          if (targets.count(canon_repr) || seen.insert(canon_repr).second) {
            mockturtle::xag_index_list il;
            mockturtle::encode(il, xag);
            auto raw = il.raw();
            out << kitty::to_hex(canon_tt) << " 0 0 ";
            for (size_t i = 0; i < raw.size(); ++i) out << (i ? "," : "") << raw[i];
            out << "\n";
            out.flush();
            if (targets.count(canon_repr)) {
              std::cout << "[!] FOUND TARGET: 0x" << std::hex << canon_repr << std::dec
                        << " at block " << blocks_parsed << "!" << std::endl;
              ++found;
            }
          }
        }
        ++blocks_parsed;
      }
    }
  }
  gzclose(gz);
  std::cout << "Parsed all " << blocks_parsed << " blocks, found " << found << " targets." << std::endl;
  return 0;
}
