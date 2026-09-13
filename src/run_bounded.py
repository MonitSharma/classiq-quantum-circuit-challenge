"""External wall-clock guard for solver scripts whose C calls hold the GIL."""
import argparse,json,subprocess,sys,time
from pathlib import Path

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--seconds',type=float,required=True)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('script')
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    assert args.seconds>0 and not args.report.exists()
    command=[sys.executable,args.script,*args.arguments]
    started=time.monotonic()
    try:
        result=subprocess.run(command,timeout=args.seconds)
        report=dict(status='completed' if result.returncode==0 else 'failed',returncode=result.returncode)
    except subprocess.TimeoutExpired:
        report=dict(status='externally_timed_out',solver_conclusion=None)
    report.update(command=command,seconds=time.monotonic()-started,limit_seconds=args.seconds)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
