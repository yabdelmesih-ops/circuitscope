import{test}from'node:test';import assert from'node:assert/strict';import{readFileSync}from'node:fs';
import renderer,{pins,wirePoints,chooseBend,flowArrow}from'../canvas/editor.js';
const sample=JSON.parse(readFileSync(new URL('../sample_drawing.json',import.meta.url)));
test('current arrows reverse with current sign and rotate with the part',()=>{const item={id:'R1',type:'R',x:200,y:200,rotation:0};assert.deepEqual(flowArrow(item,1).points,[{x:160,y:226},{x:240,y:226}]);assert.deepEqual(flowArrow(item,-1).points,[{x:240,y:226},{x:160,y:226}]);item.rotation=90;assert.deepEqual(flowArrow(item,1).points,[{x:174,y:160},{x:174,y:240}]);});
test('90-degree source rotation puts positive pin above negative',()=>{const p=pins(sample.items[0]);assert.deepEqual([p[0].x,p[0].y],[200,260]);assert.deepEqual([p[1].x,p[1].y],[200,340]);});
test('wire endpoint follows a component after it moves',()=>{const model=structuredClone(sample),wire=model.wires[0];const before=wirePoints(model,wire);model.items[0].x+=100;const after=wirePoints(model,wire);assert.equal(after[0].x,before[0].x+100);assert.equal(after[0].y,before[0].y);});
test('automatic elbow chooses a route avoiding an unrelated pin',()=>{const model={items:[{id:'A',type:'J',x:100,y:100},{id:'B',type:'J',x:300,y:300},{id:'X',type:'J',x:300,y:100}],wires:[]};assert.equal(chooseBend(model,'A:1','B:1'),'vh');});
test('all scoped controls exist in static HTML or generated SVG',()=>{const html=readFileSync(new URL('../canvas/editor.html',import.meta.url),'utf8'),js=readFileSync(new URL('../canvas/editor.js',import.meta.url),'utf8');for(const m of js.matchAll(/q\('#([^']+)'\)/g))assert.ok((html+js).includes(`id="${m[1]}"`),m[1]);});
// Minimal DOM harness for renderer events; no claim of native browser QA.
class Element{constructor(){this.listeners={};this.value='';this.classList={toggle(){}};this.dataset={};this._html='';}addEventListener(e,f){this.listeners[e]=f;}set innerHTML(v){this._html=v;}get innerHTML(){return this._html;}setPointerCapture(){}getScreenCTM(){return{inverse(){return{};}};}}
const ids=['editor','canvas','status','property-fields','selected-name','part-value','label-1','label-2','label-2-field','undo','rotate','delete','clear','inventory','properties','lesson-notes','lesson-heading','lesson-cards','cancel-wire','bend-wire','measurement-info','label-3-field','label-3','rail-min-field','rail-max-field','rail-min','rail-max','part-help','opamp-mode-field','opamp-mode'];
function harness(){const elements=Object.fromEntries(ids.map(id=>[id,new Element()])),updates=[],buttons=['select','wire','R','V','I','GROUND','J'].map(tool=>({dataset:{tool},classList:{toggle(){}}}));const parentElement={querySelector:s=>elements[s.slice(1)],querySelectorAll:()=>buttons};globalThis.DOMPoint=class{constructor(x,y){this.x=x;this.y=y;}matrixTransform(){return this;}};const cleanup=renderer({parentElement,data:{drawing:structuredClone(sample),node_map:{'R2:1':'Va'}},setStateValue:(key,value)=>updates.push(structuredClone(value))});return{elements,updates,cleanup,parentElement};}
const target=map=>({closest:s=>map[s]||null});
test('inventory drop sends a new component to Python',()=>{const h=harness();h.elements.canvas.listeners.drop({preventDefault(){},dataTransfer:{getData(){return'I';}},clientX:900,clientY:500});const last=h.updates.at(-1);assert.ok(last.items.some(i=>i.id==='I1'&&i.type==='I'));assert.equal(h.elements['part-value'].value,.001);h.cleanup();});
test('pin clicks create an explicit wire and retain its IDs',()=>{const h=harness();h.elements.canvas.listeners.drop({preventDefault(){},dataTransfer:{getData(){return'I';}},clientX:900,clientY:500});for(const pin of ['I1:1','GND1:1']){const e={button:0,pointerId:1,clientX:0,clientY:0,preventDefault(){},target:target({'[data-pin]':{dataset:{pin}}})};h.elements.canvas.listeners.pointerdown(e);h.elements.canvas.listeners.pointerup(e);}const wire=h.updates.at(-1).wires.at(-1);assert.equal(wire.a,'I1:1');assert.equal(wire.b,'GND1:1');h.cleanup();});
test('property edits and undo round-trip values',()=>{const h=harness();h.elements.canvas.listeners.drop({preventDefault(){},dataTransfer:{getData(){return'R';}},clientX:900,clientY:500});h.elements['part-value'].value='2200';h.elements.properties.listeners.submit({preventDefault(){}});assert.equal(h.updates.at(-1).items.at(-1).value,2200);h.elements.undo.listeners.click();assert.equal(h.updates.at(-1).items.at(-1).value,1000);h.cleanup();});
test('op amp current arrow uses output only and reverses when sourcing current',()=>{
  const item={id:'U1',type:'OPAMP',x:600,y:320,rotation:0};
  const positive=flowArrow(item,1),negative=flowArrow(item,-1);
  assert.ok(positive.points.every(p=>p.x>item.x),'no input arrow');
  assert.ok(positive.points[0].x>positive.points[1].x,'positive current enters output');
  assert.deepEqual(negative.points,[...positive.points].reverse());
  item.rotation=90;const rotated=flowArrow(item,1);
  assert.ok(rotated.points.every(p=>p.y>item.y));
  assert.ok(rotated.points[0].y>rotated.points[1].y);
});
