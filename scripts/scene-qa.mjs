/** CPU-side scene integration diagnostic. No WebGL/browser installation required. */
import {readFile} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {pathToFileURL} from 'node:url';
import {DEG,polar,moonDirection,reflect,scale,add,sub,distance,dot} from '../prototype/rotunda/core/math.js';
process.on('uncaughtException',e=>{console.error('QA CRASH:',e.name,e.message);process.exit(1);});

const root=resolve(import.meta.dirname,'..');
const entry=resolve(root,'prototype/rotunda/main.js');
const nodes=new Map();
function node(id){
 if(!nodes.has(id))nodes.set(id,{
  id,style:{},classList:{add(){},remove(){},toggle(){},contains(){return false;}},
  addEventListener(){},getContext(){return context;},setPointerCapture(){},
  textContent:'',visible:true,
 });
 return nodes.get(id);
}
const context={fillRect(){},clearRect(){},beginPath(){},arc(){},stroke(){},fill(){},moveTo(){},lineTo(){},fillText(){},measureText(){return{width:32};}};
globalThis.document={querySelector:node,createElement:()=>({width:0,height:0,getContext:()=>context})};
globalThis.window=globalThis;
globalThis.addEventListener=()=>{};
globalThis.location={search:'?debug=1'};
globalThis.devicePixelRatio=1;
globalThis.innerWidth=1280;globalThis.innerHeight=720;
const storage=new Map();
globalThis.localStorage={getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)};
globalThis.requestAnimationFrame=cb=>{globalThis.__pending=cb;};
let source=await readFile(entry,'utf8');
source=source.replaceAll("new THREE.WebGLRenderer({canvas:$('#scene'),antialias:true,powerPreference:'high-performance'})",'({shadowMap:{},setPixelRatio(){},setSize(){},render(){}})');
source=source.replace(/from '(\.\/[^']+)'/g,(_,relative)=>`from '${pathToFileURL(resolve(dirname(entry),relative)).href}'`);
source+='\nglobalThis.__sceneCPU={scene,world,art,optics,dayPaths,moonForms,player,mirrorDay,mirrorNight,mirrorPool,muralTarget,muralShadow,n1Bridge,n2BridgeFixed,n2BridgeMoving,n3Bridge,poolASpan,poolBSpan,roofFoot,roofTop,F1,F2,T1,T2,T3,M,oldSpot,moonM,poolMirror,poolTarget,normalPool,startGame,activePhase,updateMoon,updateSolar,updateCelestial,collision,advance,rotateY,orientMirror,get phase(){return phase;},get stage(){return stage;},get night(){return night;},get n1Score(){return n1Score;},get source(){return source;},get poolReady(){return poolReady;},get pairReady(){return pairReady;},get oldReady(){return oldReady;},get exposures(){return {n1Exposure,n2Direct,n2Reflected,poolAExposure,poolBExposure};},setYaw(which,val){if(which===\'sun\')sunYaw=val;if(which===\'moon\')moonYaw=val;if(which===\'pool\')poolYaw=val;if(which===\'swan\')swanYaw=val;},setRail(t){railT=t;},tick(time){globalThis.__pending(time);}};';
try{await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);}
catch(e){console.error('Scene bootstrap failed:',e.message);process.exitCode=1;process.exit();}
const q=globalThis.__sceneCPU;
q.startGame();
let time=performance.now();
const tick=(count=1)=>{for(let i=0;i<count;i++)q.tick(time+=50);};
const inspect=(name,fixture,count=9)=>{
 if(fixture)window.__dysisQA.fixture(...fixture);
 tick(count);
 const status={stage:q.stage,phase:q.phase,night:q.night,at:q.player.position.map(x=>+x.toFixed(2)),day:q.dayPaths.map(p=>({live:p.live,cells:q.world.surfaces.filter(s=>s.mesh.name.startsWith(p.surface.mesh.name+' · clipped')&&s.enabled).length})),exposures:q.exposures,ready:{swan:q.n1Bridge.enabled,pair:q.pairReady,old:q.oldReady,pool:q.poolReady},score:q.n1Score,collision:q.collision(q.player.position,.27,1.7)};
 console.log(name,JSON.stringify(status));
};
inspect('D1 entry');
inspect('D2 foot',[1,q.F2]);
inspect('D3 mirror',[2,q.M]);
inspect('roof start',[3,q.roofFoot]);
inspect('N1 mural',[5,[16.5,18,-6.7]]);
let best={score:0,yaw:0};
for(let yaw=-1.6;yaw<=1.6;yaw+=.025){q.setYaw('swan',yaw);q.updateMoon(.05);if(q.n1Score>best.score)best={score:q.n1Score,yaw};}
console.log('N1 swan best yaw',best);
inspect('N2 mirror',[6,q.moonM]);
q.setYaw('moon',0);q.setRail(1);inspect('N2 mirrored/paired',[6,[q.moonM[0],12,q.moonM[2]]]);
inspect('N3 crown',[7,[q.oldSpot[0],6,q.oldSpot[2]]]);
inspect('pool mirror',[8,[q.poolMirror[0],0,q.poolMirror[2]]]);
let reflective=[];for(let yaw=-1.2;yaw<=1.2;yaw+=.025){q.setYaw('pool',yaw);q.updateMoon(.05);if(q.exposures.poolBExposure)reflective.push(yaw);}
console.log('pool reflection yaw interval',reflective.length?[Math.min(...reflective),Math.max(...reflective)]:[]);
const src=moonDirection(q.phase),incoming=scale(src,-1),targetOffset=sub(q.poolTarget,q.poolMirror),outgoing=reflect(incoming,q.normalPool);
const inboundHit=q.optics.obstruction(q.poolMirror,src,80,[q.mirrorPool.userData.mirrorDisk]);
const outboundHit=q.optics.obstruction(q.poolMirror,outgoing,Math.max(0,dot(targetOffset,outgoing)-.1),[q.mirrorPool.userData.mirrorDisk]);
console.log('pool ray diagnostic',JSON.stringify({phase:q.phase,source:src,normal:q.normalPool,origin:q.poolMirror,target:q.poolTarget,outgoing,t:dot(targetOffset,outgoing),closest:distance(add(q.poolMirror,scale(outgoing,dot(targetOffset,outgoing))),q.poolTarget),originLit:q.optics.directLit(q.poolMirror,src,[q.mirrorPool.userData.mirrorDisk]),originHit:inboundHit&&{name:inboundHit.object.name,parent:inboundHit.object.parent?.name,dist:inboundHit.distance,point:inboundHit.point.toArray()},reflectedHit:outboundHit&&{name:outboundHit.object.name,parent:outboundHit.object.parent?.name,dist:outboundHit.distance,point:outboundHit.point.toArray()}}));
function motorTo(label,target,limit=100){
 const start=q.stage;let closest=Infinity,stalled=0,steps=0;
 for(;steps<limit;steps++){
  const p=q.player.position,dx=target[0]-p[0],dz=target[2]-p[2],horizontal=Math.hypot(dx,dz);
  if(horizontal<.28||q.stage!==start)break;
  const old=horizontal;
  q.player.update(.10,{move:[dx/horizontal,dz/horizontal]},q.world.support,q.collision);tick();
  if(process.env.QA_TRACE==='N1'&&label==='N1 descent 303'&&steps<18)console.log('TRACE N1',steps,q.player.position.map(v=>+v.toFixed(3)),q.player.grounded,q.phase,q.world.support(q.player.position[0],q.player.position[2],q.player.position[1]+.5,.8));
  if(Math.hypot(target[0]-q.player.position[0],target[2]-q.player.position[2])>=old-.0005)stalled++;else stalled=0;
  closest=Math.min(closest,Math.hypot(target[0]-q.player.position[0],target[2]-q.player.position[2]));
  if(stalled>12)break;
 }
 if(process.env.QA_VERBOSE==='1'||!label.includes('descent ')||stalled>12||q.stage!==start)console.log('motor '+label,JSON.stringify({from:start,to:q.stage,steps,stalled,closest:+closest.toFixed(3),position:q.player.position.map(x=>+x.toFixed(2)),target:target.map(x=>+x.toFixed(2))}));
 return Math.hypot(q.player.position[0]-target[0],q.player.position[2]-target[2])<.5||q.stage!==start;
}
if(process.env.QA_NIGHT_ONLY!=='1')for(const [name,stageNumber,from,to] of [
 ['D1',0,q.F1,q.T1],['D2',1,q.F2,q.T2],['D3',2,q.M,q.T3],['roof',3,q.roofFoot,q.roofTop],
]){
 window.__dysisQA.fixture(stageNumber,from);q.setYaw('sun',0);tick(10);motorTo(name,to);
}
const point=(r,a,y)=>polar(r,a*DEG,y),oldAngle=Math.atan2(q.oldSpot[2],q.oldSpot[0])/DEG+360;
q.setYaw('swan',0);window.__dysisQA.fixture(5,point(13.8,330,18));tick(12);
console.log('N1 gate before walk',q.n1Bridge.enabled,q.phase,q.n1Score);
motorTo('N1 mural bridge',point(18,327,18));
console.log('N1 after bridge',JSON.stringify({position:q.player.position,gate:q.n1Bridge.enabled,phase:q.phase,score:q.n1Score,exposure:q.exposures.n1Exposure,collision:q.collision(q.player.position,.27,1.7),support:q.world.support(q.player.position[0],q.player.position[2],18.5,.6)}));
if(process.env.QA_SECTION==='N1_BRIDGE')process.exit(0);
let n1Continue=true;for(let a=323;a>=250&&q.stage===5;a-=4)if(!motorTo('N1 descent '+a,point(18,Math.max(250,a),12+(Math.max(250,a)-250)*6/77))){n1Continue=false;break;}
if(q.stage===5&&n1Continue)motorTo('N1 descent last',point(18,250,12));
console.log('N1 descent result',q.stage,q.player.position.map(v=>+v.toFixed(2)));
if(process.env.QA_SECTION==='N1')process.exit(0);
q.setYaw('moon',0);q.setRail(1);
window.__dysisQA.fixture(6,point(14.3,290,12));tick(12);
motorTo('N2 paired moonbridge',point(9.2,290,12));
let n2Continue=true;for(let a=285;a>=207&&q.stage===6;a-=5)if(!motorTo('N2 descent '+a,point(9.2,Math.max(207,a),6+(Math.max(207,a)-207)*6/83))){n2Continue=false;break;}
if(q.stage===6&&n2Continue)motorTo('N2 descent last',point(9.2,207,6));
console.log('N2 descent result',q.stage,q.player.position.map(v=>+v.toFixed(2)));
window.__dysisQA.fixture(7,point(12,oldAngle,6));tick(12);
motorTo('N3 old-light bridge',point(17.2,oldAngle,6));
let n3Continue=true;for(let a=oldAngle-4;a>=oldAngle-41&&q.stage===7;a-=4)if(!motorTo('N3 descent '+a,point(17.2,Math.max(oldAngle-41,a),6+(Math.max(oldAngle-41,a)-(oldAngle-41))*6/41))){n3Continue=false;break;}
if(q.stage===7&&n3Continue)motorTo('N3 descent last',point(17.2,oldAngle-41,0));
console.log('N3 descent result',q.stage,q.player.position.map(v=>+v.toFixed(2)));
q.setYaw('pool',0);window.__dysisQA.fixture(8,point(8.25,140,0));tick(12);
motorTo('water pavilion bridge',point(2.1,140,0));
console.log('CPU scene diagnostic complete');
