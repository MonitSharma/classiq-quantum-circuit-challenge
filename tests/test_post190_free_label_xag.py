import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from post190_free_label_xag import solve


def test_free_labels_affine_positive_control():
 classes=[v&3 for v in range(64)]
 r=solve('y',0,2,class_table=classes,raw_mask=32)
 assert r['status']=='sat'
 assert r['checked_inputs']==64
 assert r['xag']['and_count']==0
 assert len(set(r['codes']))==4
