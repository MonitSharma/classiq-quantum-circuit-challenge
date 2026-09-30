"""Loader prefix replay and empty matching sets must remain safe."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def beam(tmp_path_factory):
    cc=shutil.which('cc')
    if cc is None:
        pytest.skip('C compiler unavailable')
    binary=tmp_path_factory.mktemp('parity')/'beam'
    subprocess.run([cc,'-O1',str(ROOT/'src/post151_sa/lbeam_parity.c'),'-o',str(binary)],check=True)
    return binary

def test_parity_creation_prefix_is_replayed(beam,tmp_path):
    prefix=tmp_path/'prefix.txt'; prefix.write_text('1 0\n1 4 5\n')
    output=tmp_path/'out.txt'
    env=dict(os.environ,PROTECT_TARGET='32',PREFIX=str(prefix),PREFIXK='1')
    inp='3\n64 0\n128 1\n256 2\n4\n48 64 128 256\n0\n'
    p=subprocess.run([str(beam),'20','8','5','1','16','.5',str(output),'.02'],
                     input=inp,text=True,capture_output=True,env=env)
    assert p.returncode==0,p.stderr
    lines=output.read_text().splitlines()
    assert lines[1]=='1 4 5'
    for line in lines[2:]:
        values=list(map(int,line.split()))
        assert all(values[2+2*i]!=5 for i in range(values[0]))

def test_no_legal_target_returns_failure_without_overrun(beam,tmp_path):
    env=dict(os.environ,PROTECT_TARGET='511')
    env.pop('PREFIX',None); env.pop('PREFIXK',None)
    inp='4\n64 0\n65 0\n128 1\n256 2\n0\n0\n'
    p=subprocess.run([str(beam),'20','8','5','1','16','.5',str(tmp_path/'out'),'.02'],
                     input=inp,text=True,capture_output=True,env=env)
    assert p.returncode==2,p.stderr
