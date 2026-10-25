import {test} from 'node:test';
import assert from 'node:assert/strict';
import {routePoints,wirePoints,findWireTarget,connectWireTargets,chooseBend} from '../canvas/editor.js';

const fixture=()=>({schema:'circuitscope.canvas.v1',items:[
  {id:'R1',type:'R',x:100,y:100,value:1000},
  {id:'R2',type:'R',x:500,y:100,value:1000},
  {id:'GND1',type:'GROUND',x:700,y:400},
],wires:[{id:'w1',a:'R1:2',b:'R2:1',bend:'hv'}]});
const branchTarget={kind:'wire',wireId:'w1',point:{x:300,y:100}};
const groundTarget={kind:'pin',key:'GND1:1',point:{x:700,y:380}};

test('manual routes stay orthogonal, retain corners and follow moved endpoints',()=>{
  const m=fixture(),w=m.wires[0];w.via=[{x:200,y:100},{x:200,y:200},{x:400,y:200}];
  let points=wirePoints(m,w);
  assert.ok(points.some(p=>p.x===200&&p.y===200));
  assert.ok(points.every((p,i)=>!i||p.x===points[i-1].x||p.y===points[i-1].y));
  m.items[1].y=300;points=wirePoints(m,w);
  assert.deepEqual(points.at(-1),{x:460,y:300});
  assert.ok(points.every((p,i)=>!i||p.x===points[i-1].x||p.y===points[i-1].y));
});
test('straight routes remove duplicate points without removing a reversal',()=>{
  assert.deepEqual(routePoints([{x:0,y:0},{x:0,y:0},{x:100,y:0}]),[{x:0,y:0},{x:100,y:0}]);
  assert.equal(routePoints([{x:0,y:0},{x:100,y:0},{x:50,y:0}]).length,3);
  assert.doesNotThrow(()=>chooseBend(fixture(),'R1:2','R2:1'));
});
test('nearby terminals snap and a nearby wire snaps to a point on its line',()=>{
  const m=fixture();
  assert.equal(findWireTarget(m,{x:151,y:108}).key,'R1:2');
  const target=findWireTarget(m,{x:307,y:106});
  assert.equal(target.kind,'wire');assert.deepEqual(target.point,{x:300,y:100});
  assert.equal(findWireTarget(m,{x:307,y:150}),null);
});
test('branching splits a wire and attaches the new branch atomically',()=>{
  const m=fixture(),before=structuredClone(m),next=connectWireTargets(m,groundTarget,branchTarget);
  assert.deepEqual(m,before,'a draft never mutates the published model');
  assert.equal(next.items.length,m.items.length+1);assert.equal(next.wires.length,3);
  const junction=next.items.find(p=>p.type==='J');
  assert.deepEqual([junction.x,junction.y],[300,100]);
  const key=junction.id+':1';
  assert.equal(next.wires.filter(w=>w.a===key||w.b===key).length,3);
  assert.deepEqual(wirePoints(next,next.wires[0]),[{x:140,y:100},{x:300,y:100}]);
});
test('branching at a bend preserves both original path halves',()=>{
  const m=fixture();m.items[1].y=300;
  const next=connectWireTargets(m,groundTarget,{kind:'wire',wireId:'w1',point:{x:460,y:100}});
  assert.equal(next.wires.length,3);
  const split=next.wires.find(w=>w.a.startsWith('J')&&w.b==='R2:1');
  assert.deepEqual(wirePoints(next,split),[{x:460,y:100},{x:460,y:300}]);
});
test('branching at a crossing connects only the chosen wire',()=>{
  const m=fixture();m.items.push({id:'Jtop',type:'J',x:300,y:20},{id:'Jbottom',type:'J',x:300,y:180});
  m.wires.push({id:'w2',a:'Jtop:1',b:'Jbottom:1'});
  const next=connectWireTargets(m,groundTarget,branchTarget);
  assert.deepEqual(next.wires.find(w=>w.id==='w2'),m.wires[1]);
  assert.equal(next.wires.filter(w=>w.a==='Jtop:1'||w.b==='Jtop:1').length,1);
});
test('duplicate or invalid connections fail without partial changes',()=>{
  const m=fixture(),before=structuredClone(m);
  assert.throws(()=>connectWireTargets(m,{kind:'pin',key:'R1:2'},{kind:'pin',key:'R2:1'}),/already/);
  assert.throws(()=>connectWireTargets(m,groundTarget,{kind:'wire',wireId:'w1',point:{x:300,y:200}}),/moved/);
  assert.throws(()=>connectWireTargets(m,branchTarget,branchTarget),/same wire/);
  assert.deepEqual(m,before);
});
test('failed size-limit checks do not leave a junction or half wire',()=>{
  const m=fixture();for(let i=0;m.items.length<60;i++)m.items.push({id:'J'+i,type:'J',x:800,y:600});
  const before=structuredClone(m);
  assert.throws(()=>connectWireTargets(m,groundTarget,branchTarget),/limit/);
  assert.deepEqual(m,before);
});
