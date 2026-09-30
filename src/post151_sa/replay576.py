"""Replay the exact bridge which reduces the 117-depth circuit to 576 CX."""
import argparse,hashlib,json
from pathlib import Path
from postopt import parse_ops,fuse,write
from rewrite117 import moves,optimized
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
 source=ROOT/'artifacts/117/conditional_loader_117_cx577.qasm'
 assert hashlib.sha256(source.read_bytes()).hexdigest()=='d26fa5c655b05c8a9f7f4fc93002061045acaef0368d12f19f7318d6be01c11e'
 ops=fuse(parse_ops(source));mv=moves(ops)[324];candidate,score=optimized(ops,mv,3);assert score[0]==117
 assert sum(o[0]=='cx' for o in candidate)==576
 write(candidate,a.output);print(json.dumps(dict(move=mv,score=score,path=str(a.output),sha256=hashlib.sha256(a.output.read_bytes()).hexdigest())))
if __name__=='__main__':main()
