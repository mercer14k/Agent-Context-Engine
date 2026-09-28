"""Explicit manual live request approval. Never run by tests or CI.

This is an integration example, not the future spend-capped live trial runner.
"""
import os
from pathlib import Path
from agent_context_engine import Access, Engine
from agent_context_engine.adapters import ResponsesAdapter, agent_loop
from agent_context_engine.tokens import available


def approve(payload):
    print('Live request to configured model:', payload['model'])
    print('Output cap:', payload['max_output_tokens'], 'tokens; this request can incur API charges.')
    return input('Authorize this single request? Type yes: ').strip()=='yes'


if __name__=='__main__':
    access=Access('manual-example',frozenset({'synthetic-example'}))
    engine=Engine('synthetic-example',access,tokenizer=available(Path('.ace-local/tokenizer')))
    adapter=ResponsesAdapter(model=os.environ['OPENAI_MODEL'],api_key=os.environ['OPENAI_API_KEY'],approve=approve)
    print(agent_loop(adapter.create,engine))
