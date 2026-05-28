"""Code-generation support utilities — separate from the LLM CoderAgent.

Today: anti-pattern static scanner (catches recurring hallucinations and
removed-API usages in generated code before runtime). Future room: schema
validators, code transformers, fixture loaders.
"""
