# 116 / 567 CX recipe (Sept 24)
- x loader: champion (`sat116/champ117.pkl` DX); y loader: `y_loader_y1.pkl` (lbeam4c W=4000 seed 1 default TG + sa4; py ready 40).
- phase array: `artifacts/116/recipes/kernel_co.npy` (co_24).
- kernel schedule: `kernel_schedule.txt` (kbeam_t3, strict rotation windows, model T=115, seed 1) -> assembled 116, MILP 116.
- Rebuild: `STRICT=1 python3 src/post151_sa/tail115/paireval.py champ y_loader_y1.pkl 115 16000 1 cxy1` (edit the path constants first), or pairk.py with this schedule.
