"""Guard fused loader deadlines and literal FEM rotation replay."""
from pathlib import Path
import os,pickle,shutil,subprocess,sys
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/post151_sa'))
sys.path.insert(0,str(ROOT/'src/post151_sa/tail115'))

def test_fem_replay_respects_busy_rotation_slots(tmp_path):
    from fem_replay import build_kernel
    home=[1<<k for k in range(8)];co=np.zeros(256);co[1]=.25
    pl=([],list(range(8)),home,[0]*8,[0]*8)
    env={k:','.join([str(v)]*8) for k,v in [('ZS',0),('ZD',4),('CS',0),('CD',4),('XS',0),('XD',4)]}
    env['ZBUSY']='0,1'
    short=tmp_path/'short';short.write_text('1 0\n0\n')
    with pytest.raises(AssertionError):build_kernel(pl,short,co,env)
    full=tmp_path/'full';full.write_text('2 0\n0\n0\n')
    assert build_kernel(pl,full,co,env)[1:]==[('R',0,.5)]

def test_asap_caps_reproduce_champion_profile(tmp_path,monkeypatch):
    cc=shutil.which('cc')
    if not cc:pytest.skip('C compiler unavailable')
    binary=tmp_path/'beam';subprocess.run([cc,'-O2',str(ROOT/'src/post151_sa/lbeam_asap_caps.c'),'-o',str(binary)],check=True)
    source=ROOT/'src/post151_sa';out=tmp_path/'result'
    env=dict(os.environ,CODECAP='44,35,0,43,0,0,0,0,0,0,0,44,0,0,0',WFRZ='0',WFT='.35',WFMAX='.7',
             FZMAX='4',WREACH2='.15',NP='18',WSPREAD='.6',SPCAP='3',
             BLKW='14,28,30,40,42,24,30,27,29,33,31,29,31,31,29',
             PREFIX=str(source/'runs/t115_0923/loaders/champ_x.pfx'),PREFIXK='44')
    result=subprocess.run([str(binary),'1000','32','48','1','16','.5',str(out),'.02'],input=(source/'runs/s118x.lb').read_text(),
                          text=True,capture_output=True,env=env)
    assert result.returncode==0,result.stderr
    monkeypatch.setenv('CLASSIQ_ROOT',str(ROOT));monkeypatch.setenv('CLASS_CODES',str(ROOT/'artifacts/185/class_codes.json'))
    monkeypatch.chdir(tmp_path);(tmp_path/'runs').mkdir()
    from lbeval2 import load_beam,sa4
    from sim import check_loader2,symbolic_final
    from kdrv import profile
    D=pickle.load(open(source/'runs/s118x.pkl','rb'));_,seq=load_beam(out)
    _,pen,g=sa4(D,seq,binary=str(source/'c/sa4'),tag='control')
    assert pen==0 and check_loader2(g,D['newcode'])['max_dev']<1e-9
    clocks,_=profile(g);rows=symbolic_final(g)
    for row,deadline in [(48,44),(64,35),(128,43),(256,44)]:
        assert clocks[rows.index(row)]<=deadline
