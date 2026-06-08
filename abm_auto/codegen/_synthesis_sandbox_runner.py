"""Subprocess entry for sandboxed candidate verification (ADR-015, option B).

Reads a synthesized candidate operator's CODE from stdin and an oracle paradigm
name from argv[1], execs the code to obtain ``build`` (the factory the oracle
calls), runs the AUDITED library oracle on it, and prints exactly ``PASS`` or
``FAIL``. Run by ``verify_in_subprocess`` in a separate, timeout-bounded process
so a hanging / crashing / escaping candidate is contained — the PARENT never
execs untrusted code, and the verdict it trusts is the audited oracle's, run
here on our side fresh (the candidate cannot supply or alter the oracle).

A plain subprocess gives ISOLATION (fresh interpreter, no inherited state, the
parent can kill on timeout) but is not by itself a hard security boundary; for
untrusted input set ``sandbox_cmd`` (e.g. firejail/nsjail) on the caller so this
runs with no network/filesystem.
"""
import sys


def main() -> None:
    paradigm = sys.argv[1] if len(sys.argv) > 1 else ""
    code = sys.stdin.read()
    try:
        from abm_auto.codegen.synthesis_oracles import REAL_ORACLES

        oracle = REAL_ORACLES.get(paradigm)
        if oracle is None:                      # unaudited paradigm — never trust
            print("FAIL")
            return
        namespace: dict = {}
        exec(code, namespace)                   # the candidate operator (untrusted)
        build = namespace.get("build")
        if not callable(build):
            print("FAIL")
            return
        print("PASS" if oracle(build) else "FAIL")
    except Exception:
        print("FAIL")


if __name__ == "__main__":
    main()
