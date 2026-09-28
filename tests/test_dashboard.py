import json
import os
from pathlib import Path
import threading
import time
import urllib.request
import urllib.error
from http.cookiejar import CookieJar
import pytest
from agent_context_engine.dashboard import DashboardServer
from agent_context_engine.benchmark import seed_demo
from agent_context_engine.metrics import summarize
from agent_context_engine.telemetry import Scope


@pytest.fixture
def server(db,access):
    server=DashboardServer(0,db,access,'a','local-test-secret-123456')
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield server
    server.shutdown();server.server_close();thread.join()


def client(server):
    base=f'http://127.0.0.1:{server.server_port}'
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    req=urllib.request.Request(base+'/api/login',data=json.dumps({'secret':'local-test-secret-123456'}).encode(),headers={'Content-Type':'application/json','Origin':base})
    opener.open(req).read()
    return base,opener


def test_dashboard_auth_host_origin_and_isolation(server):
    base=f'http://127.0.0.1:{server.server_port}'
    with pytest.raises(urllib.error.HTTPError) as exc:urllib.request.urlopen(base+'/api/summary')
    assert exc.value.code==401
    req=urllib.request.Request(base+'/',headers={'Host':'attacker.example'})
    with pytest.raises(urllib.error.HTTPError) as exc:urllib.request.urlopen(req)
    assert exc.value.code==403
    req=urllib.request.Request(base+'/api/login',data=b'{"secret":"local-test-secret-123456"}',headers={'Content-Type':'application/json','Origin':'https://evil.example'})
    with pytest.raises(urllib.error.HTTPError) as exc:urllib.request.urlopen(req)
    assert exc.value.code==403
    base,opener=client(server)
    with pytest.raises(urllib.error.HTTPError) as exc:opener.open(base+'/api/summary?workspace=unauthorized')
    assert exc.value.code==403
    with pytest.raises(urllib.error.HTTPError):opener.open(base+'/api/runs/missing')


def test_dashboard_api_sdk_exports_agree(server,db,access):
    seed_demo(db,'a',access)
    base,opener=client(server)
    query='?workspace=a&mode=demo&benchmark=arithmetic-25-percent'
    got=json.load(opener.open(base+'/api/summary'+query))
    scope=Scope('a','demo',filters={'benchmark':'arithmetic-25-percent'})
    expected=summarize(db.events(scope,access),scope,db.settings('a',access))
    for key in ('sample_size','input_tokens','output_tokens','cost','successes','comparisons','pairs','scope'):
        assert got[key]==expected[key]
    exported=json.load(opener.open(base+'/api/export.json'+query))
    assert exported['comparisons']==got['comparisons']
    csv=opener.open(base+'/api/export.csv'+query).read().decode()
    assert len(csv.splitlines())==4 and 'SYNTHETIC' in csv
    html=opener.open(base+'/api/report.html'+query).read().decode()
    assert 'SYNTHETIC' in html and 'workflow_reduction' in html
    rid=got['runs'][0]['run_id']
    trace=json.load(opener.open(base+'/api/runs/'+rid+query))
    assert trace['events'] and 'Unavailable' in trace['raw_content']
    assert json.load(opener.open(base+'/api/summary?workspace=a&mode=real'))['sample_size']==0


def test_dashboard_settings_and_readonly_routes(server):
    base,opener=client(server)
    settings=json.load(opener.open(base+'/api/settings?workspace=a'))
    settings['timezone']='America/Chicago'
    req=urllib.request.Request(base+'/api/settings?workspace=a',data=json.dumps(settings).encode(),headers={'Content-Type':'application/json','Origin':base})
    assert json.load(opener.open(req))['timezone']=='America/Chicago'
    with pytest.raises(urllib.error.HTTPError):opener.open(base+'/api/execute')
    response=opener.open(base+'/')
    assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
    assert response.headers['X-Content-Type-Options']=='nosniff'


@pytest.mark.skipif(os.environ.get('ACE_BROWSER_TESTS')!='1',reason='Set ACE_BROWSER_TESTS=1 with installed Chromium to run actual browser checks')
def test_browser_end_to_end(server,db,access):
    from playwright.sync_api import sync_playwright, expect
    seed_demo(db,'a',access)
    root=Path(__file__).resolve().parents[1]
    artifacts=root/'reports/browser';artifacts.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1100})
        errors=[]; console_errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:console_errors.append(m.text) if m.type=='error' else None)
        cdp=page.context.new_cdp_session(page)
        cdp.send('Performance.enable')
        before={m['name']:m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
        ui_start=time.perf_counter()
        page.goto(f'http://127.0.0.1:{server.server_port}')
        page.get_by_label('Local login secret',exact=True).fill('local-test-secret-123456')
        page.get_by_role('button',name='Open workspace').click()
        expect(page.get_by_text('Your evidence starts here.')).to_be_visible()
        expect(page.locator('#demo-banner')).to_be_hidden()
        page.get_by_label('Data mode',exact=True).select_option('demo')
        expect(page.locator('#demo-banner')).to_be_visible()
        expect(page.locator('#scope-label')).to_contain_text('21 runs')
        loaded={m['name']:m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
        initial_flow_seconds=time.perf_counter()-ui_start
        page.screenshot(path=str(artifacts/'overview-desktop.png'),full_page=True)
        page.locator('#benchmark').select_option('arithmetic-25-percent')
        expect(page.locator('#scope-label')).to_contain_text('3 runs')
        expect(page.get_by_text('25%',exact=True).first).to_be_visible()
        page.locator('.filters summary').click()
        page.locator('#arm').select_option('engine')
        expect(page.locator('#scope-label')).to_contain_text('1 runs')
        expect(page.get_by_text('40%',exact=True)).to_be_visible()
        page.locator('#arm').select_option('')
        page.locator('.filters summary').click()
        page.get_by_role('button',name='Runs and Traces',exact=False).click()
        page.get_by_role('button',name='arithmetic-25-percent',exact=True).first.click()
        expect(page.locator('#detail')).to_be_visible()
        expect(page.locator('#detail-content')).to_contain_text('Unavailable')
        page.get_by_role('button',name='Close trace').click()
        for label in ['Commands','Quality','Benchmarks','System Health']:
            page.locator('nav').get_by_role('button',name=label,exact=False).click()
            expect(page.locator('#content .panel').first).to_be_visible()
        with page.expect_download() as download:
            page.get_by_role('button',name='CSV',exact=True).click()
        downloaded=download.value
        downloaded.save_as(str(artifacts/'scoped-demo.csv'))
        assert len((artifacts/'scoped-demo.csv').read_text().splitlines())==4
        page.get_by_role('button',name='Workspace settings',exact=False).click()
        expect(page.locator('#settings')).to_be_visible()
        page.get_by_label('Display timezone').fill('UTC')
        page.get_by_role('button',name='Save settings').click()
        expect(page.locator('#settings')).to_be_hidden()
        page.locator('nav').get_by_role('button',name='Overview',exact=False).click()
        page.locator('#search').fill('not-a-real-run')
        expect(page.get_by_text('Your evidence starts here.')).to_be_visible()
        page.locator('#search').fill('')
        expect(page.locator('#scope-label')).to_contain_text('3 runs')
        page.set_viewport_size({'width':390,'height':844})
        page.screenshot(path=str(artifacts/'overview-mobile.png'),full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement !== document.body')
        assert errors==[],errors
        unexpected_console=[e for e in console_errors if '401 (Unauthorized)' not in e]
        assert unexpected_console==[],unexpected_console
        after={m['name']:m['value'] for m in cdp.send('Performance.getMetrics')['metrics']}
        (artifacts/'browser-result.json').write_text(json.dumps({'browser':browser.version,'page_errors':errors,'unexpected_console_errors':unexpected_console,'expected_auth_console_errors':console_errors,'resource_observation':{'sample_size':1,'initial_login_and_demo_flow_seconds':initial_flow_seconds,'page_cpu_task_seconds_after_load':loaded['TaskDuration']-before['TaskDuration'],'page_cpu_task_seconds_full_scripted_flow':after['TaskDuration']-before['TaskDuration'],'js_heap_bytes_after_load':loaded['JSHeapUsedSize'],'js_heap_increment_from_blank_bytes':loaded['JSHeapUsedSize']-before['JSHeapUsedSize'],'scope':'Chromium renderer TaskDuration and JS heap; scripted login/filter/view/export flow. Not OS process-tree CPU/RSS or passive polling benchmark.'},'checks':['login','real_empty','demo_label','filters','arithmetic_25','input_40','drilldown','six_views','scoped_csv','settings','search_empty','mobile_overflow','keyboard_focus']},indent=2))
        browser.close()
