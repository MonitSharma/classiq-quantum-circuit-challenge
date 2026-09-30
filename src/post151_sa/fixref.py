s = open('refine.py').read()
if 'from kdrv import full_gates' not in s:
    s = s.replace("from kdv import", "X")  # no-op guard
    s = s.replace("exec(open('try2.py').read()", "from kdrv import full_gates\nexec(open('try2.py').read()", 1)
    open('refine.py','w').write(s)
print('ok')
