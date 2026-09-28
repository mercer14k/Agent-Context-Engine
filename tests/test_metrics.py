from copy import deepcopy
import json
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from agent_context_engine.benchmark import seed_demo, offline
from agent_context_engine.metrics import summarize, usage_cost, percentile, fraction, reduction, validate_settings
from agent_context_engine.telemetry import Scope, Telemetry
from agent_context_engine.errors import AccessDenied, ValidationError
from agent_context_engine.store import Access
from agent_context_engine.reports import csv_safe, export_csv, report_html
from agent_context_engine.adapters import normalize_responses_usage


def summary(db,access,**kwargs):
    scope=Scope('a',**kwargs)
    return summarize(db.events(scope,access),scope,db.settings('a',access))


def run(db,access,rid='r',**kwargs):
    data={'task':rid,'start':100,'end':102,'expected_requests':1,'success':True,'validator':'assert-v1','provider':'simulated','model':'fixture-model','tokenizer':'fixture-counts-v1','agent':'a','config':'test-v1'}
    data.update(kwargs)
    db.emit('a','real',rid,'run',data,access)


def usage(db,access,rid='r',request='req',revision=1,**kwargs):
    data={'provider':'simulated','model':'fixture-model','input_tokens':100,'output_tokens':20,'cached_input_tokens':0,'cache_write_tokens':0,'tool_cost':0,'final':True,'purpose':'operation','evidence':'Simulated','price_version':'demo-v1'}
    data.update(kwargs)
    db.emit('a','real',rid,'usage',data,access,request_id=request,revision=revision)


def test_empty_unknown_denominators(db,access):
    s=summary(db,access)
    assert s['cost'] is None and s['cost_per_success'] is None and s['success_rate'] is None
    assert s['input_tokens'] is None and s['usage_coverage'] is None
    assert all(a['status']=='insufficient data' for a in s['alerts'])
    assert fraction(0,0) is None and reduction(0,0) is None and percentile([], .95) is None


def test_arithmetic_25_percent(db,access):
    seed_demo(db,'a',access)
    s=summary(db,access,mode='demo',filters={'benchmark':'arithmetic-25-percent'})
    assert s['sample_size']==3
    pair=next(x for x in s['pairs'] if x['baseline_arm']=='native')
    assert pair['baseline_tokens']==12000 and pair['engine_tokens']==9000
    assert pair['reduction_pct']==25
    engine=next(r for r in s['runs'] if r['arm']=='engine')
    assert engine['input_tokens']==7000 and engine['output_tokens']==2000 and engine['requests']==2
    assert engine['cost']==pytest.approx(.030)
    assert s['conflicting_requests']==0
    separate=summary(db,access,mode='demo',filters={'benchmark':'arithmetic-25-percent','arm':'engine'})
    assert separate['payload'][0]['reduction_pct']==40
    assert separate['pairs']==[]
    assert summary(db,access)['sample_size']==0


def test_demo_idempotence_negative_missing_and_failed(db,access):
    seed_demo(db,'a',access);seed_demo(db,'a',access)
    s=summary(db,access,mode='demo')
    assert s['sample_size']==21
    assert s['failures']==1 and s['unevaluated']==3
    negative=summary(db,access,mode='demo',filters={'benchmark':'negative-savings'})
    assert next(c for c in negative['comparisons'] if c['baseline_arm']=='native')['reduction_pct']<0
    cache=summary(db,access,mode='demo',filters={'benchmark':'lost-cache-benefit'})
    comp=next(c for c in cache['comparisons'] if c['baseline_arm']=='native')
    assert comp['reduction_pct']>0 and comp['cost_improvement_pct']<0
    missing=summary(db,access,mode='demo',filters={'benchmark':'missing-usage'})
    assert missing['cost'] is None and missing['known_partial_cost'] is not None
    assert missing['input_tokens'] is None and missing['success_rate'] is None


def test_unknown_prices_not_free(db,access):
    run(db,access);usage(db,access)
    s=summary(db,access)
    assert s['input_tokens']==100 and s['output_tokens']==20
    assert s['cost'] is None and s['cost_per_success'] is None
    assert s['known_partial_cost'] is None


def test_duplicate_cumulative_out_of_order(db,access):
    run(db,access)
    usage(db,access,revision=2,input_tokens=100,output_tokens=20)
    usage(db,access,revision=1,input_tokens=80,output_tokens=10,final=False)
    usage(db,access,revision=2,input_tokens=100,output_tokens=20)
    s=summary(db,access)
    assert s['input_tokens']==100 and s['output_tokens']==20 and s['runs'][0]['requests']==1


def test_conflicting_cumulative_usage_unavailable(db,access):
    run(db,access)
    usage(db,access,input_tokens=100)
    usage(db,access,input_tokens=101)
    s=summary(db,access)
    assert s['input_tokens'] is None and s['conflicting_requests']==1


def test_missing_requests_and_unknown_success(db,access):
    run(db,access,expected_requests=2,success=None)
    usage(db,access)
    s=summary(db,access)
    assert s['usage_coverage']==0 and s['input_tokens'] is None
    assert s['evaluated']==0 and s['unevaluated']==1
    assert s['runs'][0]['known_partial_tokens']==120


def test_reasoning_cache_accounting():
    p={'provider':'openai','model':'model','version':'v1','currency':'USD','source':'test','effective_date':'2026-09-14','input':2,'cached_input':.2,'cache_write':3,'output':8,'discount':0,'rule':'inclusive-input-disjoint-cache-v1'}
    u=normalize_responses_usage({'input_tokens':10000,'output_tokens':2000,'input_tokens_details':{'cached_tokens':8000},'output_tokens_details':{'reasoning_tokens':1500}},model='model',price_version='v1')
    c=usage_cost(u,[p])
    assert c['total']==pytest.approx(.0216)
    assert c['input']==pytest.approx(.0056) and c['output']==pytest.approx(.016)
    assert u['raw_usage']['output_tokens_details']['reasoning_tokens']==1500
    u['cache_write_tokens']=3000
    assert usage_cost(u,[p])['total'] is None


def test_partial_spend_failure_retries_and_judge(db,access):
    from agent_context_engine.fixtures import DEMO_PRICE
    settings=db.settings('a',access);settings['prices']=[DEMO_PRICE.copy()]
    db.settings('a',access,settings)
    run(db,access,'success',expected_requests=2)
    usage(db,access,'success','1')
    usage(db,access,'success','2',purpose='evaluation')
    run(db,access,'failed',success=False)
    usage(db,access,'failed','3')
    db.emit('a','real','failed','retry',{'reason_code':'network'},access)
    s=summary(db,access)
    assert s['cost_per_success']==pytest.approx(.00108)
    assert s['operational_cost']==pytest.approx(.00072)
    assert s['evaluation_cost']==pytest.approx(.00036)
    assert s['retries']==1 and s['success_rate']==.5


def test_concurrent_span_duration_not_sum(db,access):
    run(db,access,start=100,end=110)
    usage(db,access,span_id='child-a',parent_span_id='root')
    db.emit('a','real','r','optimization',{'duration_ms':6000,'span_id':'child-b','parent_span_id':'root'},access)
    s=summary(db,access)
    assert s['duration_median_ms']==10000 and s['duration_p95_ms']==10000
    assert percentile([1,2,3,4,100],.95)==pytest.approx(80.8)


def test_scope_filters_apply_whole_tasks(db,access):
    run(db,access,'keep',start=100,end=1000,agent='worker')
    usage(db,access,'keep','keep-request')
    run(db,access,'skip',start=10,end=11,agent='other')
    usage(db,access,'skip','skip-request')
    s=summary(db,access,start=90,end=110,filters={'agent':'worker'})
    assert s['sample_size']==1 and s['input_tokens']==100
    assert len(s['runs'])==1
    other=Access('other',frozenset({'b'}))
    with pytest.raises(AccessDenied):db.events(Scope('a'),other)


def test_incompatible_model_totals_not_pooled(db,access):
    run(db,access,'r1',model='one');usage(db,access,'r1','one',model='one')
    run(db,access,'r2',model='two');usage(db,access,'r2','two',model='two')
    assert summary(db,access)['input_tokens'] is None


def test_missing_baseline_no_counterfactual(db,access):
    run(db,access,arm='engine',pair_id='x',benchmark='same')
    usage(db,access)
    s=summary(db,access)
    assert s['pairs']==[] and s['comparisons']==[]


def test_exports_escape_content_and_formula(db,access):
    run(db,access,task='=HYPERLINK("evil")<script>alert(1)</script>')
    usage(db,access)
    s=summary(db,access)
    csv=export_csv(s)
    assert "'=HYPERLINK" in csv
    html=report_html(s)
    assert '<script>alert(1)</script>' not in html and '&lt;script&gt;' in html
    for text in ['+x','-x','@x','  =x','\tx']:
        assert csv_safe(text).startswith("'")
    assert s==json.loads(json.dumps(s))


def test_event_bounds_and_redaction(db,access):
    run(db,access)
    with pytest.raises(ValidationError):db.emit('a','real','r','command',{'api_key':'secret'},access)
    db.emit('a','real','r','command',{'operation':'run_tests','arguments':'password=secret','invocation':'secret'},access)
    events=db.events(Scope('a'),access)
    assert 'password=secret' not in json.dumps(events)
    assert '"invocation": "secret"' not in json.dumps(events)
    with pytest.raises(ValidationError):usage(db,access,input_tokens=True)
    with pytest.raises(ValidationError):usage(db,access,raw_usage={'secret':'password'})


def test_retention_restart_and_bounded_events(tmp_path,access):
    path=tmp_path/'db'
    db=Telemetry(path,max_events=2,retention_days=1)
    run(db,access);usage(db,access)
    assert db.emit('a','real','r','retry',{'reason_code':'x'},access) is None
    assert db.drops==1
    db.db.execute('UPDATE events SET received=?',(time.time()-172800,));db.db.commit()
    assert db.cleanup()==2
    db.close()
    db=Telemetry(path)
    assert db.events(Scope('a'),access)==[]
    db.close()


def test_concurrent_telemetry_workspaces(db,access):
    def work(i):
        ws='a' if i%2 else 'b'
        db.emit(ws,'real',str(i),'run',{'task':str(i),'start':100,'end':101},access)
    with ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(work,range(50)))
    assert len(db.events(Scope('a'),access))==25
    assert len(db.events(Scope('b'),access))==25


def test_offline_benchmark_pipeline(db,access,tokenizer):
    report=offline(db,'a',access,tokenizer,repeats=2)
    assert len(report['records'])==24 and report['all_fidelity_passed']
    s=summary(db,access)
    assert s['sample_size']==24
    assert s['cost'] is None and s['input_tokens'] is None
    assert s['evaluated']==0 # fidelity checks are not live task success
    assert len(s['checks'])==24


def test_settings_validation(db,access):
    value=db.settings('a',access)
    validate_settings(value)
    bad=deepcopy(value);bad['retention_days']=0
    with pytest.raises(ValidationError):validate_settings(bad)
    bad=deepcopy(value);bad['timezone']='Mars/Olympus'
    with pytest.raises(ValidationError):validate_settings(bad)


def test_demo_never_changes_real_prices_or_exports(db,access):
    before=db.settings('a',access)
    seed_demo(db,'a',access)
    assert db.settings('a',access)==before
    assert summary(db,access)['prices']==[]
    assert summary(db,access,mode='demo')['prices'][0]['provider']=='simulated'


def test_retention_honors_persisted_workspace_settings(tmp_path,access):
    db=Telemetry(tmp_path/'db')
    run(db,access)
    settings=db.settings('a',access);settings['retention_days']=100
    db.settings('a',access,settings)
    db.db.execute('UPDATE events SET received=?',(time.time()-60*86400,));db.db.commit();db.close()
    db=Telemetry(tmp_path/'db')
    assert len(db.events(Scope('a'),access))==1
    db.close()
