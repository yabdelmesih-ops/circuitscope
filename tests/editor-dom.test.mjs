// Real SVG DOM tests. Coordinates and animation frames are controlled;
// native browser layout, hit testing and Streamlit transport are not simulated.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import renderer, {pins,endpoint,wirePoints} from '../canvas/editor.js';
const {JSDOM}=await import(process.env.CIRCUITSCOPE_JSDOM_PATH || 'jsdom');
const html=readFileSync(new URL('../canvas/editor.html',import.meta.url),'utf8');
const sample=JSON.parse(readFileSync(new URL('../sample_drawing.json',import.meta.url)));

function harness(drawing=sample,lesson=null,nodeMap={},measurement=null,amplifiers=[]){
  const dom=new JSDOM(html),document=dom.window.document,svg=document.querySelector('#canvas');
  const frames=new Map(),updates=[],messages=[];let frameId=0,captured=null,cleanup;
  globalThis.AbortController=dom.window.AbortController;
  globalThis.DOMPoint=class {constructor(x,y){this.x=x;this.y=y;}matrixTransform(){return this;}};
  globalThis.requestAnimationFrame=fn=>{frames.set(++frameId,fn);return frameId;};
  globalThis.cancelAnimationFrame=id=>frames.delete(id);
  svg.getScreenCTM=()=>({inverse(){return {};}});
  svg.setPointerCapture=id=>{captured=id;};
  svg.hasPointerCapture=id=>captured===id;
  svg.releasePointerCapture=()=>{captured=null;};
  const q=s=>document.querySelector(s);
  function mount(model=drawing,overlay=lesson,readout=measurement,ampStates=amplifiers){cleanup?.();cleanup=renderer({parentElement:document.body,data:{drawing:structuredClone(model),node_map:nodeMap,lesson:overlay,measurement:readout,amplifiers:ampStates},setStateValue:(key,value)=>{messages.push({key,value:structuredClone(value)});if(key==='drawing')updates.push(structuredClone(value));}});}
  function pointer(type,target,x=0,y=0,id=1){const e=new dom.window.MouseEvent(type,{bubbles:true,clientX:x,clientY:y,button:0});Object.defineProperty(e,'pointerId',{value:id});target.dispatchEvent(e);}
  function clickPin(key){const p=endpoint(q('#editor')._editorUI.model,key);pointer('pointerdown',q(`[data-pin="${key}"] .pin-hit`),p.x,p.y);pointer('pointerup',svg,p.x,p.y);}
  function clickAt(x,y){pointer('pointerdown',svg,x,y);pointer('pointerup',svg,x,y);}
  const flush=()=>{const work=[...frames.values()];frames.clear();work.forEach(fn=>fn());};
  mount();
  return{q,svg,document,updates,messages,frames,mount,pointer,clickPin,clickAt,flush,close(){cleanup();dom.window.close();}};
}

test('dragging keeps SVG elements and inputs intact, then snaps and publishes once',()=>{
  const h=harness(),item=sample.items.find(i=>i.id==='R1');
  h.pointer('pointerdown',h.q('[data-item="R1"] .hit'),item.x,item.y);
  const body=h.q('[data-item="R1"]'),pin=h.q('[data-pin="R1:1"]');
  const wire=sample.wires.find(w=>w.a.startsWith('R1:')||w.b.startsWith('R1:'));
  const line=h.q(`[data-wire="${wire.id}"] .wire-line`),before=line.getAttribute('d');
  h.q('#part-value').value='2200';
  for(let i=1;i<=100;i++)h.pointer('pointermove',h.svg,item.x+i*.45,item.y+i*.25);
  assert.equal(h.frames.size,1,'movement coalesces into one animation frame');
  assert.equal(h.updates.length,0,'no backend update during dragging');
  h.flush();
  assert.equal(h.q('[data-item="R1"]'),body);
  assert.equal(h.q('[data-pin="R1:1"]'),pin);
  assert.equal(h.q(`[data-wire="${wire.id}"] .wire-line`),line);
  assert.equal(body.getAttribute('transform'),'translate(45,25)');
  assert.notEqual(line.getAttribute('d'),before);
  assert.equal(h.q('#part-value').value,'2200');
  h.pointer('pointerup',h.svg,item.x+45,item.y+25);
  assert.equal(h.updates.length,1);
  const moved=h.updates[0].items.find(i=>i.id==='R1');
  assert.equal(moved.x,item.x+40);assert.equal(moved.y,item.y+20);
  h.q('#undo').click();
  assert.equal(h.updates.at(-1).items.find(i=>i.id==='R1').x,item.x);
  h.close();
});

test('wire preview follows the pointer and completed wiring allows moving again',()=>{
  const emptyWires={...structuredClone(sample),wires:[]},h=harness(emptyWires);
  const start=pins(sample.items[0])[0];
  h.clickPin(start.key);
  h.pointer('pointermove',h.svg,800,450);h.flush();
  assert.equal(h.q('#wire-preview').getAttribute('d'),`M${start.x},${start.y} L800,${start.y} L800,460`);
  h.clickPin('R1:1');
  assert.equal(h.updates.at(-1).wires.length,1);
  assert.equal(h.svg.dataset.tool,'select');
  assert.equal(h.q('#wire-preview').getAttribute('d'),'');
  h.mount(emptyWires); // Simulate an older Python response arriving late.
  assert.equal(h.q('#editor')._editorUI.model.wires.length,1);
  h.close();
});

test('a stale backend echo cannot remove rapid edits or an in-progress drag',()=>{
  const h=harness();
  h.pointer('pointerdown',h.q('[data-item="R1"] .hit'),400,300);
  h.q('#rotate').click();const first=structuredClone(h.updates.at(-1));
  h.q('#rotate').click();const latest=structuredClone(h.updates.at(-1));
  h.mount(first);
  assert.deepEqual(h.q('#editor')._editorUI.model,latest);
  const item=latest.items.find(i=>i.id==='R1');
  h.pointer('pointerup',h.svg,400,300);
  h.pointer('pointerdown',h.q('[data-item="R1"] .hit'),item.x,item.y);
  h.pointer('pointermove',h.svg,item.x+43,item.y+27);h.flush();
  h.mount(h.q('#editor')._editorUI.drag.before);
  assert.equal(h.q('#editor')._editorUI.model.items.find(i=>i.id==='R1').x,item.x+43);
  h.pointer('pointermove',h.svg,item.x+48,item.y+31);h.flush();
  assert.equal(h.q('[data-item="R1"]').getAttribute('transform'),'translate(5,4)');
  h.pointer('pointerup',h.svg,item.x+48,item.y+31);
  assert.equal(h.updates.at(-1).items.find(i=>i.id==='R1').x,item.x+40);
  h.close();
});

test('pointer cancellation restores the diagram and does not publish a move',()=>{
  const h=harness(),item=sample.items.find(i=>i.id==='R1');
  h.pointer('pointerdown',h.q('[data-item="R1"] .hit'),item.x,item.y);
  h.pointer('pointermove',h.svg,item.x+73,item.y+21);h.flush();
  h.pointer('pointercancel',h.svg);
  assert.deepEqual(h.q('#editor')._editorUI.model,sample);
  assert.equal(h.q('#editor')._editorUI.drag,null);
  assert.equal(h.updates.length,0);h.close();
});

test('unfinished property edits survive a backend re-render',()=>{
  const h=harness(),item=sample.items.find(i=>i.id==='R1');
  h.pointer('pointerdown',h.q('[data-item="R1"] .hit'),item.x,item.y);
  h.pointer('pointerup',h.svg,item.x,item.y);
  h.q('#part-value').value='3300';
  h.q('#part-value').dispatchEvent(new h.document.defaultView.Event('input',{bubbles:true}));
  h.mount(sample);
  assert.equal(h.q('#part-value').value,'3300');
  h.q('#properties').dispatchEvent(new h.document.defaultView.Event('submit',{bubbles:true,cancelable:true}));
  assert.equal(h.updates.at(-1).items.find(i=>i.id==='R1').value,3300);
  h.close();
});

const lessonMap={'V1:1':'Vb','V1:2':'0','R1:1':'Vb','R1:2':'Va','R2:1':'Va','R2:2':'0','R3:1':'Va','R3:2':'Vb','GND1:1':'0'};
const teachingOverlay={node:'Va',step:1,branches:[
  {name:'R1',touching:true,outward:-.0048,direction:1,number:1,label:'4.8 mA',why:'Current enters Va through R1.'},
  {name:'R2',touching:true,outward:.0072,direction:1,number:2,label:'7.2 mA',why:'Current leaves Va through R2.'},
  {name:'R3',touching:true,outward:-.0024,direction:-1,number:3,label:'2.4 mA',why:'Current enters Va through R3.'},
],notes:[['One node has one potential.'],['R1 enters; R2 leaves; R3 enters.'],['Sum outward currents to zero.'],['7.2 mA enters and leaves.']]};

test('teaching marks the actual node, displays notes, and reverses negative-current arrows',()=>{
  const h=harness(sample,teachingOverlay,lessonMap);
  assert.equal(h.q('#lesson-notes').hidden,false);
  assert.match(h.q('#lesson-heading').textContent,/Follow the current.*Va/);
  assert.equal(h.document.querySelectorAll('.node-ring').length,3);
  assert.equal(h.document.querySelectorAll('[data-flow]').length,3);
  assert.equal(h.q('[data-flow="R3"]').dataset.direction,'-1');
  assert.match(h.q('[data-flow="R3"]').textContent,/3\. R3 · 2.4 mA/);
  assert.match(h.q('#lesson-cards').textContent,/R2 leaves/);
  h.mount(sample,{...teachingOverlay,step:0});
  assert.equal(h.document.querySelectorAll('[data-flow]').length,0);
  assert.equal(h.document.querySelectorAll('.node-ring').length,3);
  h.close();
});

test('a local electrical edit hides the previous lesson before the backend responds',()=>{
  const h=harness(sample,teachingOverlay,lessonMap);
  h.clickPin('V1:1');
  h.clickPin('R2:2');
  assert.equal(h.updates.length,1);
  assert.equal(h.q('#lesson-notes').hidden,true);
  assert.equal(h.q('#lesson-overlay'),null);
  h.mount(sample,teachingOverlay); // Stale response also cannot restore stale annotations.
  assert.equal(h.q('#lesson-overlay'),null);
  h.close();
});

test('drag-to-connect snaps a near miss to a terminal and publishes only on release',()=>{
  const m={...structuredClone(sample),wires:[]},h=harness(m),a=endpoint(m,'V1:1'),b=endpoint(m,'R1:1');
  h.pointer('pointerdown',h.q('[data-pin="V1:1"] .pin-hit'),a.x,a.y);
  h.pointer('pointermove',h.svg,b.x-10,b.y+5);h.flush();
  assert.equal(h.q('#wire-snap').getAttribute('visibility'),'visible');
  assert.equal(h.q('#wire-target-label').textContent,'R1:1');
  assert.equal(h.updates.length,0);
  h.pointer('pointerup',h.svg,b.x-10,b.y+5);
  assert.equal(h.updates.length,1);assert.equal(h.updates[0].wires[0].b,'R1:1');
  assert.equal(h.q('#editor')._editorUI.wireGesture,null);h.close();
});

test('corners can be placed, flipped, removed and finished while Wire mode stays active',()=>{
  const m={...structuredClone(sample),wires:[]},h=harness(m);
  h.q('[data-tool="wire"]').click();h.clickPin('V1:1');h.clickAt(900,600);
  assert.equal(h.updates.length,0);assert.equal(h.q('#editor')._editorUI.routeHistory.length,1);
  h.q('#bend-wire').click();assert.equal(h.q('#editor')._editorUI.bend,'vh');
  h.svg.dispatchEvent(new h.document.defaultView.KeyboardEvent('keydown',{key:'Backspace',bubbles:true}));
  assert.equal(h.q('#editor')._editorUI.route.length,0);
  h.clickAt(900,600);h.clickPin('R2:1');
  assert.equal(h.updates.length,1);assert.ok(h.updates[0].wires[0].via.length>0);
  const points=wirePoints(h.updates[0],h.updates[0].wires[0]);
  assert.ok(points.every((p,i)=>!i||p.x===points[i-1].x||p.y===points[i-1].y));
  assert.equal(h.svg.dataset.tool,'wire');
  h.clickPin('R2:2');h.clickPin('V1:2');
  assert.equal(h.updates.at(-1).wires.length,2);h.close();
});

test('branching creates a junction and both split wires in a single undoable edit',()=>{
  const m=structuredClone(sample);m.wires=m.wires.filter(w=>w.id==='w1');
  const h=harness(m);h.q('[data-tool="wire"]').click();h.clickAt(320,180);
  assert.equal(h.q('#editor')._editorUI.pending.kind,'wire');
  assert.equal(h.updates.length,0);assert.equal(h.q('#editor')._editorUI.model.items.length,m.items.length);
  h.clickPin('R2:1');
  assert.equal(h.updates.length,1);assert.equal(h.updates[0].wires.length,3);
  const junction=h.updates[0].items.find(i=>i.type==='J');
  assert.deepEqual([junction.x,junction.y],[320,180]);
  h.q('#undo').click();assert.deepEqual(h.updates.at(-1).items,m.items);assert.deepEqual(h.updates.at(-1).wires,m.wires);
  h.close();
});

test('Escape and lost pointer capture cancel a draft without leaving junctions',()=>{
  const m=structuredClone(sample);m.wires=m.wires.filter(w=>w.id==='w1');
  const h=harness(m);h.q('[data-tool="wire"]').click();h.clickAt(320,180);h.clickAt(900,600);
  h.svg.dispatchEvent(new h.document.defaultView.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
  assert.equal(h.updates.length,0);assert.deepEqual(h.q('#editor')._editorUI.model,m);
  assert.equal(h.q('#editor')._editorUI.pending,null);
  const p=endpoint(m,'V1:1');h.pointer('pointerdown',h.q('[data-pin="V1:1"] .pin-hit'),p.x,p.y);
  h.svg.dispatchEvent(new h.document.defaultView.Event('lostpointercapture'));
  assert.equal(h.q('#editor')._editorUI.pending,null);assert.equal(h.updates.length,0);h.close();
});

test('a pending route survives a backend re-render and right-click cancels it',()=>{
  const m={...structuredClone(sample),wires:[]},h=harness(m);
  h.clickPin('V1:1');h.clickAt(900,600);h.pointer('pointermove',h.svg,1000,400);h.flush();
  const preview=h.q('#wire-preview').getAttribute('d');h.mount(m);
  assert.equal(h.q('#wire-preview').getAttribute('d'),preview);
  h.svg.dispatchEvent(new h.document.defaultView.MouseEvent('contextmenu',{bubbles:true,cancelable:true}));
  assert.equal(h.q('#editor')._editorUI.pending,null);assert.equal(h.updates.length,0);h.close();
});

test('Explain mode requests a terminal lesson without creating a wire or moving the part',()=>{
  const h=harness();h.q('[data-tool="explain"]').click();h.clickPin('R1:2');
  assert.equal(h.messages.length,1);assert.equal(h.messages[0].key,'node_request');
  assert.deepEqual(h.messages[0].value,{pin:'R1:2',revision:0,sequence:1});
  assert.equal(h.updates.length,0);assert.deepEqual(h.q('#editor')._editorUI.model,sample);
  assert.equal(h.q('#editor')._editorUI.pending,null);assert.equal(h.q('#editor')._editorUI.drag,null);
  h.mount(sample);h.clickPin('V1:1');
  assert.equal(h.messages.at(-1).value.sequence,2);h.close();
});

test('a wire click explains one of its connected terminals and a component body requests a precise end',()=>{
  const h=harness();h.svg.dispatchEvent(new h.document.defaultView.KeyboardEvent('keydown',{key:'e',bubbles:true}));
  assert.equal(h.svg.dataset.tool,'explain');
  h.pointer('pointerdown',h.q('[data-wire="w2"] .wire-hit'),650,180);
  assert.equal(h.messages[0].value.pin,'R1:2');
  h.pointer('pointerdown',h.q('[data-item="R2"] .hit'),760,300);
  assert.equal(h.messages.length,1);assert.match(h.q('#status').textContent,/terminal circle or wire/);
  h.pointer('pointerdown',h.q('[data-item="GND1"] .hit'),200,540);
  assert.equal(h.messages.at(-1).value.pin,'GND1:1');
  assert.equal(h.updates.length,0);h.close();
});

test('op amp placement exposes three labeled terminals and configurable output limits',()=>{
  const h=harness({schema:'circuitscope.canvas.v1',items:[],wires:[]});
  h.q('[data-tool="OPAMP"]').click();h.clickAt(600,320);
  const u=h.updates.at(-1).items[0];
  assert.equal(u.id,'U1');assert.equal(u.type,'OPAMP');assert.equal(pins(u).length,3);
  assert.equal(h.q('[data-pin="U1:1"] text').textContent,'+');
  assert.equal(h.q('[data-pin="U1:2"] text').textContent,'−');
  assert.equal(h.q('[data-pin="U1:3"] text').textContent,'OUT');
  assert.equal(h.q('#label-3-field').hidden,false);assert.equal(h.q('#rail-min').value,'-15');
  h.q('#label-3').value='Vout';h.q('#rail-min').value='0';h.q('#rail-max').value='5';
  h.q('#rail-max').dispatchEvent(new h.document.defaultView.Event('input',{bubbles:true}));
  h.mount(h.updates.at(-1));assert.equal(h.q('#rail-max').value,'5');
  h.q('#apply').click();
  const saved=h.updates.at(-1).items[0];
  assert.equal(saved.label3,'Vout');assert.equal(saved.v_min,0);assert.equal(saved.v_max,5);
  const before=h.updates.length;h.q('#rail-min').value='6';h.q('#apply').click();
  assert.equal(h.updates.length,before);assert.match(h.q('#status').textContent,/minimum below maximum/);
  h.close();
});

test('op amp output can wire to a probe and rotation preserves all terminal identities',()=>{
  const model={schema:'circuitscope.canvas.v1',wires:[],items:[
    {id:'U1',type:'OPAMP',x:500,y:300,rotation:0,v_min:-15,v_max:15},
    {id:'OUT1',type:'PORT',x:900,y:300,rotation:0}]};
  const h=harness(model);
  h.clickPin('U1:3');h.clickPin('OUT1:1');
  assert.equal(h.updates.at(-1).wires[0].a,'U1:3');assert.equal(h.updates.at(-1).wires[0].b,'OUT1:1');
  h.pointer('pointerdown',h.q('[data-item="U1"] .hit'),500,300);
  h.pointer('pointerup',h.svg,500,300);h.q('#rotate').click();
  assert.deepEqual(pins(h.updates.at(-1).items[0]).map(p=>p.key),['U1:1','U1:2','U1:3']);
  assert.equal(endpoint(h.updates.at(-1),'U1:3').y,360);
  assert.equal(h.updates.at(-1).wires.length,1);
  h.close();
});

test('output readout shows an open load and local edits immediately clear the old measurement',()=>{
  const model=structuredClone(sample);model.items.push({id:'OUT1',type:'PORT',x:960,y:300,rotation:0});
  const measurement={node1:'Va',node2:'0',voltage:12,removedLoad:'R2',portId:'OUT1'};
  const h=harness(model,null,{},measurement);
  assert.equal(h.q('#measurement-info').hidden,false);
  assert.match(h.q('#measurement-info').textContent,/Probe current: 0 A/);
  assert.ok(h.q('[data-item="R2"].removed-load'));
  assert.match(h.q('[data-item="R2"]').textContent,/OPEN/);
  assert.match(h.q('.probe-reading').textContent,/12.0000 V/);
  h.q('[data-tool="R"]').click();h.clickAt(960,540);
  assert.equal(h.q('#measurement-info').hidden,true);assert.equal(h.q('.probe-reading'),null);
  assert.equal(h.q('.removed-load'),null);
  h.mount(model,null,measurement); // Delayed response is older than the local edit.
  assert.equal(h.q('#measurement-info').hidden,true);assert.equal(h.q('.probe-reading'),null);
  h.close();
});

test('open-loop mode edits preserve drafts, save with the circuit and undo to feedback',()=>{
  const h=harness({schema:'circuitscope.canvas.v1',items:[],wires:[]});
  h.q('[data-tool="OPAMP"]').click();h.clickAt(600,320);
  assert.equal(h.q('#opamp-mode').value,'feedback');
  h.q('#label-3').value='Vout';h.q('#rail-min').value='0';h.q('#rail-max').value='5';
  h.q('#opamp-mode').value='open_loop';
  h.q('#opamp-mode').dispatchEvent(new h.document.defaultView.Event('change',{bubbles:true}));
  assert.match(h.q('#part-help').textContent,/no feedback/);
  h.mount(h.updates.at(-1));
  assert.equal(h.q('#opamp-mode').value,'open_loop');assert.equal(h.q('#label-3').value,'Vout');
  assert.equal(h.q('#rail-max').value,'5');
  h.q('#apply').click();
  assert.equal(h.updates.at(-1).items[0].mode,'open_loop');
  assert.equal(h.updates.at(-1).items[0].v_min,0);
  assert.equal(h.q('.opamp-mode-label').textContent,'OPEN LOOP');
  h.q('#undo').click();
  assert.equal(h.q('#editor')._editorUI.model.items[0].mode,'feedback');
  assert.equal(h.q('.opamp-mode-label'),null);
  h.close();
});

test('HIGH/LOW annotations require current results and cannot return from a stale echo',()=>{
  const model={schema:'circuitscope.canvas.v1',wires:[],items:[{id:'U1',type:'OPAMP',x:600,y:320,rotation:0,mode:'open_loop',v_min:0,v_max:5}]};
  const states=[{name:'U1',state:'HIGH',voltage:5}];
  const h=harness(model,null,{},null,states);
  assert.match(h.q('[data-opamp-state="U1"]').textContent,/HIGH.*5.000 V/);
  h.pointer('pointerdown',h.q('[data-item="U1"] .hit'),600,320);h.pointer('pointerup',h.svg,600,320);
  h.q('#rail-max').value='3.3';h.q('#apply').click();
  assert.equal(h.q('.opamp-state'),null);
  h.mount(model,null,null,states);
  assert.equal(h.q('.opamp-state'),null);
  const latest=h.q('#editor')._editorUI.model;
  h.mount(latest,null,null,[{name:'U1',state:'HIGH',voltage:3.3}]);
  assert.match(h.q('.opamp-state').textContent,/HIGH.*3.300 V/);
  h.close();
});

test('a real Streamlit-style data update retires old handlers without unmounting',()=>{
  const empty={schema:'circuitscope.canvas.v1',items:[],wires:[]};
  const h=harness(empty),updates=[];
  // Streamlit calls the renderer on data updates without first calling the
  // unmount cleanup. Earlier tests mounted after cleanup and missed this bug.
  const cleanup=renderer({parentElement:h.document.body,data:{drawing:structuredClone(empty)},setStateValue:(key,value)=>updates.push({key,value:structuredClone(value)})});
  h.q('[data-tool="R"]').click();h.clickAt(600,320);
  assert.equal(updates.length,1,'one action must publish exactly once');
  assert.equal(h.updates.length,0,'the old renderer must no longer receive events');
  assert.equal(h.q('#editor')._editorUI.model.items.length,1);
  assert.equal(h.q('#editor')._editorUI.model.items[0].id,'R1');
  cleanup();h.close();
});


test('wire gestures keep the property panel and delayed teaching layout steady',()=>{
  const h=harness(sample),item=sample.items.find(i=>i.id==='R1');
  h.pointer('pointerdown',h.q('[data-item="R1"] .hit'),item.x,item.y);
  h.pointer('pointerup',h.svg,item.x,item.y);
  assert.equal(h.q('#property-fields').hidden,false);
  h.clickPin('R1:1');
  assert.equal(h.q('#property-fields').hidden,false,'starting a wire must not collapse the form');
  h.mount(sample,teachingOverlay);
  assert.equal(h.q('#lesson-notes').hidden,true,'a backend result must not resize an active route');
  h.clickPin('R2:1');
  assert.equal(h.updates.at(-1).wires.length,sample.wires.length+1);
  h.mount(h.updates.at(-1),teachingOverlay);
  assert.equal(h.q('#lesson-notes').hidden,false,'fresh results can appear after completion');
  h.close();
});
