import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest
from agent_context_engine import Engine, Registry
from agent_context_engine.adapters import ResponsesAdapter, agent_loop, offline_agent
from agent_context_engine.errors import AccessDenied, ValidationError
from agent_context_engine.mcp import MCP, serve
from agent_context_engine.telemetry import Scope


def test_offline_loop(db,access,tokenizer):
    result=offline_agent(db,'a',access,tokenizer)
    assert result['verified_mock_success'] and result['provider_calls']==0 and result['mock_steps']==2
    assert result['answer']['closing_total']==4200
    assert any(e['kind']=='optimization' for e in db.events(Scope('a'),access))


def test_responses_approval_preserves_ids_and_opaque(db,access):
    calls=[];records=[]
    opaque={'type':'reasoning','id':'opaque','encrypted_content':'SIGNED.DoNotTouch','summary':[]}
    def transport(payload):
        calls.append(payload)
        return {'id':'resp_1','output':[opaque,{'type':'function_call','id':'fc_1','call_id':'call_雪','name':'read_inventory','arguments':'{}'}], 'usage':{'input_tokens':100,'output_tokens':20,'input_tokens_details':{'cached_tokens':0},'output_tokens_details':{'reasoning_tokens':10}}}
    adapter=ResponsesAdapter(model='configured-model',api_key='test-key',approve=lambda p:True,transport=transport,emit=lambda *a,**k:records.append((a,k)))
    response=adapter.create([{'role':'user','content':'test'}],[])
    assert response['output'][0] is opaque
    assert response['output'][1]['call_id']=='call_雪'
    assert calls[0]['stream'] is False and calls[0]['store'] is False
    assert records[0][1]['request_id']=='resp_1'
    assert 'SIGNED' not in json.dumps(records)
    adapter.approve=lambda p:False
    with pytest.raises(AccessDenied):adapter.create([],[])
    assert len(calls)==1


def test_agent_loop_preserves_opaque_history(access):
    outputs=[];counter=0
    opaque={'type':'reasoning','id':'r','encrypted_content':'unaltered.signature'}
    def create(inputs,tools):
        nonlocal counter
        counter+=1
        if counter==1:return {'output':[opaque,{'type':'function_call','name':'read_inventory','call_id':'exact-id','arguments':'{}'}]}
        assert inputs[1] is opaque
        assert inputs[-1]['call_id']=='exact-id' and inputs[-1]['type']=='function_call_output'
        return {'output':[{'type':'message','content':[{'type':'output_text','text':'{"answer":1}'}]}]}
    assert agent_loop(create,Engine('a',access))=={'answer':1}


def test_responses_failures_not_retried():
    calls=[]
    def fail(payload):calls.append(payload);raise TimeoutError('ambiguous')
    adapter=ResponsesAdapter(model='m',api_key='key',approve=lambda _:True,transport=fail)
    with pytest.raises(TimeoutError):adapter.create([],[])
    assert len(calls)==1
    with pytest.raises(ValidationError):adapter.create([],[{'type':'web_search'}])
    assert len(calls)==1


def test_invalid_agent_tool_never_executes(access):
    def create(inputs,tools):return {'output':[{'type':'function_call','name':'run_shell','call_id':'1','arguments':'{}'}]}
    with patch('subprocess.run') as run:
        with pytest.raises(ValidationError):agent_loop(create,Engine('a',access))
        run.assert_not_called()


def test_mcp_lifecycle_tools_authorization(db,access,tmp_path):
    (tmp_path/'test_a.py').write_text('')
    r=Registry(tmp_path,{'auth':'test_a.py'})
    m=MCP(Engine('a',access),db,r)
    def call(method,params={},id=1):return m.handle({'jsonrpc':'2.0','id':id,'method':method,'params':params})
    assert 'error' in call('tools/list')
    assert call('initialize',{'protocolVersion':'old','capabilities':{},'clientInfo':{'name':'test','version':'1'}})['result']['protocolVersion']=='2025-11-25'
    m.handle({'jsonrpc':'2.0','method':'notifications/initialized'})
    assert len(call('tools/list')['result']['tools'])==5
    req=r.encode('auth')
    result=call('tools/call',{'name':'ace_expand','arguments':req})
    assert result['result']['isError'] is False
    assert json.loads(result['result']['content'][0]['text'])['executed'] is False
    req['approve']=True
    assert call('tools/call',{'name':'ace_expand','arguments':req})['result']['isError']
    assert call('tools/call',{'name':'ace_retrieve','arguments':{'reference':'missing'}})['result']['isError']
    assert call('tools/call',{'name':'ace_usage','arguments':{'workspace':'b'}})['result']['isError']


def test_mcp_stdio_framing(db,access):
    input=io.StringIO('{bad}\n'+json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}})+'\n')
    out=io.StringIO();serve(Engine('a',access),db,input=input,output=out)
    records=[json.loads(line) for line in out.getvalue().splitlines()]
    assert records[0]['error']['code']==-32700 and records[1]['result']['serverInfo']['name']=='agent-context-engine'


def test_cli_diagnostics_and_mcp_process(tmp_path):
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src')}
    base=[sys.executable,'-m','agent_context_engine','--state',str(tmp_path/'state')]
    result=subprocess.run(base+['diagnostics'],env=env,capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['raw_storage_default']=='memory_only'
    messages=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'test','version':'1'}}},{'jsonrpc':'2.0','method':'notifications/initialized'},{'jsonrpc':'2.0','id':2,'method':'tools/list'}]
    result=subprocess.run(base+['mcp'],env=env,input='\n'.join(json.dumps(m)for m in messages)+'\n',capture_output=True,text=True,check=True)
    assert len(result.stdout.splitlines())==2
    assert len(json.loads(result.stdout.splitlines()[-1])['result']['tools'])==4
