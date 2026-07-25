# Natural-Language Model Contract Phase 1 - Task 4 Status

**Status:** PASS on 2026-07-15.

## Schemas

- Model contract: `abm-auto/natural-language-model-contract/v1`
- Semantic patch: `abm-auto/semantic-patch/v1`

## Committed Fixture

`base-contract.json` is a quick contract containing a non-empty MIR with the
`threshold_adoption` process. Its parameter at
`/mir/processes/0/params/threshold` starts at `0.4`.

`conversation-patch.json` and `panel-patch.json` each contain exactly one
`replace` operation at that path, changing `0.4` to `0.6`. Both bind to the
exact base contract revision
`7438bfc3c3375fea9e5180eae94a9c38e57d9bfa52507911bcd8db4b64f461d2`.
The patch documents differ only in their `source` field: `conversation` versus
`panel`.

The JSON artifacts are constructor-generated UTF-8. Their byte rule is compact
canonical JSON from `to_json()`, with no indentation and exactly one trailing
LF byte.

## Observed Gate Result

The three committed artifacts were loaded through `load_model_contract` and
`load_semantic_patch`, then checked with `semantic_patch_equivalence_gate`.
The observed result was:

> PASS: structured-patch equivalence only; ordered patch operations and
> resulting MIR are equal, while distinct producer source labels remain
> visible in distinct contract revisions. This does not establish
> natural-language utterance equivalence, LLM extraction equivalence, UI
> behavior equivalence, runtime behavior equivalence, construct validity, or
> scientific truth.

The shared operation digest is
`ac216f659a41ca4880b9c56c6a21a0a7fc7b3813180a64aa6a027adf62034f75`, and
the shared resulting MIR digest is
`f00b181ab810b8f042cace94548ccd15bf9be2b327a1117a942851b98a158007`.
The independently visible result revisions are:

- Conversation: `025ad5b657846e7b13aee9755aa7e08850090bc50234d0b6b97a28c7474c6462`
- Panel: `4504a631cf0facc341132f667a231dc29ca5814173844dee63e8e86e33ad47d4`

## Strict Boundary

This fixture proves deterministic equivalence only after upstream producers
have emitted structured patches. It makes no claim of natural-language
utterance equivalence, LLM extraction equivalence, UI behavior equivalence,
runtime behavior equivalence, construct validity, or scientific truth. It does
not exercise a language model, user interface, code generator, simulation
runtime, or scientific validation workflow.

The contract's application lock is an application-level immutability record.
It is not a scientific prediction lock, Git ancestry proof, or evidentiary
provenance lock.
