import importlib
for m in ['pysat', 'ortools', 'z3', 'pulp', 'scipy', 'numpy', 'networkx']:
    try:
        mod = importlib.import_module(m)
        print(m, 'OK', getattr(mod, '__version__', ''))
    except Exception:
        print(m, 'MISSING')
