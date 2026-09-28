"""Generate current-host request and show its exact invocation, without execution."""
import json
from pathlib import Path
from agent_context_engine import Registry
from agent_context_engine.tokens import available

root=Path(__file__).resolve().parents[1]
registry=Registry(root,{'auth':'tests/test_core.py'})
request=registry.encode('auth',1)
(root/'examples/request.json').write_text(json.dumps(request,indent=2))
print(json.dumps(registry.dry_run(request),indent=2))
print(json.dumps(registry.choose_interface(request,available(root/'.ace-local/tokenizer')),indent=2))
