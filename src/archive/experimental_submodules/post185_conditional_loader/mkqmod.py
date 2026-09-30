import re, sys, hashlib
def qasm_to_qmod(qasm_path, qmod_path, fname="conditional_loader_logo_oracle"):
    src=open(qasm_path).read(); sha=hashlib.sha256(src.encode()).hexdigest()
    st=[s.strip() for s in re.sub(r"//[^\n]*","",src).split(";") if s.strip()]
    lines=[f"// Standalone QASM SHA-256: {sha}",
           "// Literal gate-for-gate companion of the QASM; main adds twelve preparation Hadamards (absent from the QASM).",
           f"qfunc {fname}(q: qbit[18]) {{"]
    n=0
    for s in st[3:]:
        m=re.fullmatch(r"u3\s*\(([^,]+),([^,]+),([^,]+)\)\s+q\s*\[\s*(\d+)\s*\]",s)
        if m:
            lines.append(f"  U({float(m.group(1))!r}, {float(m.group(2))!r}, {float(m.group(3))!r}, 0.0, q[{m.group(4)}]);"); n+=1; continue
        m=re.fullmatch(r"cx\s+q\s*\[\s*(\d+)\s*\]\s*,\s*q\s*\[\s*(\d+)\s*\]",s)
        if m:
            lines.append(f"  CX(q[{m.group(1)}], q[{m.group(2)}]);"); n+=1; continue
        raise ValueError(s)
    lines.append("}"); lines.append("")
    lines.append("qfunc main(output q: qbit[18]) {"); lines.append("  allocate(18, q);")
    for i in range(12): lines.append(f"  H(q[{i}]);")
    lines.append(f"  {fname}(q);"); lines.append("}")
    open(qmod_path,"w").write("\n".join(lines)+"\n")
    return sha,n
if __name__=="__main__":
    print(qasm_to_qmod(sys.argv[1],sys.argv[2]))
