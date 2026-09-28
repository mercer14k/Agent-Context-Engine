"""Offline SDK example: exact task envelope and tool-result optimization."""
from pathlib import Path
import json
from agent_context_engine import Engine, Access
from agent_context_engine.fixtures import story_manifest, inventory
from agent_context_engine.tokens import available

access = Access('example-host', frozenset({'example-project'}))
engine = Engine('example-project', access, tokenizer=available(Path('.ace-local/tokenizer')))
context = engine.prepare_context(story_manifest(), 'Validate narrative structure', ['heroes', 'nodes'], 'Separate hero, chapter, node assertions')
print(json.dumps(context, indent=2))
result = engine.optimize(inventory(), 'json', exact_dataset=True)
print(json.dumps({k:v for k,v in result.metadata().items() if k!='content'},indent=2))
