// This file draws and edits a diagram. Python determines electrical nodes.
export function pins(item) {
  const offsets = item.type === 'GROUND' ? [[0, -20]] : item.type === 'J' ? [[0, 0]] : item.type === 'OPAMP' ? [[-60,-20],[-60,20],[60,0]] : [[-40, 0], [40, 0]];
  const angle = (item.rotation || 0) * Math.PI / 180;
  const c = Math.round(Math.cos(angle)), s = Math.round(Math.sin(angle));
  return offsets.map(([x, y], i) => ({key: `${item.id}:${i + 1}`, x: item.x + x*c - y*s, y: item.y + x*s + y*c}));
}
export function endpoint(model, key) {
  const item = model.items.find(p => p.id === key.split(':')[0]);
  return item ? pins(item).find(p => p.key === key) : null;
}
export function wirePoints(model, wire) {
  const a = endpoint(model, wire.a), b = endpoint(model, wire.b);
  if (!a || !b) return [];
  return routePoints([a,...(wire.via||[]),b],wire.bend);
}
export function routePoints(anchors,bend='hv') {
  const points=[];
  for(const end of anchors){
    const a=points.at(-1);
    if(a&&a.x!==end.x&&a.y!==end.y)points.push(bend==='vh'?{x:a.x,y:end.y}:{x:end.x,y:a.y});
    points.push({x:end.x,y:end.y});
  }
  const clean=[];
  for(const p of points){
    if(clean.length&&clean.at(-1).x===p.x&&clean.at(-1).y===p.y)continue;
    while(clean.length>1){const a=clean.at(-2),b=clean.at(-1);if((a.x===b.x&&b.x===p.x&&(b.y-a.y)*(p.y-b.y)>=0)||(a.y===b.y&&b.y===p.y&&(b.x-a.x)*(p.x-b.x)>=0))clean.pop();else break;}
    clean.push(p);
  }
  return clean;
}
export function projectOnWire(model,wire,point) {
  const points=wirePoints(model,wire);let best=null;
  for(let i=0;i<points.length-1;i++){
    const a=points[i],b=points[i+1],dx=b.x-a.x,dy=b.y-a.y,den=dx*dx+dy*dy;
    const t=den?Math.max(0,Math.min(1,((point.x-a.x)*dx+(point.y-a.y)*dy)/den)):0;
    const p={x:a.x+t*dx,y:a.y+t*dy},distance=Math.hypot(point.x-p.x,point.y-p.y);
    if(!best||distance<best.distance)best={point:p,distance,segment:i,points};
  }
  return best;
}
export function findWireTarget(model,point,radius=22,onlyWire=null) {
  let pin=null;
  for(const item of model.items)for(const p of pins(item)){
    const distance=Math.hypot(point.x-p.x,point.y-p.y);
    if(distance<=radius&&(!pin||distance<pin.distance))pin={kind:'pin',key:p.key,point:{x:p.x,y:p.y},distance};
  }
  if(pin)return pin;
  let best=null;
  for(const wire of model.wires){
    if(onlyWire&&wire.id!==onlyWire)continue;
    const hit=projectOnWire(model,wire,point);
    if(!hit||hit.distance>radius*.65||best&&hit.distance>=best.distance)continue;
    const a=hit.points[hit.segment],b=hit.points[hit.segment+1],p={...hit.point};
    if(a.x===b.x)p.y=Math.max(Math.min(a.y,b.y),Math.min(Math.max(a.y,b.y),Math.round(p.y/20)*20));
    else p.x=Math.max(Math.min(a.x,b.x),Math.min(Math.max(a.x,b.x),Math.round(p.x/20)*20));
    best={kind:'wire',wireId:wire.id,point:p,distance:hit.distance};
  }
  return best;
}
function nextId(items,prefix) {
  let n=1;const used=new Set(items.map(p=>p.id.toLowerCase()));while(used.has((prefix+n).toLowerCase()))n++;
  return prefix+n;
}
export function connectWireTargets(original,start,end,via=[],bend='hv') {
  if(via.length>200||via.some(p=>!Number.isFinite(p.x)||!Number.isFinite(p.y)||p.x<0||p.x>1140||p.y<0||p.y>720))throw Error('Keep the route inside the canvas and below 200 routing points.');
  if(start.kind==='pin'&&end.kind==='pin'&&start.key===end.key)throw Error('Choose a different terminal.');
  if(start.kind==='wire'&&end.kind==='wire'&&start.wireId===end.wireId)throw Error('Those points are already on the same wire.');
  const model=JSON.parse(JSON.stringify(original));
  function attach(target){
    if(target.kind==='pin'){
      if(!endpoint(model,target.key))throw Error('That terminal no longer exists.');
      return target.key;
    }
    const wire=model.wires.find(w=>w.id===target.wireId),hit=wire&&projectOnWire(model,wire,target.point);
    if(!hit||hit.distance>1e-6)throw Error('That wire moved. Choose its new position.');
    const points=hit.points,p=hit.point;
    for(const key of [wire.a,wire.b]){const terminal=endpoint(model,key);if(Math.hypot(terminal.x-p.x,terminal.y-p.y)<1e-6)return key;}
    const id=nextId(model.items,'J'),key=id+':1';
    model.items.push({id,type:'J',x:p.x,y:p.y,rotation:0,label1:'',label2:''});
    const first=routePoints([...points.slice(0,hit.segment+1),p]),second=routePoints([p,...points.slice(hit.segment+1)]);
    const tail={...wire,id:nextId(model.wires,'w'),a:key,via:second.slice(1,-1)};
    wire.b=key;wire.via=first.slice(1,-1);model.wires.push(tail);
    return key;
  }
  const a=attach(start),b=attach(end);
  if(a===b||model.wires.some(w=>w.a===a&&w.b===b||w.a===b&&w.b===a))throw Error('Those terminals are already connected by a wire.');
  const wire={id:nextId(model.wires,'w'),a,b,bend,via:via.map(p=>({x:p.x,y:p.y}))};
  model.wires.push(wire);
  if(model.items.length>60||model.wires.length>200)throw Error('Circuit limit: 60 items and 200 wire segments.');
  return model;
}
function onLine(p, a, b) {
  return a.x===b.x && p.x===a.x && p.y>=Math.min(a.y,b.y) && p.y<=Math.max(a.y,b.y) ||
    a.y===b.y && p.y===a.y && p.x>=Math.min(a.x,b.x) && p.x<=Math.max(a.x,b.x);
}
export function chooseBend(model, a, b) {
  const start=endpoint(model,a),end=endpoint(model,b),all=model.items.flatMap(pins);
  const score=bend=>{const r=wirePoints(model,{a,b,bend});return all.filter(p=>p.key!==a&&p.key!==b&&r.some((end,i)=>i&&onLine(p,r[i-1],end))).length;};
  return start && end && score('vh') < score('hv') ? 'vh' : 'hv';
}
export function flowArrow(item, direction) {
  if(item.type==='OPAMP'){
    const angle=(item.rotation||0)*Math.PI/180,c=Math.round(Math.cos(angle)),s=Math.round(Math.sin(angle));
    const rotate=(x,y)=>({x:item.x+x*c-y*s,y:item.y+x*s+y*c});
    const points=[rotate(100,26),rotate(45,26)];
    return{points:direction<0?points.slice().reverse():points,label:rotate(90,48)};
  }
  const [p1,p2]=pins(item),dx=p2.x-p1.x,dy=p2.y-p1.y,length=Math.hypot(dx,dy);
  const nx=-dy/length,ny=dx/length;
  const a={x:p1.x+nx*26,y:p1.y+ny*26},b={x:p2.x+nx*26,y:p2.y+ny*26};
  return{points:direction<0?[b,a]:[a,b],label:{x:item.x+nx*46,y:item.y+ny*46}};
}
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = value => JSON.parse(JSON.stringify(value));
const path = points => points.map((p,i)=>`${i?'L':'M'}${p.x},${p.y}`).join(' ');

// Streamlit calls this renderer and supplies setStateValue to send data to Python.
export default function({parentElement, data, setStateValue}) {
  const q = selector => parentElement.querySelector(selector);
  const root=q('#editor'), svg=q('#canvas'), controller=new AbortController();
  // Streamlit calls the renderer again on data updates; its returned cleanup
  // runs on unmount, not before every update. Retire the previous handlers and
  // pending animation frame ourselves while retaining the shared editor state.
  root._editorCleanup?.();
  const listen=(element,event,fn)=>element.addEventListener(event,fn,{signal:controller.signal});
  const ui=root._editorUI || {tool:'select',selected:null,pending:null,drag:null,history:[]};
  root._editorUI=ui;
  if(typeof ui.pending==='string')ui.pending={kind:'pin',key:ui.pending};
  ui.route=ui.route||[];ui.routeHistory=ui.routeHistory||[];ui.bend=ui.bend||'hv';
  // A delayed Python echo must not replace edits made since it was sent.
  const incoming=clone(data.drawing);
  ui.backendRevision=incoming.revision||0;
  let model=ui.model && (ui.drag||ui.wireGesture||(ui.model.revision||0)>(incoming.revision||0)) ? ui.model : incoming;
  ui.model=model;
  ui.revision=Math.max(ui.revision||0,model.revision||0);
  let nodeMap=data.node_map || {},frame=null,cursor=ui.cursor||null;
  const cleanup=()=>{controller.abort();if(frame!==null)cancelAnimationFrame(frame);if(root._editorCleanup===cleanup)delete root._editorCleanup;};
  root._editorCleanup=cleanup;
  // A delayed result must not open a notes panel or measurement banner halfway
  // through a gesture: that changes the SVG transform under the pointer.
  const annotations=ui.drag||ui.pending||ui.wireGesture?ui.annotations||{}:data;
  let lesson=(model.revision||0)>(incoming.revision||0)?null:annotations.lesson||null;
  let measurement=(model.revision||0)>(incoming.revision||0)?null:annotations.measurement||null;
  let amplifiers=(model.revision||0)>(incoming.revision||0)?[]:annotations.amplifiers||[];
  const snap=n=>Math.round(n/20)*20;
  const tell=text=>q('#status').textContent=text;
  const history=()=>{ui.history.push(clone(model));if(ui.history.length>40)ui.history.shift();};
  const commit=()=>{model.revision=++ui.revision;ui.model=model;lesson=null;measurement=null;amplifiers=[];render();setStateValue('drawing',clone(model));};
  const getItem=()=>model.items.find(i=>i.id===ui.selected);

  function setTool(tool) {
    cancelWire(false,false);ui.tool=tool;ui.pending=null;svg.dataset.tool=tool;
    if(tool==='explain')ui.selected=null;
    parentElement.querySelectorAll('[data-tool]').forEach(b=>b.classList.toggle('active',b.dataset.tool===tool));
    tell(tool==='explain'?'Click a wire or terminal to see its node voltage, current arrows and teaching notes. E selects Explain; Esc returns to move.':tool==='wire'?'Drag or click between terminals. Click empty space for corners; click a wire to branch. Esc cancels.':tool==='select'?'Drag parts to move. W selects Wire; E selects Explain node.':`Click the grid to place ${tool}.`);
    render();
  }
  function place(type, position) {
    if(model.items.length>=60){tell('Maximum 60 items.');return;}
    history();let n=1,prefix=type==='GROUND'?'GND':type==='OPAMP'?'U':type==='PORT'?'OUT':type;
    while(model.items.some(i=>i.id===prefix+n))n++;
    const item={id:prefix+n,type,x:Math.max(60,Math.min(1080,snap(position.x))),y:Math.max(60,Math.min(660,snap(position.y))),rotation:['V','I'].includes(type)?90:0,label1:'',label2:''};
    if(['R','V','I'].includes(type))item.value=type==='R'?1000:type==='V'?5:.001;
    if(type==='OPAMP'){item.v_min=-15;item.v_max=15;item.label3='';item.mode='feedback';}
    model.items.push(item);ui.selected=item.id;setTool('select');commit();
  }
  function explainNode(event){
    const terminal=event.target.closest('[data-pin]'),wire=event.target.closest('[data-wire]'),component=event.target.closest('[data-item]');
    let pin=terminal?.dataset.pin;
    if(!pin&&wire)pin=model.wires.find(w=>w.id===wire.dataset.wire)?.a;
    if(!pin&&component){const item=model.items.find(i=>i.id===component.dataset.item);if(item&&pins(item).length===1)pin=pins(item)[0].key;}
    if(!pin&&!component){const target=targetAt(event,position(event,false));if(target)pin=target.kind==='pin'?target.key:model.wires.find(w=>w.id===target.wireId)?.a;}
    if(!pin){tell('Choose a terminal circle or wire. A two-terminal component has a different node at each end.');return;}
    ui.pickSequence=(ui.pickSequence||0)+1;
    tell(`Explaining ${pin}. The circuit and its wiring stay in place.`);
    setStateValue('node_request',{pin,revision:model.revision||0,sequence:ui.pickSequence});
  }
  function wireStart(){return ui.pending?.kind==='pin'?endpoint(model,ui.pending.key):ui.pending?.point;}
  function draftPoints(end){const start=wireStart();return start?routePoints([start,...ui.route,end],ui.bend):[];}
  function targetAt(event,point){
    const terminal=event.target?.closest('[data-pin]');
    if(terminal){const key=terminal.dataset.pin,p=endpoint(model,key);if(p)return{kind:'pin',key,point:{x:p.x,y:p.y}};}
    const matrix=svg.getScreenCTM(),scale=Math.hypot(matrix?.a||1,matrix?.b||0);
    return findWireTarget(model,point,18/scale,event.target?.closest('[data-wire]')?.dataset.wire);
  }
  function releaseGesture(){const gesture=ui.wireGesture;ui.wireGesture=null;if(gesture&&svg.hasPointerCapture?.(gesture.pointerId))svg.releasePointerCapture(gesture.pointerId);}
  function cancelWire(exit=true,redraw=true){
    releaseGesture();ui.pending=null;ui.route=[];ui.routeHistory=[];
    if(exit)ui.tool='select';if(redraw)render();
  }
  function undoCorner(){
    if(ui.routeHistory.length){ui.route=ui.routeHistory.pop();tell('Last corner removed. Continue the wire or press Esc.');render();}
    else{cancelWire(true);tell('Wire cancelled.');}
  }
  function flipBend(){ui.bend=ui.bend==='hv'?'vh':'hv';tell('Bend flipped. Click to place a corner or finish at a green target.');paintPreview();}
  function wireDown(event,target,at){
    const started=!ui.pending;
    if(started&&!target){tell('Start on a terminal or an existing wire.');return;}
    if(started){ui.wireStay=ui.tool==='wire';ui.pending=target;ui.route=[];ui.routeHistory=[];ui.tool='wire';}
    ui.wireGesture={pointerId:event.pointerId,started,x:event.clientX,y:event.clientY};
    svg.setPointerCapture(event.pointerId);cursor=at;ui.cursor=at;event.preventDefault();
    tell('Release on a green target, or click empty space to place a corner. Tab flips the bend; Esc cancels.');render();
  }
  function finishWire(event){
    const gesture=ui.wireGesture;if(!gesture||gesture.pointerId!==event.pointerId)return;
    const moved=Math.hypot(event.clientX-gesture.x,event.clientY-gesture.y)>4;
    releaseGesture();if(gesture.started&&!moved)return;
    const at=position(event,false),target=targetAt(event,at);cursor=at;ui.cursor=at;
    if(target){
      try{
        const points=draftPoints(target.point),next=connectWireTargets(model,ui.pending,target,points.slice(1,-1),ui.bend);
        history();model=next;ui.pending=null;ui.route=[];ui.routeHistory=[];ui.selected=null;ui.tool=ui.wireStay?'wire':'select';
        tell('Connected. Drag or click again to add another wire.');commit();
      }catch(error){tell(error.message);render();}
    }else if(at.x>=0&&at.x<=1140&&at.y>=0&&at.y<=720){
      const route=draftPoints({x:snap(at.x),y:snap(at.y)}).slice(1);
      if(route.length>200){tell('Route limit reached. Finish this wire or remove a corner.');return;}
      ui.routeHistory.push(clone(ui.route));ui.route=route;
      tell('Corner placed. Continue to a terminal or wire. Backspace removes this corner.');render();
    }else tell('Return to the canvas to finish the wire, or press Esc to cancel.');
  }
  function position(event, snapped=true) {
    const matrix=svg.getScreenCTM();
    const p=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());
    return{x:snapped?snap(p.x):p.x,y:snapped?snap(p.y):p.y};
  }
  function paintPreview() {
    const preview=q('#wire-preview');
    if(!preview)return;
    const matrix=svg.getScreenCTM(),scale=Math.hypot(matrix?.a||1,matrix?.b||0);
    const target=cursor?findWireTarget(model,cursor,18/scale):null;
    const end=target?.point||(cursor?{x:snap(cursor.x),y:snap(cursor.y)}:null);
    preview.setAttribute('d',ui.pending&&end?path(draftPoints(end)):'');
    const halo=q('#wire-snap'),label=q('#wire-target-label');
    if(halo){halo.setAttribute('visibility',target&&(ui.pending||ui.tool==='wire')?'visible':'hidden');if(target){halo.setAttribute('cx',target.point.x);halo.setAttribute('cy',target.point.y);}}
    if(label){label.textContent=target&&(ui.pending||ui.tool==='wire')?(target.kind==='pin'?target.key:'Junction on wire'):'';if(target){label.setAttribute('x',Math.min(980,target.point.x+16));label.setAttribute('y',Math.max(18,target.point.y-16));}}
  }
  function paintDrag() {
    const drag=ui.drag;if(!drag)return;
    const item=getItem(),dx=item.x-drag.visualX,dy=item.y-drag.visualY;
    // Keep the SVG nodes and property inputs intact while the pointer moves.
    q(`[data-item="${item.id}"]`)?.setAttribute('transform',`translate(${dx},${dy})`);
    for(const pin of pins(item)){
      q(`[data-pin="${pin.key}"]`)?.setAttribute('transform',`translate(${dx},${dy})`);
      q(`[data-node-pin="${pin.key}"]`)?.setAttribute('transform',`translate(${dx},${dy})`);
    }
    for(const wire of model.wires)if(wire.a.startsWith(item.id+':')||wire.b.startsWith(item.id+':')){
      const d=path(wirePoints(model,wire));
      q(`[data-wire="${wire.id}"]`)?.querySelectorAll('path').forEach(p=>p.setAttribute('d',d));
    }
  }
  function queueFrame() {
    if(frame!==null)return;
    frame=requestAnimationFrame(()=>{frame=null;if(ui.drag)paintDrag();else paintPreview();});
  }
  function updateDrag(event) {
    const drag=ui.drag;if(!drag||event.pointerId!==drag.pointerId)return;
    const p=position(event,false),item=getItem();
    item.x=Math.max(60,Math.min(1080,drag.x+p.x-drag.start.x));
    item.y=Math.max(60,Math.min(660,drag.y+p.y-drag.start.y));
  }
  function rotate() {
    const item=getItem();if(!item)return;history();item.rotation=((item.rotation||0)+90)%360;commit();
  }
  function remove() {
    if(!ui.selected)return;history();
    if(getItem()){const id=ui.selected;model.items=model.items.filter(i=>i.id!==id);model.wires=model.wires.filter(w=>!w.a.startsWith(id+':')&&!w.b.startsWith(id+':'));}
    else model.wires=model.wires.filter(w=>w.id!==ui.selected);
    ui.selected=null;ui.pending=null;commit();
  }
  function symbol(item) {
    let shape='';
    if(item.type==='R')shape='<path d="M-40 0h12l5-10 8 20 8-20 8 20 8-20 8 20 5-10h18"/>';
    if(['V','I'].includes(item.type))shape=`<path d="M-40 0h17m46 0h17"/><circle r="23" fill="#fafdf8"/>${item.type==='V'?'<path d="M-14 0h10m-5-5v10m14-5h10"/>':'<path d="M-12 0h24m-7-5 7 5-7 5"/>'}`;
    if(item.type==='GROUND')shape='<path d="M0-20V0m-18 0h36m-29 7h22m-16 7h10"/>';
    if(item.type==='J')shape='<circle r="5" fill="#358252"/>';
    if(item.type==='OPAMP')shape='<path d="M-60-20h20m-20 40h20m80-20h20M-40-44V44L40 0Z" fill="#fafdf8"/><path d="M-32-20h12m-6-6v12m-6 34h12"/>';
    if(item.type==='PORT')shape='<path d="M-40 0h10m60 0h10"/><circle r="22" fill="white" stroke-dasharray="4 3"/><text x="0" y="5" text-anchor="middle" stroke="none" fill="#416d4b" font-size="16">V</text>';
    const open=measurement?.removedLoad===item.id;
    if(open)shape='<path d="M-40 0h18m44 0h18M-22 0L12-18" stroke="#b65d08"/><circle cx="-22" r="3"/><circle cx="22" r="3"/>';
    const vertical=[90,270].includes(item.rotation),x=item.x+(vertical?(item.type==='OPAMP'?62:38):0),y=item.y+(vertical?-5:item.type==='OPAMP'?-58:-46);
    return `<g class="component ${open?'removed-load ':''}${ui.selected===item.id?'selected':''}" data-item="${esc(item.id)}" role="button" tabindex="0" aria-label="Select ${esc(item.id)}${open?' (removed load, open circuit)':''}"><g transform="translate(${item.x},${item.y}) rotate(${item.rotation||0})"><rect class="hit" x="${item.type==='OPAMP'?-44:-34}" y="${item.type==='OPAMP'?-46:-31}" width="${item.type==='OPAMP'?88:68}" height="${item.type==='OPAMP'?92:62}" rx="9"/><g fill="none" stroke="#416d4b" stroke-width="2" stroke-linejoin="round">${shape}</g></g><text x="${x}" y="${y}" text-anchor="${vertical?'start':'middle'}" fill="#47794c" font-size="14">${esc(item.id)}${open?' · OPEN':''}</text>${item.value!==undefined&&!open?`<text x="${x}" y="${y+19}" text-anchor="${vertical?'start':'middle'}" font-size="11" fill="#8ca080">${esc(item.value)} ${item.type==='R'?'Ω':item.type==='V'?'V':'A'}</text>`:''}</g>`;
  }
  function lessonOverlay() {
    if(!lesson)return '';
    let markup=`<g id="lesson-overlay" pointer-events="none" ${ui.drag?'visibility="hidden"':''}><defs><marker id="flow-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="context-stroke"/></marker></defs>`;
    for(const wire of model.wires)if(nodeMap[wire.a]===lesson.node&&nodeMap[wire.b]===lesson.node){
      markup+=`<path class="node-highlight" d="${path(wirePoints(model,wire))}"/>`;
    }
    for(const item of model.items)for(const pin of pins(item))if(nodeMap[pin.key]===lesson.node){
      markup+=`<circle class="node-ring" cx="${pin.x}" cy="${pin.y}" r="11"/>`;
    }
    if(lesson.step>0)for(const branch of lesson.branches){
      const item=model.items.find(p=>p.id===branch.name);if(!item||item.id===measurement?.removedLoad)continue;
      const arrow=flowArrow(item,branch.direction),color=branch.touching?(branch.outward<0?'#b65d08':branch.outward>0?'#087f62':'#526779'):'#728a9c';
      const label=`${branch.number?branch.number+'. ':''}${branch.name} · ${branch.label}`,width=label.length*6.4+12;
      markup+=`<g class="flow" data-flow="${esc(branch.name)}" data-direction="${branch.direction}" aria-label="${esc(branch.why)}">${branch.direction?`<path class="flow-arrow" d="${path(arrow.points)}" stroke="${color}" marker-end="url(#flow-head)"/>`:''}<rect x="${arrow.label.x-width/2}" y="${arrow.label.y-11}" width="${width}" height="21" rx="4" fill="white" fill-opacity=".96" stroke="${color}" stroke-opacity=".3"/><text x="${arrow.label.x}" y="${arrow.label.y+3}" text-anchor="middle" fill="${color}" font-size="11">${esc(label)}</text></g>`;
    }
    return markup+'</g>';
  }
  function lessonNotes() {
    q('#lesson-notes').hidden=!lesson;
    if(!lesson)return;
    const headings=['Meet the node','Follow the current','Build the equation','Check the balance'];
    q('#lesson-heading').textContent=`${headings[lesson.step]} · ${lesson.node}`;
    q('#lesson-cards').innerHTML=lesson.notes[lesson.step].map(note=>`<li>${esc(note)}</li>`).join('');
  }
  function render() {
    ui.annotations={lesson,measurement,amplifiers};
    q('#measurement-info').hidden=!measurement;
    if(measurement)q('#measurement-info').textContent=`Open output: V(${measurement.node1}) − V(${measurement.node2}) = ${Number(measurement.voltage).toPrecision(6)} V · Probe current: 0 A · Removed load: ${measurement.removedLoad||'none'} (feedback stays connected)`;
    let html='<defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><circle r=".8" fill="#d6e5ce"/></pattern></defs><rect width="1140" height="720" fill="url(#grid)"/>';
    for(const w of model.wires){const points=wirePoints(model,w);if(!points.length)continue;const d=path(points);html+=`<g class="wire ${ui.selected===w.id?'selected':''}" data-wire="${esc(w.id)}"><path class="wire-hit" d="${d}"/><path class="wire-line" d="${d}"/></g>`;}
    if(!model.items.length)html+='<text x="570" y="330" text-anchor="middle" fill="#b0c5a5" font-size="24">Drag a component from the inventory</text>';
    model.items.forEach(item=>{
      html+=symbol(item);
      if(item.type==='OPAMP'&&item.mode==='open_loop')html+=`<text class="opamp-mode-label" x="${item.x}" y="${item.y-78}" text-anchor="middle" font-size="11" fill="#8651a2" pointer-events="none">OPEN LOOP</text>`;
    });
    for(const state of amplifiers){const item=model.items.find(i=>i.id===state.name&&i.type==='OPAMP'&&i.mode==='open_loop');if(item)html+=`<text class="opamp-state" data-opamp-state="${esc(state.name)}" x="${item.x+110}" y="${item.y-34}" text-anchor="middle" font-size="13" fill="${state.state==='HIGH'?'#087f62':'#b65d08'}" pointer-events="none">${esc(state.state)} · ${esc(Number(state.voltage).toPrecision(4))} V</text>`;}
    html+='<path id="wire-preview" fill="none" stroke="#168059" stroke-width="3" stroke-dasharray="7 5" pointer-events="none"/><circle id="wire-snap" r="14" fill="#3db67b" fill-opacity=".2" stroke="#13844d" stroke-width="3" pointer-events="none" visibility="hidden"/><text id="wire-target-label" fill="#086b43" font-size="12" font-weight="600" pointer-events="none"></text>';
    const labelsShown=new Set();
    for(const item of model.items)for(const pin of pins(item)){
      const count=model.wires.filter(w=>w.a===pin.key||w.b===pin.key).length;
      const pending=ui.pending?.kind==='pin'&&ui.pending.key===pin.key;
      const pinNumber=Number(pin.key.split(':')[1]),pinLabel=item.type==='OPAMP'?['+','−','OUT'][pinNumber-1]:item.type==='PORT'?['+','−'][pinNumber-1]:pinNumber;
      html+=`<g class="terminal" data-pin="${esc(pin.key)}"><circle class="pin-hit" cx="${pin.x}" cy="${pin.y}" r="20" fill="transparent" stroke="none" pointer-events="all"/><circle class="pin" cx="${pin.x}" cy="${pin.y}" r="${pending?9:6}" style="fill:${pending?'#94d2ab':count>1?'#4b9367':'white'}" pointer-events="none"/><title>${esc(pin.key)} · ${pinLabel}${nodeMap[pin.key]?' · node '+esc(nodeMap[pin.key]):''}</title><text x="${pin.x+9}" y="${pin.y+18}" fill="#657a60" font-size="10" pointer-events="none">${pinLabel}</text></g>`;
      const node=nodeMap[pin.key];if(node&&node!=='0'&&!labelsShown.has(node)){
        labelsShown.add(node);html+=`<text data-node-pin="${esc(pin.key)}" x="${pin.x}" y="${pin.y-22}" text-anchor="middle" fill="#258353" font-size="12" font-weight="600" pointer-events="none">${esc(node)}</text>`;
      }
    }
    if(measurement?.portId){const probe=model.items.find(i=>i.id===measurement.portId);if(probe)html+=`<text class="probe-reading" x="${probe.x}" y="${probe.y+64}" text-anchor="middle" font-size="14" fill="#7e4fa9" pointer-events="none">${Number(measurement.voltage).toPrecision(6)} V · I = 0</text>`;}
    svg.innerHTML=html+lessonOverlay();svg.dataset.tool=ui.tool;
    if(ui.drag){const item=getItem();ui.drag.visualX=item.x;ui.drag.visualY=item.y;}
    paintPreview();
    parentElement.querySelectorAll('[data-tool]').forEach(b=>b.classList.toggle('active',b.dataset.tool===ui.tool));
    q('#undo').disabled=!ui.history.length&&!ui.pending;q('#rotate').disabled=!getItem();q('#delete').disabled=!ui.selected;
    q('#cancel-wire').disabled=!ui.pending;q('#bend-wire').disabled=!ui.pending;
    showProperties();
    lessonNotes();
  }
  function showProperties() {
    const item=getItem(),fields=q('#property-fields');
    fields.hidden=!item;
    if(!item){q('#selected-name').textContent=ui.selected?'Selected wire — Delete removes it.':'Select a component to edit its value.';q('#part-help').textContent='';return;}
    q('#selected-name').textContent=`${item.id} · ${item.type} · ${item.rotation||0}°`;
    const draft=ui.draft?.id===item.id?ui.draft:null;
    q('#part-value').value=draft?draft.value:item.value??'';q('#part-value').disabled=item.value===undefined;
    q('#label-1').value=draft?draft.label1:item.label1||'';q('#label-2').value=draft?draft.label2:item.label2||'';
    q('#label-1').disabled=item.type==='GROUND';q('#label-2-field').hidden=pins(item).length===1;
    q('#label-3-field').hidden=q('#rail-min-field').hidden=q('#rail-max-field').hidden=q('#opamp-mode-field').hidden=item.type!=='OPAMP';
    q('#label-3').value=draft?draft.label3:item.label3||'';
    q('#rail-min').value=draft?draft.v_min:item.v_min??-15;q('#rail-max').value=draft?draft.v_max:item.v_max??15;
    q('#opamp-mode').value=draft?draft.mode??'feedback':item.mode??'feedback';
    q('#part-help').textContent=item.type==='OPAMP'?(q('#opamp-mode').value==='open_loop'?'OPEN LOOP: no feedback from OUT to either input. + > − selects output maximum; + < − selects minimum. Equal inputs are undefined. Both input currents are zero; supplies are implicit.':'NEGATIVE FEEDBACK: pin 1 = + · pin 2 = − · pin 3 = OUT. Zero input currents; keep inputs separate. Wire OUT back to −. Limits describe the supported linear range; supplies are implicit.'):item.type==='PORT'?'Pin 1 = + · Pin 2 = −. Infinite resistance: terminals are never connected internally. Choose Open-circuit voltage above to read this probe.':'';
  }
  listen(q('#inventory'),'click',event=>{const b=event.target.closest('[data-tool]');if(b)setTool(b.dataset.tool);});
  listen(q('#inventory'),'dragstart',event=>{const b=event.target.closest('[data-tool]');if(b){event.dataTransfer.setData('application/x-circuitscope',b.dataset.tool);event.dataTransfer.effectAllowed='copy';}});
  listen(svg,'dragover',event=>event.preventDefault());
  listen(svg,'drop',event=>{event.preventDefault();const type=event.dataTransfer.getData('application/x-circuitscope');if(type==='wire')setTool('wire');else if(['R','V','I','OPAMP','PORT','GROUND','J'].includes(type))place(type,position(event));});
  listen(svg,'pointerdown',event=>{
    if(event.button!==0||ui.drag||ui.wireGesture)return;
    svg.focus?.({preventScroll:true});
    if(ui.tool==='explain'){event.preventDefault();explainNode(event);return;}
    const terminal=event.target.closest('[data-pin]');
    if(terminal||ui.pending||ui.tool==='wire'){const at=position(event,false);wireDown(event,targetAt(event,at),at);return;}
    const component=event.target.closest('[data-item]'),wire=event.target.closest('[data-wire]'),at=position(event);
    if(!['select','wire'].includes(ui.tool)){place(ui.tool,at);return;}
    if(component){event.preventDefault();ui.selected=component.dataset.item;const item=getItem();ui.drag={id:item.id,pointerId:event.pointerId,start:position(event,false),x:item.x,y:item.y,before:clone(model)};svg.setPointerCapture(event.pointerId);render();}
    else{ui.selected=wire?wire.dataset.wire:null;render();}
  });
  listen(svg,'pointermove',event=>{if(ui.wireGesture&&event.pointerId!==ui.wireGesture.pointerId)return;if(ui.drag)updateDrag(event);else{cursor=position(event,false);ui.cursor=cursor;}if(ui.drag||ui.pending||ui.tool==='wire')queueFrame();});
  const finish=event=>{
    if(!ui.drag||event.pointerId!==ui.drag.pointerId)return;
    updateDrag(event);const last=ui.drag,item=getItem();
    item.x=snap(item.x);item.y=snap(item.y);ui.drag=null;
    if(svg.hasPointerCapture?.(last.pointerId))svg.releasePointerCapture(last.pointerId);
    if(item.x!==last.x||item.y!==last.y){ui.history.push(last.before);commit();}else render();
  };
  const cancelDrag=()=>{if(!ui.drag)return;const pointerId=ui.drag.pointerId;model=ui.drag.before;ui.model=model;ui.drag=null;if(svg.hasPointerCapture?.(pointerId))svg.releasePointerCapture(pointerId);render();};
  listen(svg,'pointerup',event=>{if(ui.wireGesture)finishWire(event);else finish(event);});
  const cancelPointer=()=>{if(ui.wireGesture){cancelWire(true);tell('Wire cancelled.');}else cancelDrag();};
  listen(svg,'pointercancel',cancelPointer);listen(svg,'lostpointercapture',cancelPointer);
  listen(svg,'contextmenu',event=>{if(ui.pending){event.preventDefault();cancelWire(true);tell('Wire cancelled.');}});
  function undo(){if(ui.pending){undoCorner();return;}if(!ui.history.length)return;model=ui.history.pop();ui.selected=null;commit();}
  listen(svg,'keydown',event=>{
    if(event.key==='Escape'){cancelDrag();cancelWire(true);tell('Cancelled. Select / move is active.');return;}
    if(ui.drag)return;
    if(ui.pending&&event.key==='Tab'){event.preventDefault();flipBend();return;}
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'){event.preventDefault();undo();return;}
    if(ui.pending&&['Backspace','Delete'].includes(event.key)){event.preventDefault();undoCorner();return;}
    if(event.key.toLowerCase()==='w'){event.preventDefault();setTool('wire');return;}
    if(event.key.toLowerCase()==='e'){event.preventDefault();setTool('explain');return;}
    if(event.key.toLowerCase()==='r')rotate();
    if(['Delete','Backspace'].includes(event.key)){event.preventDefault();remove();}
    if(['Enter',' '].includes(event.key)){const item=event.target.closest('[data-item]');if(item){event.preventDefault();ui.selected=item.dataset.item;render();}}
  });
  listen(q('#undo'),'click',undo);
  listen(q('#cancel-wire'),'click',()=>{cancelWire(true);tell('Wire cancelled.');});
  listen(q('#bend-wire'),'click',flipBend);
  listen(q('#rotate'),'click',rotate);listen(q('#delete'),'click',remove);
  listen(q('#clear'),'click',()=>{cancelWire(true,false);history();model={schema:'circuitscope.canvas.v1',items:[],wires:[]};ui.selected=null;ui.pending=null;ui.tool='select';ui.draft=null;commit();});
  function rememberProperties(){ui.draft={id:ui.selected,value:q('#part-value').value,label1:q('#label-1').value,label2:q('#label-2').value,label3:q('#label-3').value,v_min:q('#rail-min').value,v_max:q('#rail-max').value,mode:q('#opamp-mode').value};}
  listen(q('#properties'),'input',rememberProperties);
  listen(q('#opamp-mode'),'change',()=>{rememberProperties();showProperties();});
  listen(q('#properties'),'submit',event=>{event.preventDefault();const item=getItem();if(!item)return;
    const value=Number(q('#part-value').value),l1=q('#label-1').value.trim(),l2=q('#label-2').value.trim(),l3=q('#label-3').value.trim(),low=Number(q('#rail-min').value),high=Number(q('#rail-max').value);
    if(item.value!==undefined&&(!q('#part-value').value.trim()||!Number.isFinite(value)||(item.type==='R'&&value<=0))){tell('Enter a finite value; resistances must be positive.');return;}
    if([l1,l2,...(item.type==='OPAMP'?[l3]:[])].some(label=>label&&!/^[A-Za-z][A-Za-z0-9_]{0,11}$/.test(label))){tell('Node labels begin with a letter; ground uses a ground symbol.');return;}
    if(item.type==='OPAMP'&&(!q('#rail-min').value.trim()||!q('#rail-max').value.trim()||!Number.isFinite(low)||!Number.isFinite(high)||low>=high)){tell('Enter finite output limits with minimum below maximum.');return;}
    if(item.type==='OPAMP'&&!['feedback','open_loop'].includes(q('#opamp-mode').value)){tell('Choose a valid op-amp operation.');return;}
    history();if(item.value!==undefined)item.value=value;if(item.type!=='GROUND')item.label1=l1;item.label2=l2;
    if(item.type==='OPAMP'){item.label3=l3;item.v_min=low;item.v_max=high;item.mode=q('#opamp-mode').value;}
    ui.draft=null;commit();
  });
  render();
  return cleanup;
}
