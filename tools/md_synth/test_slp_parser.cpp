#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <regex>
#include <zlib.h>
#include <kitty/dynamic_truth_table.hpp>
#include <kitty/print.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/algorithms/simulation.hpp>

int main() {
  gzFile file = gzopen("artifacts/post190_nist_catalog/n6_slp_mc5.txt.gz", "rb");
  if (!file) {
    std::cerr << "Cannot open n6_slp_mc5.txt.gz" << std::endl;
    return 1;
  }

  char buffer[4096];
  std::string content;
  int bytes_read;
  // Read first 10KB
  while ((bytes_read = gzread(file, buffer, sizeof(buffer) - 1)) > 0) {
    buffer[bytes_read] = '\0';
    content += buffer;
    if (content.size() > 10000) break;
  }
  gzclose(file);

  std::istringstream stream(content);
  std::string line;
  int block_count = 0;
  while (std::getline(stream, line)) {
    if (line.rfind("f", 0) == 0 && line.find(" = ") != std::string::npos && line.find("x") != std::string::npos) {
      std::cout << "Block " << ++block_count << " func: " << line << std::endl;
      if (block_count >= 3) break;
    }
  }
  return 0;
}
