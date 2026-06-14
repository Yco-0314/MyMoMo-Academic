# Security Policy

## Reporting a vulnerability

Please report security issues privately, **not** as a public issue.

- Preferred: GitHub → the repository's **Security** tab → **Report a vulnerability**
  (private security advisory).

You'll get an acknowledgement as soon as possible. Please include steps to
reproduce and the affected version/commit.

## Security model — read this before running untrusted input

This project is an **autonomous code-generation and execution** system. It is
important to understand what that means for safety:

- **It runs LLM-generated Python.** The pipeline turns a natural-language
  `story.md` into model code and then **executes it** to produce simulation
  results. Generated code is arbitrary Python running with your user's
  privileges.
- **A `story.md` is an untrusted input in the same way a script is.** A
  malicious or careless scenario can steer codegen toward code that touches the
  filesystem, the network, or your environment.
- **It calls external LLM APIs** (Anthropic / OpenAI / DeepSeek), sending it the
  contents of your `story.md` and intermediate artifacts. Do not feed it secrets
  or data you are not comfortable sending to those providers.

### Recommended precautions

- Run the pipeline in an **isolated environment** (container, VM, or a
  throwaway user account) when processing scenarios you did not write yourself.
- Keep API keys in `.env` (git-ignored) or the environment — never in `story.md`,
  code, or committed files.
- Review generated model code before reusing it outside the sandbox.

These are properties of the tool's purpose (autonomous codegen), not bugs. We
still want to hear about ways the sandboxing or guardrails can be tightened —
please report them via the channel above.
