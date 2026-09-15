#include <iostream>
#include <fstream>
#include <vector>
#include <string>

#include <mockturtle/algorithms/cleanup.hpp>
#include <mockturtle/algorithms/cut_rewriting.hpp>
#include <mockturtle/algorithms/node_resynthesis/xag_minmc2.hpp>
#include <mockturtle/algorithms/resubstitution.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/algorithms/xag_balancing.hpp>
#include <mockturtle/algorithms/xag_optimization.hpp>
#include <mockturtle/algorithms/xag_resub.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/properties/mccost.hpp>
#include <mockturtle/utils/cost_functions.hpp>
#include <mockturtle/views/depth_view.hpp>
#include <kitty/print.hpp>

namespace {
struct seed {
  using mask_type = unsigned __int128;
  std::vector<std::pair<mask_type, mask_type>> nodes;
  mask_type output{0};
};

seed::mask_type parse_mask(std::string const& text) {
  seed::mask_type value = 0;
  for (char c : text) {
    if (c < '0' || c > '9') throw std::runtime_error("non-decimal XAG mask");
    value = value * 10 + static_cast<unsigned>(c - '0');
  }
  return value;
}

seed read_seed(std::string const& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open seed: " + path);
  seed result;
  std::string tag;
  while (input >> tag) {
    if (tag == "#") {
      std::string ignored;
      std::getline(input, ignored);
    } else if (tag == "AND") {
      std::string left, right;
      input >> left >> right;
      result.nodes.emplace_back(parse_mask(left), parse_mask(right));
    } else if (tag == "OUTPUT") {
      std::string output;
      input >> output;
      result.output = parse_mask(output);
    }
  }
  return result;
}

std::vector<uint8_t> read_truth(std::string const& path) {
  std::ifstream input(path);
  if (!input) throw std::runtime_error("cannot open truth table: " + path);
  std::string hex, part;
  while (input >> part) hex += part;
  std::vector<uint8_t> bytes;
  for (size_t i = 0; i < hex.size(); i += 2) {
    bytes.push_back(static_cast<uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
  }
  return bytes;
}

mockturtle::xag_network::signal affine(mockturtle::xag_network& xag,
                                       std::vector<mockturtle::xag_network::signal> const& signals,
                                       seed::mask_type mask) {
  auto result = xag.get_constant(false);
  for (uint32_t i = 0; i < 128; ++i) {
    if ((mask >> i) & 1u) {
      result = xag.create_xor(result, signals[i]);
    }
  }
  return result;
}

bool exact(mockturtle::xag_network const& xag, std::vector<uint8_t> const& target) {
  for (uint32_t point = 0; point < 4096; ++point) {
    mockturtle::input_word_simulator simulator(point);
    auto values = mockturtle::simulate<bool>(xag, simulator);
    if (values.empty() || values.front() != static_cast<bool>((target[point / 8] >> (point % 8)) & 1u))
      return false;
  }
  return true;
}

uint32_t and_count(mockturtle::xag_network const& xag) {
  uint32_t result = 0;
  xag.foreach_gate([&](auto n) {
    if (xag.is_and(n)) ++result;
  });
  return result;
}
}

int main(int argc, char** argv) {
  try {
    const std::string truth_path = "artifacts/multiplicative_depth/logo_truth.hex";
    const std::string seed_path = "artifacts/multiplicative_depth/seeds/shared_rank.xag";
    const auto target = read_truth(truth_path);
    const auto spec = read_seed(seed_path);

    mockturtle::xag_network xag;
    std::vector<mockturtle::xag_network::signal> signals;
    signals.push_back(xag.get_constant(true));
    for (int i = 0; i < 12; ++i) signals.push_back(xag.create_pi());
    for (auto const& [left, right] : spec.nodes) {
      auto a = affine(xag, signals, left);
      auto b = affine(xag, signals, right);
      signals.push_back(xag.create_and(a, b));
    }
    xag.create_po(affine(xag, signals, spec.output));

    std::cout << "Initial ANDs: " << and_count(xag) << ", exact: " << exact(xag, target) << std::endl;

    for (int iter = 0; iter < 10; ++iter) {
      std::cout << "\n--- Iteration " << iter + 1 << " ---" << std::endl;
      uint32_t before_iter = and_count(xag);

      // Balance
      mockturtle::xag_balance(xag);
      std::cout << "After balance: " << and_count(xag) << ", exact: " << exact(xag, target) << std::endl;

      // Constant fanin opt
      xag = mockturtle::xag_constant_fanin_optimization(xag);
      std::cout << "After constant fanin: " << and_count(xag) << ", exact: " << exact(xag, target) << std::endl;

      // Don't cares opt
      xag = mockturtle::xag_dont_cares_optimization(xag);
      std::cout << "After dont cares: " << and_count(xag) << ", exact: " << exact(xag, target) << std::endl;

      // Cut rewriting
      mockturtle::future::xag_minmc_resynthesis<mockturtle::xag_network> resyn;
      mockturtle::cut_rewriting_params ps;
      ps.cut_enumeration_ps.cut_size = 6;
      ps.cut_enumeration_ps.cut_limit = 24;
      ps.allow_zero_gain = true;
      xag = mockturtle::cut_rewriting<mockturtle::xag_network, decltype(resyn), mockturtle::mc_cost<mockturtle::xag_network>>(
          xag, resyn, ps);
      xag = mockturtle::cleanup_dangling(xag);
      std::cout << "After cut rewriting: " << and_count(xag) << ", exact: " << exact(xag, target) << std::endl;

      // Resubstitution
      mockturtle::resubstitution_params rps;
      rps.max_divisors = 150;
      rps.max_inserts = 2;
      mockturtle::fanout_view<mockturtle::xag_network> f_view{ xag };
      mockturtle::depth_view<mockturtle::fanout_view<mockturtle::xag_network>> resub_view{ f_view };
      mockturtle::xag_resubstitution(resub_view, rps);
      xag = mockturtle::cleanup_dangling(xag);
      std::cout << "After resubstitution: " << and_count(xag) << ", exact: " << exact(xag, target) << std::endl;

      if (and_count(xag) == before_iter) {
        std::cout << "Converged at iteration " << iter + 1 << std::endl;
        break;
      }
    }

    return 0;
  } catch (std::exception const& e) {
    std::cerr << "Error: " << e.what() << std::endl;
    return 1;
  }
}
