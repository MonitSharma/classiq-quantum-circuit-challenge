"""Restoration pruning must count circuit layers, including parallel CXs."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]

def test_two_layer_repairs_are_not_pruned(tmp_path):
    compiler=shutil.which('cc')
    if compiler is None:
        pytest.skip('C compiler unavailable')
    source=tmp_path/'check.c'
    source.write_text(f'''
#define N 4
#define main beam_main
#include "{ROOT/'src/post151_sa/kbeam_typed_lb.c'}"
#undef main
#include <assert.h>
int main(void) {{
    for(int i=0;i<N;i++) {{ ST[i]=1<<i; DDLG[i]=100; }}
    uint16_t a[4]={{15,2,4,8}};
    // Old bound says 3; (1->0, 2->3), then 3->0 is a two-layer repair.
    assert(lbwire(a,0,ST[0],0)==3);
    assert(typed_restore_lb(a,0)==2);
    a[0]^=a[1]; a[3]^=a[2]; a[0]^=a[3];
    assert(a[0]==ST[0]);
    uint16_t b[4]={{2,1,4,8}};
    assert(typed_restore_lb(b,0)==2);
    b[1]^=b[0]; b[0]^=b[1]; assert(b[0]==ST[0]);
    uint16_t p[4]={{7,2,4,8}};
    // Rotate on wire 0 while preparing 1->2, then 2->0: two layers,
    // even though the target starts with a pending rotation.
    assert(restore_with_pending(p,0,1)==2);
    p[2]^=p[1]; p[0]^=p[2]; assert(p[0]==ST[0]);

    // Enumerate all two-layer matching sequences from many invertible
    // starting frames. If a home row is reached, the bound must be <=2.
    uint8_t cs[5],ts[5]; genm(0,0,cs,ts);
    uint16_t rows[4]={{1,2,4,8}};
    for(int trial=0;trial<128;trial++) {{
        int c=trial%4,t=(c+1+(trial/4)%3)%4; rows[t]^=rows[c];
        int lb[4]; for(int i=0;i<N;i++) lb[i]=typed_restore_lb(rows,i);
        for(int m=0;m<M;m++) for(int n=0;n<M;n++) {{
            uint16_t r[4]; memcpy(r,rows,sizeof r);
            for(int q=0;q<mk[m];q++) r[mt[m][q]]^=r[mc[m][q]];
            for(int q=0;q<mk[n];q++) r[mt[n][q]]^=r[mc[n][q]];
            for(int i=0;i<N;i++) if(r[i]==ST[i]) assert(lb[i]<=2);
        }}
    }}
    return 0;
}}
''')
    binary=tmp_path/'check'
    subprocess.run([compiler,'-O1',str(source),'-o',str(binary)],check=True,capture_output=True)
    subprocess.run([str(binary)],check=True)
