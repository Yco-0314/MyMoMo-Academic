# Synthesize an operator — write Python for a known protocol

The Coverage Gate halted on a mechanism (capability `{{ capability }}`) the
runtime has no operator for, but there IS an audited verification paradigm:
**{{ paradigm }}**. Write a small, correct, dependency-light Python
implementation. An INDEPENDENT oracle will verify it on a known problem in an
isolated sandbox — you cannot see or influence the oracle; just implement the
protocol correctly.

## Protocol — define EXACTLY this

{{ protocol }}

Hard rules:
- Define a module-level callable **`build`** exactly as the protocol says.
- Pure numerical operator: standard library only (you MAY `import math` /
  `import random`). NO file access, NO network, NO `os`/`sys`/`subprocess`,
  no printing. The sandbox denies these anyway.
- Self-contained: the code is `exec`'d alone; define every name you use.

{{ feedback }}

## Output

ONE fenced ```python``` block containing the implementation. Nothing before or
after it.
