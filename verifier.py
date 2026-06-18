"""
maya / verifier — the playground.

ONE file. The AI writes whatever check it wants and runs it here, isolated:
a separate process, no network, wall-clock + CPU + memory limits, nothing
persisted. The check defines `check()` and returns a JSON-able result.

    import verifier
    print(verifier.run('''
def check():
    import numpy as np
    psi  = np.array([1, 0, 0, 1]) / np.sqrt(2)       # Bell state
    rho  = np.outer(psi, psi).reshape(2, 2, 2, 2)
    rhoA = np.trace(rho, axis1=1, axis2=3)
    ev   = np.linalg.eigvalsh(rhoA); ev = ev[ev > 1e-12]
    S    = float(-(ev * np.log(ev)).sum())
    return {"S": S, "expected": float(np.log(2)), "passed": abs(S - np.log(2)) < 1e-9}
'''))

SOUNDNESS IS THE CALLER'S JOB: a check only means something if it computes an
OBJECTIVE quantity and compares to INDEPENDENT ground truth — and could FAIL. A
check that just returns True verifies nothing.

Packages: runs under the same Python that imports it (numpy is available). Need
more (qutip, sympy, ...)? `pip install` it first, then run — the check itself
executes sealed (no network).
"""
from __future__ import annotations

import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time

_DRIVER = r'''
import json, sys, socket, traceback
try:
    import resource
except Exception:
    resource = None

def _limit(cpu_s, mem_bytes):
    if resource is None:
        return
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
    except Exception:
        pass
    if mem_bytes and sys.platform != "darwin":          # RLIMIT_AS breaks Python on macOS
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except Exception:
            pass

def _no_network():
    def blocked(*a, **k):
        raise OSError("network is disabled in the maya verifier")
    for name in ("socket", "create_connection", "socketpair"):
        try:
            setattr(socket, name, blocked)
        except Exception:
            pass

def main():
    job_path, out_path = sys.argv[1], sys.argv[2]
    with open(job_path) as f:
        job = json.load(f)
    _limit(job["cpu_s"], job["mem_bytes"])
    _no_network()
    out = {"ok": False, "error": "unknown"}
    try:
        ns = {}
        exec(job["code"], ns)
        fn = ns.get(job["entry"])
        if not callable(fn):
            raise NameError("check must define a callable named %r" % job["entry"])
        results = []
        for args in job["calls"]:
            results.append(fn(*args))
        out = {"ok": True, "results": results}
    except Exception:
        out = {"ok": False, "error": traceback.format_exc()}
    def _enc(o):
        try:
            return o.item()          # numpy scalars (np.bool_, np.float64, ...) -> python
        except Exception:
            return str(o)
    try:
        with open(out_path, "w") as f:
            json.dump(out, f, default=_enc)
    except TypeError:
        with open(out_path, "w") as f:
            json.dump({"ok": False, "error": "result not JSON-serializable"}, f)

main()
'''


def _killpg(proc):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def run(code, entry="check", calls=None, timeout=30, cpu_s=30, mem_mb=2048, python=None):
    """Run `code` in the sandbox, calling `entry(*args)` for each args in `calls`
    (default: call it once with no args). Returns a dict:
        {ok, result, results, error, stdout, seconds, timed_out}
    `result` is the first return value — the usual case for a single check()."""
    calls = calls if calls is not None else [[]]
    python = python or sys.executable
    with tempfile.TemporaryDirectory(prefix="maya-verify-") as d:
        dp = pathlib.Path(d)
        (dp / "driver.py").write_text(_DRIVER)
        (dp / "job.json").write_text(json.dumps({
            "code": code, "entry": entry, "calls": calls,
            "cpu_s": cpu_s, "mem_bytes": mem_mb * 1024 * 1024 if mem_mb else 0,
        }))
        out_path = dp / "out.json"
        env = {"PATH": "/usr/bin:/bin", "HOME": str(dp), "TMPDIR": str(dp),
               "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8",
               "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}  # same packages as the parent
        t0 = time.monotonic()
        proc = subprocess.Popen(
            [python, str(dp / "driver.py"), str(dp / "job.json"), str(out_path)],
            cwd=str(dp), env=env, start_new_session=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            _killpg(proc)
            stdout, stderr = proc.communicate()
            timed_out = True
        seconds = round(time.monotonic() - t0, 3)

        if timed_out:
            return {"ok": False, "result": None, "results": None,
                    "error": f"timeout after {timeout}s", "stdout": stdout,
                    "seconds": seconds, "timed_out": True}
        try:
            o = json.loads(out_path.read_text()) if out_path.exists() else {}
        except (json.JSONDecodeError, OSError):
            o = {}
        if not o:
            return {"ok": False, "result": None, "results": None,
                    "error": "no output (killed: CPU/memory limit?)", "stdout": stdout,
                    "seconds": seconds, "timed_out": False}
        results = o.get("results")
        return {"ok": o.get("ok", False), "result": (results or [None])[0],
                "results": results, "error": o.get("error"), "stdout": stdout,
                "seconds": seconds, "timed_out": False}


if __name__ == "__main__":
    demo = '''
def check():
    import numpy as np
    psi  = np.array([1, 0, 0, 1]) / np.sqrt(2)
    rho  = np.outer(psi, psi).reshape(2, 2, 2, 2)
    rhoA = np.trace(rho, axis1=1, axis2=3)
    ev   = np.linalg.eigvalsh(rhoA); ev = ev[ev > 1e-12]
    S    = float(-(ev * np.log(ev)).sum())
    return {"S": round(S, 6), "expected": round(float(np.log(2)), 6), "passed": abs(S - np.log(2)) < 1e-9}
'''
    print(run(demo))
