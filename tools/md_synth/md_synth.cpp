#include <fstream>
#include <algorithm>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include <mockturtle/algorithms/xag_algebraic_rewriting.hpp>
#include <mockturtle/algorithms/xag_balancing.hpp>
#include <mockturtle/algorithms/simulation.hpp>
#include <mockturtle/networks/xag.hpp>
#include <mockturtle/views/depth_view.hpp>
#include <kitty/print.hpp>

namespace
{
struct seed
{
  using mask_type = unsigned __int128;
  std::vector<std::pair<mask_type, mask_type>> nodes;
  mask_type output{0};
};

seed::mask_type parse_mask( std::string const& text )
{
  seed::mask_type value = 0;
  for ( char c : text )
  {
    if ( c < '0' || c > '9' )
      throw std::runtime_error( "non-decimal XAG mask" );
    value = value * 10 + static_cast<unsigned>( c - '0' );
  }
  return value;
}

seed read_seed( std::string const& path )
{
  std::ifstream input( path );
  if ( !input )
    throw std::runtime_error( "cannot open seed: " + path );
  seed result;
  std::string tag;
  while ( input >> tag )
  {
    if ( tag == "#" )
    {
      std::string ignored;
      std::getline( input, ignored );
    }
    else if ( tag == "AND" )
    {
      std::string left, right;
      input >> left >> right;
      result.nodes.emplace_back( parse_mask( left ), parse_mask( right ) );
    }
    else if ( tag == "OUTPUT" )
    {
      std::string output;
      input >> output;
      result.output = parse_mask( output );
    }
    else
    {
      throw std::runtime_error( "unknown seed record: " + tag );
    }
  }
  return result;
}

std::vector<uint8_t> read_truth( std::string const& path )
{
  std::ifstream input( path );
  if ( !input )
    throw std::runtime_error( "cannot open truth table: " + path );
  std::string hex, part;
  while ( input >> part )
    hex += part;
  if ( hex.size() != 1024 )
    throw std::runtime_error( "expected 512-byte truth table hex" );
  std::vector<uint8_t> bytes;
  bytes.reserve( 512 );
  for ( size_t i = 0; i < hex.size(); i += 2 )
    bytes.push_back( static_cast<uint8_t>( std::stoul( hex.substr( i, 2 ), nullptr, 16 ) ) );
  return bytes;
}

mockturtle::xag_network::signal affine( mockturtle::xag_network& xag,
                                        std::vector<mockturtle::xag_network::signal> const& signals,
                                        seed::mask_type mask )
{
  auto result = xag.get_constant( false );
  for ( uint32_t i = 0; i < 128; ++i )
  {
    if ( ( mask >> i ) & 1u )
    {
      if ( i >= signals.size() )
        throw std::runtime_error( "seed references signal " + std::to_string( i )
                                  + " before signal count " + std::to_string( signals.size() ) );
      result = xag.create_xor( result, signals[i] );
    }
  }
  return result;
}

bool is_and( mockturtle::xag_network const& xag, mockturtle::xag_network::node n )
{
  auto const function = static_cast<uint8_t>( std::stoul( kitty::to_hex( xag.node_function( n ) ), nullptr, 16 ) );
  return ( ( function >> 3 ) ^ ( function >> 2 ) ^ ( function >> 1 ) ^ function ) & 1u;
}

std::vector<uint32_t> levels_for( mockturtle::xag_network const& xag )
{
  std::vector<uint32_t> levels( xag.size(), 0u );
  xag.foreach_node( [&]( auto n ) {
    if ( xag.is_constant( n ) || xag.is_ci( n ) )
      return;
    uint32_t child = 0;
    xag.foreach_fanin( n, [&]( auto s ) { child = std::max( child, levels[s.index] ); } );
    levels[n] = child + ( is_and( xag, n ) ? 1u : 0u );
  } );
  return levels;
}

uint32_t md( mockturtle::xag_network const& xag )
{
  auto const levels = levels_for( xag );
  uint32_t result = 0;
  xag.foreach_po( [&]( auto s ) { result = std::max( result, levels[s.index] ); } );
  return result;
}

std::vector<uint32_t> layer_widths( mockturtle::xag_network const& xag )
{
  auto const levels = levels_for( xag );
  std::vector<uint32_t> widths;
  xag.foreach_gate( [&]( auto n ) {
    if ( is_and( xag, n ) )
    {
      if ( widths.size() < levels[n] )
        widths.resize( levels[n], 0u );
      ++widths[levels[n] - 1];
    }
  } );
  return widths;
}

uint32_t nonlinear_live_width( mockturtle::xag_network const& xag )
{
  std::vector<uint32_t> last_use( xag.size(), 0u );
  xag.foreach_node( [&]( auto n ) {
    if ( xag.is_constant( n ) || xag.is_ci( n ) )
      return;
    xag.foreach_fanin( n, [&]( auto s ) {
      if ( s.index < last_use.size() && !xag.is_constant( s.index ) &&
           !xag.is_ci( s.index ) && is_and( xag, s.index ) )
        last_use[s.index] = std::max( last_use[s.index], static_cast<uint32_t>( n ) );
    } );
  } );
  xag.foreach_po( [&]( auto s ) {
    if ( s.index < last_use.size() && !xag.is_constant( s.index ) &&
         !xag.is_ci( s.index ) && is_and( xag, s.index ) )
      last_use[s.index] = std::max( last_use[s.index], static_cast<uint32_t>( xag.size() ) );
  } );
  std::set<uint32_t> live;
  uint32_t peak = 0;
  xag.foreach_node( [&]( auto n ) {
    if ( xag.is_constant( n ) || xag.is_ci( n ) )
      return;
    for ( auto it = live.begin(); it != live.end(); )
    {
      if ( last_use[*it] < n ) it = live.erase( it );
      else ++it;
    }
    if ( is_and( xag, n ) && last_use[n] ) live.insert( n );
    peak = std::max( peak, static_cast<uint32_t>( live.size() ) );
  } );
  return peak;
}

uint32_t and_count( mockturtle::xag_network const& xag )
{
  uint32_t result = 0;
  xag.foreach_gate( [&]( auto n ) { result += is_and( xag, n ); } );
  return result;
}

using mask_type = unsigned __int128;

std::string mask_to_decimal( mask_type value )
{
  if ( value == 0 ) return "0";
  std::string result;
  while ( value )
  {
    result.push_back( char( '0' + static_cast<unsigned>( value % 10 ) ) );
    value /= 10;
  }
  std::reverse( result.begin(), result.end() );
  return result;
}

mask_type affine_signal_mask( mockturtle::xag_network::signal const& signal,
                              std::unordered_map<uint32_t, mask_type> const& masks )
{
  auto const found = masks.find( signal.index );
  if ( found == masks.end() )
    throw std::runtime_error( "optimized network references an unknown signal" );
  return found->second ^ ( signal.complement ? 1u : 0u );
}

void serialize_xag( mockturtle::xag_network const& xag, std::string const& path )
{
  std::ofstream output( path );
  if ( !output )
    throw std::runtime_error( "cannot write optimized XAG: " + path );
  std::unordered_map<uint32_t, mask_type> masks;
  masks[0] = 0;
  xag.foreach_pi( [&]( auto n, auto index ) { masks[n] = mask_type( 1 ) << ( index + 1 ); } );
  uint32_t next_signal = 13;
  output << "# mockturtle optimized exact XAG; signal 0 is constant-one\n";
  xag.foreach_node( [&]( auto n ) {
    if ( xag.is_constant( n ) || xag.is_ci( n ) )
      return;
    std::vector<mockturtle::xag_network::signal> fanins;
    xag.foreach_fanin( n, [&]( auto s ) { fanins.push_back( s ); } );
    if ( fanins.size() != 2 )
      throw std::runtime_error( "non-binary optimized node" );
    auto const left = affine_signal_mask( fanins[0], masks );
    auto const right = affine_signal_mask( fanins[1], masks );
    auto const function = static_cast<uint8_t>( std::stoul( kitty::to_hex( xag.node_function( n ) ), nullptr, 16 ) );
    auto const coefficient_a = ( ( function >> 2 ) ^ function ) & 1u;
    auto const coefficient_b = ( ( function >> 1 ) ^ function ) & 1u;
    auto const constant = function & 1u;
    if ( is_and( xag, n ) )
    {
      auto const left_factor = left ^ ( coefficient_b ? 1u : 0u );
      auto const right_factor = right ^ ( coefficient_a ? 1u : 0u );
      auto const complement = constant ^ ( coefficient_a & coefficient_b );
      output << "AND " << mask_to_decimal( left_factor ) << " " << mask_to_decimal( right_factor ) << "\n";
      masks[n] = ( mask_type( 1 ) << next_signal++ ) ^ complement;
    }
    else
    {
      masks[n] = constant ^ ( coefficient_a ? left : 0u ) ^ ( coefficient_b ? right : 0u );
    }
  } );
  xag.foreach_po( [&]( auto s ) { output << "OUTPUT " << mask_to_decimal( affine_signal_mask( s, masks ) ) << "\n"; } );
}

bool exact( mockturtle::xag_network const& xag, std::vector<uint8_t> const& target )
{
  for ( uint32_t point = 0; point < 4096; ++point )
  {
    mockturtle::input_word_simulator simulator( point );
    auto values = mockturtle::simulate<bool>( xag, simulator );
    if ( values.empty() || values.front() != static_cast<bool>( ( target[point / 8] >> ( point % 8 ) ) & 1u ) )
      return false;
  }
  return true;
}
}

int main( int argc, char** argv )
{
  try
  {
    const std::string truth_path = argc > 1 ? argv[1] : "artifacts/multiplicative_depth/logo_truth.hex";
    const std::string seed_path = argc > 2 ? argv[2] : "artifacts/multiplicative_depth/seeds/shared_rank.xag";
    const std::string pipeline = argc > 3 ? argv[3] : "balance-rewrite";
    const std::string output_path = argc > 4 ? argv[4] : "";
    const auto target = read_truth( truth_path );
    const auto spec = read_seed( seed_path );

  mockturtle::xag_network xag;
  std::vector<mockturtle::xag_network::signal> signals;
  signals.push_back( xag.get_constant( true ) );
  for ( int i = 0; i < 12; ++i )
    signals.push_back( xag.create_pi() );
  for ( auto const& [left, right] : spec.nodes )
  {
    auto a = affine( xag, signals, left );
    auto b = affine( xag, signals, right );
    signals.push_back( xag.create_and( a, b ) );
  }
  xag.create_po( affine( xag, signals, spec.output ) );

  mockturtle::depth_view initial_depth{xag};
  const auto before = md( xag );
  const auto exact_before = exact( xag, target );
  if ( pipeline == "balance" || pipeline == "balance2" || pipeline == "balance-rewrite" )
    mockturtle::xag_balance(xag);
  if ( pipeline == "balance2" )
    mockturtle::xag_balance(xag);
  mockturtle::depth_view depth_xag{xag};
  if ( pipeline == "rewrite" || pipeline == "balance-rewrite" )
    mockturtle::xag_algebraic_depth_rewriting(depth_xag);
  const auto after = md( depth_xag );
  const auto exact_after = exact( depth_xag, target );
  const auto widths = layer_widths( depth_xag );
  if ( !output_path.empty() && exact_after )
    serialize_xag( depth_xag, output_path );
  std::cout << "{\"truth_points\":4096,\"seed\":\"" << seed_path
            << "\",\"pipeline\":\"" << pipeline
            << "\",\"exact_before\":" << ( exact_before ? "true" : "false" )
            << ",\"exact_after\":" << ( exact_after ? "true" : "false" )
            << ",\"md_before\":" << before
            << ",\"md_after\":" << after
            << ",\"and_count_before\":" << spec.nodes.size()
            << ",\"and_count_after\":" << and_count( depth_xag )
            << ",\"nonlinear_live_width_after\":" << nonlinear_live_width( depth_xag )
            << ",\"optimized_seed\":\"" << output_path << "\""
            << ",\"and_layer_widths_after\":[";
  for ( size_t i = 0; i < widths.size(); ++i )
    std::cout << ( i ? "," : "" ) << widths[i];
  std::cout << "]}\n";
  return 0;
  }
  catch ( std::exception const& error )
  {
    std::cerr << error.what() << "\n";
    return 2;
  }
}
