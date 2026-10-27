// Real browser + Streamlit transport checks. No DOM-event mocks or state injection.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createServer} from 'node:net';
import {tmpdir} from 'node:os';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
const {chromium}=await import(process.env.CIRCUITSCOPE_PLAYWRIGHT_PATH||'playwright-core');
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const sources=['drawing_app.py','practice.py','practice_ui.py','course_methods.py','course_examples.py','course_ui.py','diagram_import.py','screenshot_import.py','screenshot_ui.py','canvas/editor.js','canvas/editor.html','canvas/editor.css','engine.py','circuit_model.py','topology.py','teaching.py','examples.py','opamp_examples.py','verification.py','spice_export.py','requirements.txt','package.json','tests/browser-smoke.mjs'];
const source_hashes=Object.fromEntries(await Promise.all(sources.map(async name=>[name,createHash('sha256').update(await readFile(join(root,name))).digest('hex')])));
const output=resolve(process.env.CIRCUITSCOPE_BROWSER_REPORT||join(root,'validation/browser_report.json'));
const args=process.argv.slice(2),urlFlag=args.indexOf('--url');
const rows=[],errors=[];let server,browser,page,logs='',failure;
const report={schema:'circuitscope.browser-check.v1',generated_utc:new Date().toISOString(),platform:process.platform,source_hashes,rows,
 scope:'Real Chromium mouse/keyboard/HTML drag-and-drop, Streamlit component transport, downloads, guided practice, course methods, screenshot upload/review (no live API call) and responsive layout checks at 1440, 1024 and 390 pixels. This is a headless browser run on the recorded platform; it does not establish native Windows, physical touch, Safari or Firefox behavior.'};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function freePort(){const s=createServer();await new Promise((ok,fail)=>{s.once('error',fail);s.listen(0,'127.0.0.1',ok);});const port=s.address().port;await new Promise(ok=>s.close(ok));return port;}
async function check(name,fn){const started=Date.now();try{await fn();rows.push({Check:name,Result:'PASS',Milliseconds:Date.now()-started});console.log('PASS',name);}catch(error){rows.push({Check:name,Result:'FAIL',Milliseconds:Date.now()-started,Details:error.message});throw error;}}
async function model(){return page.locator('#editor').evaluate(el=>structuredClone(el._editorUI.model));}
async function waitModel(predicate){const start=Date.now();while(Date.now()-start<10000){const m=await model();if(predicate(m))return m;await sleep(80);}throw Error('Drawing state did not reach the expected value.');}
async function synced(){for(let retry=0;retry<125;retry++){if(await page.locator('#editor').evaluate(el=>{const ui=el._editorUI;return ui&&ui.backendRevision===(ui.model.revision||0);}))return;await sleep(80);}throw Error('Python did not acknowledge the drawing revision.');}
async function select(label,value){const combo=page.getByRole('combobox',{name:label,exact:true});for(let retry=0;retry<10;retry++){await combo.click();try{await page.getByRole('option',{name:value,exact:true}).click({timeout:1000});return;}catch(error){if(retry===9)throw error;await page.keyboard.press('Escape');await sleep(100);}}}
async function solve(value){await page.getByRole('button',{name:'Solve drawing',exact:true}).click();await page.locator('[data-testid="stMetricValue"]').filter({hasText:new RegExp('^'+value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$')}).waitFor({timeout:15000});}
async function point(x,y){return page.locator('#canvas').evaluate((el,p)=>{const q=new DOMPoint(p.x,p.y).matrixTransform(el.getScreenCTM());const r=el.getBoundingClientRect();return{x:q.x,y:q.y,relative:{x:q.x-r.x,y:q.y-r.y}};},{x,y});}
async function place(kind,x,y,drag=false){
 await page.locator('#canvas').scrollIntoViewIfNeeded();
 if(drag){const p=await point(x,y);await page.locator(`[data-tool="${kind}"]`).dragTo(page.locator('#canvas'),{targetPosition:p.relative});}
 else{await page.locator(`[data-tool="${kind}"]`).click();const p=await point(x,y);await page.mouse.click(p.x,p.y);}
 await synced();
}
async function pin(key){const locator=page.locator(`[data-pin="${key}"] .pin-hit`);for(let retry=0;retry<20;retry++){await locator.waitFor({state:'visible'});const b=await locator.boundingBox();if(b)return{x:b.x+b.width/2,y:b.y+b.height/2};await sleep(50);}throw Error('Terminal did not remain visible: '+key);}
async function wire(a,b){
 await synced();
 await page.locator('#canvas').scrollIntoViewIfNeeded();const start=await pin(a),count=(await model()).wires.length;
 await page.mouse.move(start.x,start.y);await page.mouse.down();
 // Read the destination after pointerdown, as the browser may scroll a focused
 // canvas into view. This still uses the real pointer and terminal hit region.
 const end=await pin(b);await page.mouse.move(end.x,end.y,{steps:12});await page.mouse.up();await waitModel(m=>m.wires.length===count+1);await synced();
}
async function edit(id,fields){await page.locator(`[data-item="${id}"] .hit`).click();for(const [key,value]of Object.entries(fields)){const input=page.locator(key);if(key==='#opamp-mode')await input.selectOption(value);else await input.fill(String(value));}await page.locator('#apply').click();await synced();}
async function loadButton(label){const previous=await page.locator('#editor').elementHandle();await page.getByRole('button',{name:label,exact:true}).click();await page.waitForFunction(el=>!el.isConnected,previous,{timeout:15000});await page.locator('#canvas').waitFor();}
async function example(title){const panel=page.locator('[data-testid="stExpander"]').filter({has:page.getByText('Example circuits and solver checks',{exact:true})});const details=panel.locator('details');if(await details.getAttribute('open')===null)await panel.locator('summary').click();await select('Reference circuit',title);await loadButton('Load selected example');}

async function expand(title){const panel=page.locator('[data-testid="stExpander"]').filter({has:page.getByText(title,{exact:true})});if(await panel.locator('details').getAttribute('open')===null)await panel.locator('summary').click();}
async function courseExample(title){await expand('Circuits I method examples');await select('Course example',title);await loadButton('Load course example');}
async function method(name){await expand('Circuits I methods · explain this circuit');await select('Circuit method',name);await page.getByRole('button',{name:'Explain selected method',exact:true}).click();}
async function download(label){await synced();const pending=page.waitForEvent('download').then(file=>({file}),error=>({error}));await page.getByRole('button',{name:label,exact:true}).click();const result=await pending;if(result.error)throw result.error;const file=result.file;return{filename:file.suggestedFilename(),text:await readFile(await file.path(),'utf8')};}
async function layout(){const data=await page.locator('#editor').evaluate(el=>{const r=el.getBoundingClientRect(),p=el.querySelector('#properties').getBoundingClientRect();return{height:r.height,width:r.width,formBottom:p.bottom-r.top,clientWidth:document.documentElement.clientWidth,documentWidth:document.documentElement.scrollWidth};});assert.ok(Math.abs(data.height-820)<2,JSON.stringify(data));assert.ok(data.formBottom<=data.height+1,JSON.stringify(data));assert.ok(data.documentWidth<=data.clientWidth+2,JSON.stringify(data));}
try{
 let url;
 if(urlFlag>=0){url=args[urlFlag+1];if(!url)throw Error('Pass a URL after --url.');}
 else{const port=await freePort();url=`http://127.0.0.1:${port}`;const python=process.env.CIRCUITSCOPE_PYTHON||(process.platform==='win32'?'py':'python');server=spawn(python,['-m','streamlit','run','drawing_app.py','--global.developmentMode=false','--server.address','127.0.0.1','--server.port',String(port),'--server.headless','true','--browser.gatherUsageStats','false'],{cwd:root,env:process.env,stdio:['ignore','pipe','pipe']});server.on('error',error=>{logs+=error.message;});server.stdout.on('data',x=>logs+=x);server.stderr.on('data',x=>logs+=x);const deadline=Date.now()+30000;while(true){try{if((await fetch(url+'/_stcore/health')).ok)break;}catch{}if(Date.now()>deadline)throw Error('Streamlit did not start: '+logs.slice(-2000));await sleep(100);}}
 const executablePath=process.env.CIRCUITSCOPE_BROWSER_EXECUTABLE;
 const launch={headless:true};if(executablePath)launch.executablePath=executablePath;else launch.channel=process.env.CIRCUITSCOPE_BROWSER_CHANNEL||(process.platform==='win32'?'msedge':'chrome');
 if(process.env.CIRCUITSCOPE_BROWSER_SINGLE_PROCESS==='1')launch.args=['--no-sandbox','--disable-setuid-sandbox','--single-process','--no-zygote','--disable-dev-shm-usage','--disable-gpu'];
 browser=await chromium.launch(launch);report.browser=browser.version();
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
 await page.goto(url);await page.locator('#canvas').waitFor({timeout:30000});
 await check('Empty startup and bounded desktop editor',async()=>{assert.equal((await model()).items.length,0);await layout();});
 await check('Native inventory drag-and-drop and terminal wiring reach Python',async()=>{
  await place('V',220,300,true);await page.getByRole('combobox',{name:'Find',exact:true}).waitFor();await edit('V1',{'#part-value':12,'#label-1':'Vs'});
  await place('R',500,180,true);await edit('R1',{'#label-2':'Va'});await place('R',780,300);await page.locator('#rotate').click();await edit('R2',{'#part-value':2000});await place('GROUND',220,580);
  await wire('V1:1','R1:1');await wire('R1:2','R2:1');await wire('R2:2','V1:2');await wire('V1:2','GND1:1');
  await select('First node','Va');await select('Second / reference node','0');await solve('8 V');
  const file=await download('Save drawing JSON');const saved=JSON.parse(file.text);assert.equal(saved.items.length,4);assert.equal(saved.wires.length,4);assert.equal(saved.items.find(p=>p.id==='R2').value,2000);
 });
 await check('Explain-node click produces a live visual lesson',async()=>{await page.locator('[data-tool="explain"]').click();await page.locator('[data-pin="R2:1"] .pin-hit').click();await page.locator('#lesson-heading').filter({hasText:'Va'}).waitFor();assert.ok(await page.locator('#lesson-overlay').isVisible());assert.equal((await model()).wires.length,4);await page.locator('#canvas').press('Escape');});
 await check('Property edit and Undo invalidate and recalculate results',async()=>{await edit('R2',{'#part-value':1000});await waitModel(m=>m.items.find(p=>p.id==='R2').value===1000);await solve('6 V');await page.locator('#undo').click();await waitModel(m=>m.items.find(p=>p.id==='R2').value===2000);await solve('8 V');});
 await check('Wire branching creates one junction and an unloaded probe reads voltage',async()=>{
  await place('PORT',980,400);await page.locator('[data-tool="wire"]').click();let p=await point(660,180);await page.mouse.click(p.x,p.y);await page.locator('[data-pin="OUT1:1"] .pin-hit').click();await waitModel(m=>m.items.some(p=>p.type==='J')&&m.wires.length===6);await wire('OUT1:2','GND1:1');await page.locator('#canvas').press('Escape');
  await select('Find','Open-circuit voltage');await solve('8 V');await page.locator('.probe-reading').filter({hasText:'8.00000 V'}).waitFor();assert.equal((await model()).wires.length,7);
 });
 await check('Cancel a pending wire, clear, and Undo preserve saved drawing',async()=>{const before=await model();await page.locator('[data-pin="R1:1"] .pin-hit').click();await page.locator('#canvas').press('Escape');assert.equal((await model()).wires.length,before.wires.length);await page.locator('#clear').click();await waitModel(m=>m.items.length===0);await page.locator('#undo').click();await waitModel(m=>m.items.length===before.items.length);const saved=JSON.parse((await download('Save drawing JSON')).text);assert.equal(saved.wires.length,7);});
 await check('SPICE download contains the current full circuit',async()=>{await page.getByText('Export for LTspice / ngspice',{exact:true}).click();await page.getByRole('button',{name:'Prepare SPICE export',exact:true}).click();const file=await download('Download SPICE netlist');assert.match(file.filename,/\.cir$/);assert.match(file.text,/V_V1 .* 12\n/);assert.match(file.text,/R_R2 .* 2000\n/);assert.match(file.text,/\.op\n\.end/);});
 await check('Feedback op amp and removed-load overlay solve through the browser',async()=>{await example('Op amp · inverting amplifier (−2 V)');await select('Find','Open-circuit voltage');await select('Load to remove','RL');await solve('-2 V');assert.ok(await page.locator('[data-item="RL"].removed-load').isVisible());await page.locator('.probe-reading').filter({hasText:'-2.00000 V'}).waitFor();assert.equal(await page.locator('[data-flow="RL"]').count(),0);});
 await check('Open-loop HIGH, LOW and equality handling have no stale result',async()=>{await example('Open loop · comparator HIGH (5 V)');await solve('5 V');await page.locator('.opamp-state').filter({hasText:'HIGH'}).waitFor();await edit('V1',{'#part-value':1});await solve('0 V');await page.locator('.opamp-state').filter({hasText:'LOW'}).waitFor();await edit('V1',{'#part-value':2});await page.getByRole('button',{name:'Solve drawing',exact:true}).click();await page.getByText(/undefined at the switching threshold/).waitFor();assert.equal(await page.locator('.opamp-state').count(),0);assert.equal(await page.locator('[data-testid="stMetricValue"]').count(),0);});
 await check('Independent SPICE report can be inspected',async()=>{const box=page.getByRole('checkbox',{name:'Show independent SPICE verification',exact:true});if(!await box.isChecked())await page.getByText('Show independent SPICE verification',{exact:true}).click();await page.getByText(/29\/29 external DC configurations passed/).waitFor();});
 await check('Lesson and op-amp properties remain bounded at tablet and mobile widths',async()=>{await example('Op amp · inverting amplifier (−2 V)');await solve('-2 V');await page.locator('[data-item="U1"] .hit').click();for(const width of [1440,1024,390]){await page.setViewportSize({width,height:1000});await layout();assert.ok(await page.locator('#opamp-mode').isVisible());assert.ok(await page.locator('#apply').isVisible());}await page.setViewportSize({width:1440,height:1000});});
 await check('Guided practice checks units, reveals on success and rejects changed circuits',async()=>{
  await page.getByText('Guided practice · predict, check, explain',{exact:true}).click();
  await page.getByRole('button',{name:'Start practice question',exact:true}).click();
  await waitModel(m=>m.items.some(p=>p.id==='R2'&&p.value===2000)&&m.items.some(p=>p.id==='V1'&&p.value===12));
  assert.equal(await page.getByText('Worked answer',{exact:true}).count(),0);
  await page.getByRole('textbox',{name:'Your predicted answer',exact:true}).fill('7');
  await page.getByRole('button',{name:'Check my answer',exact:true}).click();await page.getByText(/Try again. Check the chosen units/).waitFor();
  assert.equal(await page.getByText('Worked answer',{exact:true}).count(),0);
  await page.getByRole('button',{name:'Show next hint',exact:true}).click();await page.getByText(/Hint 1: R1 and R2 carry the same current/).waitFor();
  await select('Answer unit','mV');await page.getByRole('textbox',{name:'Your predicted answer',exact:true}).fill('8000');
  await page.getByRole('button',{name:'Check my answer',exact:true}).click();await page.getByText('Worked answer',{exact:true}).waitFor();
  await page.getByText(/Practice progress: 1\/9 questions answered correctly/).waitFor();
  await edit('R2',{'#part-value':1000});await page.getByText(/The circuit changed. This practice answer key no longer applies/).waitFor();
  assert.equal(await page.getByRole('button',{name:'Check my answer',exact:true}).count(),0);
  assert.equal(await page.getByText('Worked answer',{exact:true}).count(),0);
 });
 await check('Practice reveal is optional and signed current is graded in milliamps',async()=>{
  await select('Practice question','4 · Signed branch current');await page.getByRole('button',{name:'Start practice question',exact:true}).click();
  await page.getByRole('button',{name:'Reveal worked answer',exact:true}).click();await page.getByText('Worked answer',{exact:true}).waitFor();
  await page.getByText(/Practice progress: 1\/9 questions answered correctly/).waitFor();
  await page.getByRole('textbox',{name:'Your predicted answer',exact:true}).fill('2.4');await page.getByRole('button',{name:'Check my answer',exact:true}).click();
  await page.getByText(/The magnitude matches. Check the reference direction/).waitFor();
  await page.getByRole('textbox',{name:'Your predicted answer',exact:true}).fill('-2.4');await page.getByRole('button',{name:'Check my answer',exact:true}).click();
  await page.getByText(/Practice progress: 2\/9 questions answered correctly/).waitFor();
 });
 await check('Supernode equations highlight the canvas and edits invalidate the overlay',async()=>{
  await courseExample('Supernode · floating source');await waitModel(m=>m.items.some(p=>p.id==='V1'&&p.value===6)&&!m.items.some(p=>p.id==='R3'));
  await method('Supernodes');await page.getByText('Supernode: Va, Vb',{exact:true}).waitFor();await page.locator('#method-overlay').waitFor();
  await edit('V1',{'#part-value':10});assert.equal(await page.locator('#method-overlay').count(),0);
 });
 await check('Superposition displays source contributions and a real circuit preview',async()=>{
  await courseExample('Superposition · voltage and current sources');await waitModel(m=>m.items.some(p=>p.id==='I1'));
  await method('Superposition');await page.getByText('Superposition contributions agree with the full linear solution.',{exact:true}).waitFor();
  await page.getByText(/Contribution sum: 9.3333333 V/).waitFor();assert.ok(await page.getByText('Preview one source contribution',{exact:true}).isVisible());
 });
 await check('Divider and source transformation preserve a loaded output',async()=>{
  await courseExample('Voltage divider and source transformation');await waitModel(m=>m.items.some(p=>p.id==='R2'&&p.value===2000)&&!m.items.some(p=>p.type==='I'));
  await method('Voltage divider');await page.getByText(/V\(Va\) = 8 V; full solver: 8 V/).waitFor();
  await method('Source transformation');await page.getByText(/External-node DC voltages match/).waitFor();
  await loadButton('Load transformed circuit');await waitModel(m=>m.items.some(p=>p.type==='I')&&!m.items.some(p=>p.type==='V'));
  await solve('8 V');
 });
 await check('Both summing amplifiers and a supported feedback cascade solve',async()=>{
  await courseExample('Summing amplifier · inverting');await waitModel(m=>m.items.some(p=>p.id==='V2'&&p.value===2));await method('Summing amplifiers');await page.getByText(/Predicted Vout: -4 V/).waitFor();await solve('-4 V');
  await courseExample('Summing amplifier · non-inverting');await waitModel(m=>m.items.some(p=>p.id==='V2'&&p.value===3));await method('Summing amplifiers');await page.getByText(/Predicted Vout: 4 V/).waitFor();await solve('4 V');
  await courseExample('Supported feedback · follower then gain stage');await waitModel(m=>m.items.some(p=>p.id==='U2'));await method('Feedback loops');await page.getByText(/U1: OUT \(Vbuf\) → direct wire/).waitFor();await solve('3 V');
 });
 await check('Screenshot upload and local review require approval before loading',async()=>{
  await expand('Import a circuit screenshot');
  const panel=page.locator('[data-testid="stExpander"]').filter({has:page.getByText('Import a circuit screenshot',{exact:true})});
  // A tiny valid PNG exercises upload, not image recognition. No API request is sent.
  await panel.locator('input[type="file"]').setInputFiles({name:'upload-check.png',mimeType:'image/png',buffer:Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jWWQAAAAASUVORK5CYII=','base64')});
  await page.getByRole('textbox',{name:'OpenAI API key',exact:true}).waitFor();
  await page.getByRole('button',{name:'Try import review demo (no API)',exact:true}).click();
  assert.ok(await page.getByRole('button',{name:'Load reviewed circuit',exact:true}).isDisabled());
  await page.getByText('I checked the values, source directions, reference node and every connection against the image',{exact:true}).click();
  await loadButton('Load reviewed circuit');await waitModel(m=>m.items.some(p=>p.id==='V1'&&p.value===12)&&m.items.length===4);
  await solve('8 V');await layout();
 });
 await check('No client JavaScript errors during the workflows',async()=>{assert.deepEqual(errors,[]);});
}catch(error){failure=error;console.error(error.stack||error);if(page&&process.env.CIRCUITSCOPE_BROWSER_DEBUG_DIR){const dir=resolve(process.env.CIRCUITSCOPE_BROWSER_DEBUG_DIR);await mkdir(dir,{recursive:true});await page.screenshot({path:join(dir,'failure.png'),fullPage:true}).catch(()=>{});await writeFile(join(dir,'failure.json'),JSON.stringify({model:await model().catch(()=>null),ui:await page.locator('#editor').evaluate(el=>({selected:el._editorUI?.selected,tool:el._editorUI?.tool,backendRevision:el._editorUI?.backendRevision,pending:el._editorUI?.pending})).catch(()=>null),logs},null,2));}}
finally{report.client_errors=errors;report.status=failure?'FAIL':'PASS';if(failure)report.failure=failure.message;await mkdir(dirname(output),{recursive:true});await writeFile(output,JSON.stringify(report,null,2));await browser?.close();if(server){server.kill('SIGTERM');await Promise.race([new Promise(ok=>server.once('exit',ok)),sleep(2000)]);}console.log(`${rows.filter(r=>r.Result==='PASS').length}/${rows.length} browser checks passed. Report: ${output}`);}
if(failure)process.exitCode=1;
