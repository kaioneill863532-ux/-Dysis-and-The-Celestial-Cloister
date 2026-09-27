import * as THREE from './vendor/three.module.js';
import {DEG,clamp,lerp,polar,add,sub,scale,normalize,distance,dot,reflect,mirrorNormal,sunDirection,moonDirection,uniformPhase,rayPlane,segmentDistanceXZ} from './core/math.js';
import {PlayerMotor} from './core/player.js';
import {phaseAtPosition,DAY_RAMPS,NIGHT_REFLECTION} from './core/layout.js';
import {MoonForm,NightProgress,shadowAlignment,pairAlignment,dualBridgeReady} from './core/puzzles.js';
import {createArchitecture} from './render/architecture.js';
import {createGoddess,createSwan,createMirrorStatue,createArmillary} from './render/sculptures.js';
import {makeWorld,stripHole,sectorHole,labelSprite} from './render/geometry.js';
import {createOptics} from './render/optics.js';

const $=s=>document.querySelector(s),V=a=>new THREE.Vector3(...a);
const angle=p=>{let a=Math.atan2(p[2],p[0])/DEG;return a<0?a+360:a;};
const radial=(r,a,y)=>polar(r,a*DEG,y);
const pathPoint=(a,b,t)=>a.map((v,i)=>lerp(v,b[i],t));
const radialLength=p=>Math.hypot(p[0],p[2]);
const SAVE='dysis-rotunda-v1';
const debug=new URLSearchParams(location.search).has('debug');
const notices=[];
let started=false,ended=false,stage=0,night=false,phase=0,source=sunDirection(0),elapsed=0,iris=0,apple=false;
let checkpoint={stage:0,position:radial(14,20,0),phase:0},lastToast=0;
let sunYaw=.32,moonYaw=.3,swanYaw=.7,poolYaw=-.32,railT=0;
let cameraYaw=1.13,cameraPitch=.24,cameraDistance=5.5,dragging=false,overview=false;
let nearest=null,lastE=false,lastH=false,lastX=false,lastTab=false,fallPeak=0;
let n1Score=0,pairReady=false,oldReady=false,poolReady=false;
let n1Exposure=false,n2Direct=false,n2Reflected=false,poolAExposure=false,poolBExposure=false;
const progress=new NightProgress(),keys=new Set();
const chapters=[
 ['Ⅰ · 初光','借一束日光上楼','绕行改变光位；沿亮面向上。'],
 ['Ⅱ · 双窗','穿过两道并行的光','相邻窗洞织出两条光路。远端金色小龛可以顺路探访。'],
 ['Ⅲ · 返照','让镜中的光抵达上层','在持镜像旁调整镜面，再沿石阶登上反射光。'],
 ['Ⅳ · 天心','从圆殿内部抵达天空','穿过中央孔，登上孔口周围的观天台。'],
 ['Ⅴ · 日落回廊','绕行，让穹顶缓缓展开','沿石脊走向外围，再走过半圈。带上金苹果。'],
 ['Ⅵ · 群鹅','把天鹅的影子送回群中','月光中的女神化为天鹅；转动雕像，补齐浮雕。'],
 ['Ⅶ · 相逢','让两片月石相接','先校准旧镜，再沿光中的轨道移动另一半。'],
 ['Ⅷ · 旧镜新光','走向被旧镜照亮的回廊','改变月位，让上一层的反光抵达脚下。'],
 ['Ⅸ · 水之心','让两段桥同时醒来','一段借月亮，一段借岸边的镜子。沿等时方向入亭。'],
 ['尾声','把金苹果放回浑天仪','有些光，不必带走。'],
];
const hints=[
 '先走到日光落地的地方。亮面有连续的金边，可以承重。再迎着光向上走。',
 '沿本层圆廊来到对面；双窗下方的光路落在内缘。若想访日之龛，可轻跃到邻近光带。',
 '靠近持镜像，Q / R 缓慢转动镜面；反射光的终点需要搭上上层的石台。镜旁小石阶通向光路起点。',
 '中央光坡属于固定时间连接带。沿光面穿入孔口，叶片不会在你登顶时提前展开。',
 '从观天台的唯一石脊走向外围。绕行至暮色中的浑天仪，E 拾取金苹果，再穿过拱门。',
 '站到浮雕朝向月亮的一面。女神变成天鹅后，用 Q / R 调整；金色空缺与深色投影需要重合。',
 '镜面反射必须沿轨道照亮活动月石；在镜边用 Q / R 校准，再靠近轨道用 Q / R 移动。离光会复原，位置会保留。',
 '不用再碰那面镜子。沿圆廊走向日月石壁前的高冠饰；抬头追寻那道细银光。',
 '亭檐挡住了内半桥的直射光。校准岸边镜子，把月光从檐下送进去；径向入亭可保持月位。',
 '走近中央浑天仪，按 E。',
];
function toast(text,duration=5){$('#toast').textContent=text;$('#toast').classList.add('show');lastToast=elapsed+duration;notices.push(text);}
function error(message){$('#error-text').textContent=message;$('#error').classList.remove('hidden');}
let renderer;
try{renderer=new THREE.WebGLRenderer({canvas:$('#scene'),antialias:true,powerPreference:'high-performance'});}catch(e){error('浏览器没有可用的 WebGL。请使用支持硬件加速的桌面浏览器打开。');throw e;}
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setSize(innerWidth,innerHeight);
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.15;renderer.outputColorSpace=THREE.SRGBColorSpace;
const scene=new THREE.Scene();scene.background=new THREE.Color(0xa9c5c7);scene.fog=new THREE.Fog(0xa9c5c7,60,190);
const camera=new THREE.PerspectiveCamera(58,innerWidth/innerHeight,.08,240);
const hemi=new THREE.HemisphereLight(0xc7e4f2,0x947653,2.2);scene.add(hemi);
const celestial=new THREE.DirectionalLight(0xffe0ac,3.7);celestial.castShadow=true;celestial.shadow.mapSize.set(2048,2048);
Object.assign(celestial.shadow.camera,{left:-27,right:27,top:34,bottom:-25,near:1,far:110});celestial.shadow.bias=-.0003;celestial.shadow.normalBias=.025;scene.add(celestial,celestial.target);
const sunOrb=new THREE.Mesh(new THREE.SphereGeometry(1.15,24,16),new THREE.MeshBasicMaterial({color:0xffe5b4}));scene.add(sunOrb);
const skyStars=new THREE.BufferGeometry(),starPoints=[];
for(let i=0;i<430;i++){const a=i*2.399963,b=Math.acos(1-((i*.618033)%1));starPoints.push(Math.cos(a)*Math.sin(b)*130,Math.cos(b)*130+15,Math.sin(a)*Math.sin(b)*130);}
skyStars.setAttribute('position',new THREE.Float32BufferAttribute(starPoints,3));const stars=new THREE.Points(skyStars,new THREE.PointsMaterial({color:0xcfe5ff,size:.14,transparent:true,opacity:0}));scene.add(stars);

const roofFoot=DAY_RAMPS[3].foot,roofTop=DAY_RAMPS[3].top,roofAngle=angle(roofTop);
const art=createArchitecture(scene,{roofAngle:roofAngle*DEG,radius:20});
art.floorDecorations.forEach(m=>m.visible=false);
art.materials.lightStone.side=THREE.DoubleSide;art.materials.stone.side=THREE.DoubleSide;
const world=makeWorld(scene,art.materials);world.occluders.push(...art.occluders);
world.box([11.2,3.2,1.6],[14.45,25.6,0],art.materials.relief);
world.opticalCylinders=art.obstacles.filter(o=>o.type==='cylinder').flatMap(o=>[o,{...o,radius:.672,top:o.bottom+.16},{...o,radius:.701,bottom:o.top-.24}]);
const optics=createOptics(scene,world);
const moonStone=new THREE.MeshStandardMaterial({color:0xb9d9eb,roughness:.58,metalness:.18,emissive:0x24475b,emissiveIntensity:.45,side:THREE.DoubleSide});
const bronze=art.materials.bronze,stone=art.materials.lightStone;
const T1=DAY_RAMPS[0].top,T2=DAY_RAMPS[1].top,M=DAY_RAMPS[2].mirror,T3=DAY_RAMPS[2].top;
const F1=DAY_RAMPS[0].foot,F2=DAY_RAMPS[1].foot,normalDay=DAY_RAMPS[2].mirrorNormal;
const dayF=(layer,a)=>phaseAtPosition(layer,radial(1,a,0));
const moonTheta=290,moonM=NIGHT_REFLECTION.mirror,normalMoon=NIGHT_REFLECTION.mirrorNormal;
const oldSpot=NIGHT_REFLECTION.target,oldAngle=angle(oldSpot);
const poolTheta=140,poolMirror=radial(8.7,poolTheta,1.8),poolTarget=radial(2.7,poolTheta,.6),poolSourcePhase=150;
const normalPool=mirrorNormal(scale(moonDirection(poolSourcePhase),-1),sub(poolTarget,poolMirror));
const moonForms={swan:new MoonForm(),fixed:new MoonForm(),moving:new MoonForm(),old:new MoonForm(),poolA:new MoonForm(),poolB:new MoonForm()};

// A single cut-out owns both the visible floor and the collision support.
const nearTopHole=(foot,top)=>{
 const start=pathPoint(foot,top,.70),d=[top[0]-start[0],0,top[2]-start[2]],l2=dot(d,d);
 return p=>{const t=((p[0]-start[0])*d[0]+(p[2]-start[2])*d[2])/l2;return t>=0&&t<.995&&segmentDistanceXZ(p,start,top).distance<1.7;};
};
const solarSlotAt=h=>add(M,scale(sunDirection(h),3.5/sunDirection(h)[1]));
const upperSolarSlot=stripHole(solarSlotAt(29.2),solarSlotAt(39.5),3.1);
const returnCross=rayPlane(moonM,normalize(sub(oldSpot,moonM)),[0,12,0],[0,1,0]).point;
const returnSlot=p=>Math.hypot(p[0]-returnCross[0],p[2]-returnCross[2])<.85;
world.annulus(8,19.1,0);
world.annulus(11.2,14.8,6,7,353,[nearTopHole(F1,T1),sectorHole(12.5,16,oldAngle-5,oldAngle+5)]);
world.annulus(11.2,14.8,12,7,353,[nearTopHole(F2,T2),returnSlot,sectorHole(10,13.9,moonTheta-16,moonTheta+16)]);
world.annulus(11.2,14.8,18,7,353,[nearTopHole(M,T3),upperSolarSlot,nearTopHole(roofFoot,roofTop)]);
const nightIntake=p=>p[0]>8.0&&p[0]<10.1&&p[2]>-18.3&&p[2]<-16.0;
for(const y of [6,12,18])for(let a=30;a<360;a+=30)world.annulus(14.5,18.8,y,a-5,a+5,y===18?[nightIntake,upperSolarSlot,sectorHole(16.9,19.2,250,327)]:y===6?[sectorHole(15.95,18.45,oldAngle-41,oldAngle+.5)]:[],art.materials.stone);
for(const [top,foot,from,to] of [[T1,F1,51,73],[T2,F2,153,195],[T3,M,258,281]])world.annulus(14.5,17,top[1],from,to,[nearTopHole(foot,top)]);
for(const [top,heading] of [[T1,sunDirection(dayF(0,55))],[T2,sunDirection(dayF(1,165))],[T3,sub(T3,M)]]){
 const forward=normalize([heading[0],0,heading[2]]);
 world.quad(top,add(top,scale(forward,2.7)),4.2);
 world.line([add(top,[0,.02,0]),add(add(top,scale(forward,2.5)),[0,.02,0])],0xc4a25a);
}
world.quad(radial(12,20,0),F1,2.9);world.disk(1.1,0,F1[0],F1[2]);world.disk(1.25,6,F2[0],F2[2]);
world.straightStairs(radial(13,230,12),M,2.6);world.disk(1.55,14.5,M[0],M[2]);
world.quad(radial(14.1,230,12),radial(17,230,12),2.6);
world.disk(1.35,18,roofFoot[0],roofFoot[2]);world.quad(radial(14,304,18),roofFoot,2.5);
world.annulus(4.5,6,24,0,360);world.quad(radial(5.7,roofAngle,24),radial(16.7,roofAngle,24),2.3);
world.annulus(15.8,18.6,24,8,352,[sectorHole(15.7,18.7,305,347)]);
world.stairs(17.2,305,346,24,18,2.1);world.annulus(14.5,18.8,18,338,349);
const stairN1=world.stairs(18,327,250,18,12,2.0);
world.quad(radial(18,250,12),radial(14.1,250,12),2.5);
const n1Bridge=world.quad(radial(13.8,330,18),radial(18,327,18),2.25,moonStone,{solid:false});n1Bridge.mesh.visible=false;
const n1Door=world.box([2.3,3.5,.24],radial(18,326.5,19.65),art.materials.relief);n1Door.rotation.y=-326.5*DEG;
// Leave the first stair bay open so the moon bridge can join the stair centre.
for(let i=1;i<15;i++)for(const r of [16.96,19.04])world.rail(radial(r,lerp(327,250,i/15),lerp(18,12,i/15)),radial(r,lerp(327,250,(i+1)/15),lerp(18,12,(i+1)/15)));
world.annulus(14.5,18.9,18,336,344);
const n2BridgeFixed=world.quad(radial(9.2,moonTheta,12),radial(11.3,moonTheta,12),2.3,moonStone,{solid:false});
const n2BridgeMoving=world.quad(radial(11.3,moonTheta,12),radial(14.3,moonTheta,12),2.3,moonStone,{solid:false});
n2BridgeFixed.mesh.visible=n2BridgeMoving.mesh.visible=false;
world.disk(1.15,12,...[radial(9.2,moonTheta,12)[0],radial(9.2,moonTheta,12)[2]]);
world.stairs(9.2,moonTheta,207,12,6,2.3);world.quad(radial(9.2,207,6),radial(12,207,6),2.4);
world.quad(radial(14.2,moonTheta,12),radial(19,moonTheta,12),2.8);
const n3Bridge=world.quad(radial(12,oldAngle,6),radial(17.2,oldAngle,6),2.4,moonStone,{solid:false});n3Bridge.mesh.visible=false;
world.stairs(17.2,oldAngle,oldAngle-41,6,0,2.3);world.disk(1.1,6,oldSpot[0],oldSpot[2]);
world.disk(2.35,0,0,0);
const poolASpan=world.quad(radial(8.25,poolTheta,0),radial(5,poolTheta,0),2.2,moonStone,{solid:false});
const poolBSpan=world.quad(radial(5,poolTheta,0),radial(2.1,poolTheta,0),2.2,moonStone,{solid:false});
poolASpan.mesh.visible=poolBSpan.mesh.visible=false;
world.quad(radial(10.1,poolTheta,0),radial(8.2,poolTheta,0),2.7);
const pavilionRoof=world.disk(3.2,4.2,0,0,art.materials.darkStone);world.surfaces.at(-1).enabled=false;
for(const a of [0,60,120,180,240,300]){const p=radial(2.5,a,2.1);world.add(new THREE.Mesh(new THREE.CylinderGeometry(.12,.17,4.2,16),stone)).position.set(...p);}
for(const y of [0,6,12,18])for(let a=15;a<350;a+=10){const r0=y===0?8.4:11.45;world.line([radial(r0,a,y+.012),radial(14.5,a,y+.012)],0x4c939a,.45);}
for(const y of [6,12,18])for(let a=10;a<350;a+=2){const p=radial(11.26,a,y+.05),q=radial(11.26,a+1.7,y+.05);if(world.support(p[0],p[2],y+.1,.2)!==null)world.line([p,q],0xad8a4d,.7);}
world.line([T1,radial(15.5,58,6),radial(15.5,68,6),radial(13,72,6)].map(p=>add(p,[0,.026,0])),0xc4a25a);
world.line([T2,radial(16.7,165,12),...Array.from({length:7},(_,i)=>radial(16.7,168+i*3.33,12)),radial(13,195,12)].map(p=>add(p,[0,.026,0])),0xc4a25a);
world.line([T3,radial(15.5,276,18),radial(13,282,18)].map(p=>add(p,[0,.026,0])),0xc4a25a);

// Every luminous walk is a real, finite, dynamically enabled support surface.
const dayPaths=[
 optics.path('D1 · first light'),optics.path('D2 · twin light'),
 optics.path('D2 · optional side light',0xffe5a4,2.2),
 optics.path('D3 · returned light',0xffdc8a,2.5,{origin:'a'}),
 optics.path('Oculus · steady light'),
];
const solarIncoming=optics.rayLine('Sun through facade',0xffcc75);
const moonIncoming=optics.rayLine('Moon through clerestory');
const moonReturning=optics.rayLine('Mirror toward crown');
const poolReturning=optics.rayLine('Moon beneath pavilion eave');
const T2side=[-17.16995,12,2.97103];
const sideHeading=normalize([sunDirection(15.05)[0],0,sunDirection(15.05)[2]]);
const sideShrine=add(T2side,scale(sideHeading,1.66));
world.disk(1.6,12,sideShrine[0],sideShrine[2]);
world.quad(T2side,add(T2side,scale(sideHeading,.7)),2.2);

function putModel(model,p,s=1){model.position.set(...p);model.scale.setScalar(s);scene.add(model);return model;}
function orientMirror(model,normal,p){
 const disk=model.userData.mirrorDisk,assembly=model.userData.mirrorAssembly;
 assembly.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),V(normal));
 model.updateMatrixWorld(true);
 model.position.add(V(p).sub(disk.getWorldPosition(new THREE.Vector3())));
 model.updateMatrixWorld(true);
}
const rotateY=(n,yaw)=>V(n).applyAxisAngle(new THREE.Vector3(0,1,0),yaw).toArray();
const mirrorDay=putModel(createMirrorStatue(),[M[0],12,M[2]]);
const mirrorNight=putModel(createMirrorStatue(),[moonM[0],12,moonM[2]]);
const mirrorPool=putModel(createMirrorStatue(),[poolMirror[0],0,poolMirror[2]],.72);
world.disk(1.45,12,moonM[0],moonM[2]);world.disk(1.2,0,poolMirror[0],poolMirror[2]);

// A projected, landmark-tested silhouette rather than a proximity switch.
const receiverSource=moonDirection(101);
const receiverNormal=normalize([receiverSource[0],0,receiverSource[2]]);
const receiverPoint=radial(15,337,19.9);
const sculpturePoint=add([receiverPoint[0],18.55,receiverPoint[2]],scale(receiverNormal,2.5));
const muralWall=world.box([6.2,4.3,.28],receiverPoint,art.materials.darkStone,{block:false});
muralWall.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),V(receiverNormal));
const goddess=putModel(createGoddess(),sculpturePoint,.62);
const swan=putModel(createSwan(moonStone),sculpturePoint,.62);
world.disk(.91,18.55,sculpturePoint[0],sculpturePoint[2]);
const targetSwan=putModel(createSwan(),sculpturePoint,.62);targetSwan.rotation.y=-.8;
const muralTarget=optics.projectModel(targetSwan,receiverPoint,receiverNormal,0xc4aa71);
const targetLandmarks=muralTarget.update(scale(receiverSource,-1));targetSwan.visible=false;
muralTarget.group.children.forEach(m=>m.material.opacity=.52);
const muralShadow=optics.projectModel(swan,receiverPoint,receiverNormal,0x162638);
const wallTangent=[receiverNormal[2],0,-receiverNormal[0]];
for(const side of [-1,1]){
 const copy=muralTarget.group.clone();
 copy.traverse(m=>{if(m.isMesh){m.material=m.material.clone();m.material.color.setHex(0xdbd4c3);m.material.opacity=.9;}});
 copy.position.set(...scale(wallTangent,side*1.95));scene.add(copy);
}
const moonGlyph=labelSprite('月光还未落在女神身上',{scale:2.2});moonGlyph.position.set(...add(sculpturePoint,[0,3.1,0]));scene.add(moonGlyph);

function archFragment(material=moonStone){
 const g=new THREE.Group();
 const stem=new THREE.Mesh(new THREE.CylinderGeometry(.13,.2,2.4,12),material);stem.position.y=1.2;g.add(stem);
 const arc=new THREE.Mesh(new THREE.TorusGeometry(.68,.13,10,28,Math.PI),material);arc.position.y=2.36;g.add(arc);
 const socket=new THREE.Mesh(new THREE.SphereGeometry(.22,16,12),bronze);socket.position.set(.68,2.35,0);g.add(socket);
 return g;
}
const fixedPoint=radial(9.7,moonTheta,12),movingPoint=t=>radial(15.7-2.9*t,moonTheta,12);
const fixedFragment=putModel(archFragment(),fixedPoint,.72);
const movingFragment=putModel(archFragment(),movingPoint(railT),.72);
const fixedSleeping=putModel(createGoddess(),fixedPoint,.57);
const movingSleeping=putModel(createGoddess(),movingPoint(railT),.57);
const oldSleeping=putModel(createGoddess(),[oldSpot[0],6.86,oldSpot[2]],.98);
const oldAwake=putModel(archFragment(),[oldSpot[0],6.86,oldSpot[2]],.98);
const oldStone=world.disk(.91,6.86,oldSpot[0],oldSpot[2]);
const poolAForm=putModel(archFragment(),radial(6.7,poolTheta,0),.5);
const poolBForm=putModel(archFragment(),radial(2.7,poolTheta,0),.5);
const upperArmillary=putModel(createArmillary(),radial(17.2,300,24));
const finalArmillary=putModel(createArmillary({apple:false}),[0,0,0]);
const prism=putModel(createArmillary({apple:false}),radial(17.4,225,24),.65);
const shrines=[
 {id:'day',name:'日之龛',point:sideShrine,active:false},
 {id:'rainbow',name:'彩虹龛',point:radial(17.5,225,24),active:false},
 {id:'moon',name:'月之龛',point:radial(17.5,150,0),active:false},
];
for(const shrine of shrines){
 const marker=labelSprite(shrine.name,{scale:1.6});marker.position.set(shrine.point[0],shrine.point[1]+2.4,shrine.point[2]);scene.add(marker);shrine.marker=marker;
}

const avatar=new THREE.Group();scene.add(avatar);
const robe=new THREE.Mesh(new THREE.ConeGeometry(.38,1.17,12),new THREE.MeshStandardMaterial({color:0x566d72,roughness:.82}));robe.position.y=.68;robe.castShadow=true;avatar.add(robe);
const head=new THREE.Mesh(new THREE.SphereGeometry(.22,16,12),new THREE.MeshStandardMaterial({color:0xe4d5b5,roughness:.78}));head.position.y=1.47;head.castShadow=true;avatar.add(head);
const carried=new THREE.PointLight(0xffd9a4,.55,4);carried.position.y=1.15;avatar.add(carried);
const player=new PlayerMotor({position:checkpoint.position});

function collision(p,r,h){
 if(world.blocked(p,r,h))return true;
 for(const o of art.obstacles){
  if(p[1]>=o.top-.03||p[1]+h<=o.bottom+.03)continue;
  if(o.type==='cylinder'&&Math.hypot(p[0]-o.x,p[2]-o.z)<o.radius+r)return true;
  if(o.type==='box'&&p[0]>o.minX-r&&p[0]<o.maxX+r&&p[2]>o.minZ-r&&p[2]<o.maxZ+r)return true;
  if(o.type==='orientedBox'){
   const dx=p[0]-o.x,dz=p[2]-o.z,c=Math.cos(o.rotationY),s=Math.sin(o.rotationY);
   if(Math.abs(c*dx-s*dz)<o.halfX+r&&Math.abs(s*dx+c*dz)<o.halfZ+r)return true;
  }
 }
 return false;
}
const activePhase=()=>{
 const p=player.position,a=angle(p),r=radialLength(p);
 if(stage<3)return dayF(stage,a);
 if(stage===3){
  const ascent=segmentDistanceXZ(p,roofFoot,roofTop);
  return ascent.distance<1.65&&r<12.8?44.2732:uniformPhase(a*DEG,270*DEG,304*DEG,39.45454545,44.2732);
 }
 if(stage===4){
  if(p[1]<23.8)return night?98:74.15;
  if(r<15.8)return 44.2732;
  return uniformPhase(a*DEG,roofAngle*DEG,305*DEG,44.2732,74.15);
 }
 if(stage===5){
  if(r>16.5&&a<=327)return uniformPhase(a*DEG,327*DEG,250*DEG,101.6,106.4);
  return uniformPhase(a*DEG,345*DEG,315*DEG,98,104);
 }
 if(stage===6){
  if(r<10.8)return uniformPhase(a*DEG,moonTheta*DEG,207*DEG,105,115);
  return 105+(moonTheta-a)*.035;
 }
 if(stage===7){
  if(r>15.6)return uniformPhase(a*DEG,oldAngle*DEG,(oldAngle-41)*DEG,145,147);
  return uniformPhase(a*DEG,207*DEG,oldAngle*DEG,115,145);
 }
 if(stage===8)return r<9?150:uniformPhase(a*DEG,(oldAngle-41)*DEG,poolTheta*DEG,147,150);
 return 150;
};
const moonSource=()=>moonDirection(phase);
function save(){
 const data={version:1,checkpoint,stage,night,apple,sunYaw,moonYaw,swanYaw,poolYaw,railT,shrines:shrines.map(s=>s.active),journal:progress.toJSON()};
 try{localStorage.setItem(SAVE,JSON.stringify(data));}catch{/* Private browsing may refuse local storage. */}
}
function load(){
 try{
  const data=JSON.parse(localStorage.getItem(SAVE)||'null');
  if(data?.version!==1||!Number.isInteger(data.stage)||data.stage<0||data.stage>9||!Array.isArray(data.checkpoint?.position)||data.checkpoint.position.length!==3||!data.checkpoint.position.every(Number.isFinite))return false;
  stage=data.stage;night=Boolean(data.night);apple=Boolean(data.apple);iris=stage>=5?1:0;
  checkpoint={stage,phase:data.checkpoint.phase,position:[...data.checkpoint.position]};
  for(const k of ['sunYaw','moonYaw','swanYaw','poolYaw','railT'])if(Number.isFinite(data[k])){
   if(k==='railT')railT=clamp(data[k]);else if(Math.abs(data[k])<2)({sunYaw:()=>sunYaw=data[k],moonYaw:()=>moonYaw=data[k],swanYaw:()=>swanYaw=data[k],poolYaw:()=>poolYaw=data[k]})[k]();
  }
  data.shrines?.forEach((v,i)=>{if(shrines[i])shrines[i].active=Boolean(v);});
  const journal=NightProgress.fromJSON(data.journal);
  for(const id of journal.discovered)progress.discover(id);
  for(const id of journal.completed)progress.complete(id);
  player.teleport(checkpoint.position);return true;
 }catch{return false;}
}
function setStage(next,position){
 if(next<=stage)return;
 stage=next;checkpoint={stage:next,position:[...position],phase};
 player.teleport(position);fallPeak=position[1];
 if(next>=5){night=true;iris=1;}
 save();toast(chapters[next][0]+' · '+chapters[next][1],6);
}
function respawn(){
 player.teleport(checkpoint.position);fallPeak=checkpoint.position[1];
 toast('回到最近的安全台。光与雕像的朝向保留。',3);
}
function journal(id){progress.discover(id);if(progress.complete(id))save();}
function updateSolar(){
 const sun=sunDirection(phase),isDay=!night;
 const top1=T1,top2=T2;
 const foot1=sub(top1,scale(sun,6/Math.max(.12,sun[1])));
 const foot2=sub(top2,scale(sun,6/Math.max(.12,sun[1])));
 const direct1=isDay&&stage<=1&&optics.directLit(add(top1,[0,.10,0]),sun);
 const direct2=isDay&&stage>=1&&stage<=2&&optics.directLit(add(top2,[0,.10,0]),sun);
 dayPaths[0].set(foot1,top1,direct1);
 dayPaths[1].set(foot2,top2,direct2);
 const sideFoot=sub(T2side,scale(sun,6/Math.max(.12,sun[1])));
 const sideOn=isDay&&stage>=1&&stage<=2&&optics.directLit(add(T2side,[0,.08,0]),sun);
 dayPaths[2].set(sideFoot,T2side,sideOn);
 const n=rotateY(normalDay,sunYaw),reflected=reflect(scale(sun,-1),n);
 const hit=rayPlane(M,reflected,[0,18,0],[0,1,0]);
 const thirdOn=isDay&&stage>=2&&stage<=3&&sun[1]>.05&&Boolean(hit)
  &&optics.directLit(add(M,[0,.04,0]),sun,[mirrorDay.userData.mirrorDisk]);
 dayPaths[3].set(M,hit?.point||T3,thirdOn);
 const roofOn=isDay&&stage>=3&&stage<=4&&optics.directLit(add(roofTop,[0,.08,0]),sunDirection(44.2732));
 dayPaths[4].set(roofFoot,roofTop,roofOn);
 solarIncoming.set(add(M,scale(sun,8)),M,thirdOn);
 orientMirror(mirrorDay,n,M);
 // The upper ray is intentionally constant across the central connection.
 const roofBeam=stage===3&&segmentDistanceXZ(player.position,roofFoot,roofTop).distance<1.55;
 if(roofBeam)solarIncoming.set(add(roofTop,scale(sunDirection(44.2732),9)),roofTop,true);
 sunOrb.visible=isDay;sunOrb.position.copy(V(scale(sunDirection(Math.min(phase,74.15)),80)));
}
function updateMoon(dt){
 const moon=moonSource();
 const illuminate=(position,exclude=[])=>night&&optics.directLit(position,moon,exclude);
 const swanSample=add(sculpturePoint,[0,1.38,0]);
 n1Exposure=stage>=5&&illuminate(swanSample,[muralWall]);
 moonForms.swan.update(n1Exposure,dt);
 swan.rotation.y=-.8+swanYaw;
 const projected=muralShadow.update(scale(moon,-1));
 n1Score=shadowAlignment(projected,targetLandmarks,{positionTolerance:1.15});
 const swanReady=n1Exposure&&moonForms.swan.value>.92&&n1Score>.52;
 goddess.visible=moonForms.swan.value<.96;swan.visible=moonForms.swan.value>.04;
 goddess.scale.setScalar(.62*(1-moonForms.swan.value));swan.scale.setScalar(.62*moonForms.swan.value);
 muralShadow.group.visible=swan.visible&&n1Exposure;moonGlyph.visible=stage===5&&!n1Exposure;
 n1Bridge.enabled=n1Bridge.mesh.visible=swanReady;n1Door.visible=!swanReady;
 if(swanReady)journal('swan-mural');

 const mNormal=rotateY(normalMoon,moonYaw),moving=movingPoint(railT);
 n2Direct=stage>=6&&illuminate(add(fixedPoint,[0,2.5,0]));
 n2Reflected=stage>=6&&night&&optics.reflectedLit(add(moving,[0,2.5,0]),moonM,mNormal,moon,1.3,[mirrorNight.userData.mirrorDisk]);
 moonForms.fixed.update(n2Direct,dt);moonForms.moving.update(n2Reflected,dt);
 fixedFragment.visible=moonForms.fixed.value>.08;fixedSleeping.visible=moonForms.fixed.value<.96;
 movingFragment.visible=moonForms.moving.value>.08;movingSleeping.visible=moonForms.moving.value<.96;
 movingFragment.position.set(...moving);movingSleeping.position.set(...moving);
 pairReady=pairAlignment(radial(11.3+(1-railT)*2.9,moonTheta,12),radial(11.3,moonTheta,12),n2Direct,n2Reflected,.23)
  &&moonForms.fixed.value>.92&&moonForms.moving.value>.92;
 n2BridgeFixed.enabled=n2BridgeFixed.mesh.visible=n2Direct&&moonForms.fixed.value>.92;
 n2BridgeMoving.enabled=n2BridgeMoving.mesh.visible=pairReady;
 if(pairReady)journal('moon-pair');
 oldReady=stage>=7&&night&&optics.reflectedLit(oldSpot,moonM,mNormal,moon,.58,[mirrorNight.userData.mirrorDisk]);
 moonForms.old.update(oldReady,dt);oldSleeping.visible=moonForms.old.value<.96;oldAwake.visible=moonForms.old.value>.08;
 n3Bridge.enabled=n3Bridge.mesh.visible=oldReady&&moonForms.old.value>.92;
 if(n3Bridge.enabled)journal('old-crown');
 orientMirror(mirrorNight,mNormal,moonM);
 const outgoing=reflect(scale(moon,-1),mNormal);
 moonIncoming.set(add(moonM,scale(moon,9)),moonM,night&&stage>=6);
 moonReturning.set(moonM,add(moonM,scale(outgoing,12)),night&&stage>=6);

 const pNormal=rotateY(normalPool,poolYaw),poolA=add(radial(6.7,poolTheta,0),[0,.2,0]);
 poolAExposure=stage>=8&&illuminate(poolA);
 poolBExposure=stage>=8&&night&&optics.reflectedLit(poolTarget,poolMirror,pNormal,moon,.64,[mirrorPool.userData.mirrorDisk]);
 moonForms.poolA.update(poolAExposure,dt);moonForms.poolB.update(poolBExposure,dt);
 poolAForm.visible=moonForms.poolA.value>.08;poolBForm.visible=moonForms.poolB.value>.08;
 poolReady=dualBridgeReady(poolAExposure,poolBExposure,moonForms.poolA.value,moonForms.poolB.value);
 poolASpan.enabled=poolASpan.mesh.visible=poolAExposure&&moonForms.poolA.value>.92;
 poolBSpan.enabled=poolBSpan.mesh.visible=poolReady;
 if(poolReady)journal('water-court');
 orientMirror(mirrorPool,pNormal,poolMirror);
 poolReturning.set(poolMirror,poolTarget,stage>=8&&poolBExposure);
}

function near(p,q,r=2.9,y=3.2){return Math.hypot(p[0]-q[0],p[2]-q[2])<r&&Math.abs(p[1]-q[1])<y;}
function advance(){
 const p=player.position,a=angle(p),r=radialLength(p);
 if(stage===0&&near(p,T1,3.2)&&p[1]>5.83)setStage(1,radial(15.1,58,6));
 else if(stage===1&&near(p,T2,3.2)&&p[1]>11.82)setStage(2,radial(15.1,166,12));
 else if(stage===2&&near(p,T3,3.2)&&p[1]>17.82)setStage(3,radial(15.1,276,18));
 else if(stage===3&&p[1]>23.82&&r<6.3)setStage(4,roofTop);
 else if(stage===4&&p[1]<18.2&&a>338)setStage(5,radial(17.2,345,18));
 else if(stage===5&&p[1]<12.21&&a>244&&a<258)setStage(6,radial(14.3,250,12));
 else if(stage===6&&p[1]<6.21&&r<10.4&&a>201&&a<214)setStage(7,radial(12,207,6));
 else if(stage===7&&p[1]<.21&&r>15.8&&Math.abs(a-(oldAngle-41))<8)setStage(8,radial(16.3,oldAngle-41,0));
 else if(stage===8&&r<2.25&&poolReady)setStage(9,[0,0,1.8]);
 // A descending chapter deliberately travels a full storey below its save
 // platform. Compare with that chapter's *destination*, not the save height.
 const bottom=[-1.8,4.2,10.2,16.2,17.3,11.3,5.3,-1.4,-1.4,-1.4][stage];
 if(p[1]<bottom||r>20.3)respawn();
}
function markAndAct(kind){
 if(kind==='apple'){
  if(!apple){apple=true;upperArmillary.userData.apple.visible=false;toast('一枚很轻的金苹果。它在等待归处。');save();}
  return;
 }
 if(kind==='prism'){
  const s=shrines[1];if(!s.active){s.active=true;toast('彩虹龛：光穿过玻璃，仍旧是同一束光。');save();}return;
 }
 if(kind==='finish'){
  if(!apple){toast('浑天仪的空位还在等待金苹果。');return;}
  ended=true;finalArmillary.userData.apple.visible=true;
  $('#ending-journal').textContent=shrines.filter(s=>s.active).length===3?'三座小龛也记住了你走过的光。':'你走过的每一道光，都留在建筑里。';
  $('#ending').classList.remove('hidden');save();return;
 }
 const shrine=shrines.find(s=>s.id===kind);
 if(shrine&&!shrine.active){shrine.active=true;shrine.marker.material.color.set('#fff0be');toast(`${shrine.name} · 这束光有了见证。`);save();}
}
function interactions(dt){
 nearest=null;const p=player.position,options=[];
 const offer=(id,label,pos,maxDistance=3.15)=>{if(near(p,pos,maxDistance,3.3))options.push({id,label,pos,d:distance(p,pos)});};
 if(stage===2)offer('solar-mirror','Q / R · 旋转日镜',M,3.65);
 if(stage===4){offer('apple','E · 拾取金苹果',radial(17.2,300,24),3.8);offer('prism','E · 观察彩虹龛',radial(17.4,225,24),3.1);}
 if(stage===5)offer('swan','Q / R · 旋转月下天鹅',sculpturePoint,3.5);
 if(stage===6){offer('moon-mirror','Q / R · 调整月镜',moonM,3.5);offer('rail','Q / R · 沿轨移动月石',movingPoint(railT),3.1);}
 if(stage===8)offer('pool-mirror','Q / R · 调整岸边镜面',radial(8.7,poolTheta,0),3.2);
 if(stage===9)offer('finish','E · 放回金苹果',[0,0,0],3);
 if(stage<=2)offer('day','E · 探访日之龛',sideShrine,2.7);
 if(stage>=8)offer('moon','E · 探访月之龛',shrines[2].point,2.7);
 options.sort((a,b)=>a.d-b.d);nearest=options[0]||null;
 if(nearest){$('#actions').classList.remove('hidden');$('#interaction').textContent=nearest.label;}
 else $('#actions').classList.add('hidden');
 const fine=keys.has('ShiftLeft')||keys.has('ShiftRight'),delta=dt*(fine?.13:.55)*(Number(keys.has('KeyR'))-Number(keys.has('KeyQ')));
 if(nearest&&delta){
  if(nearest.id==='solar-mirror')sunYaw=clamp(sunYaw+delta,-1.2,1.2);
  if(nearest.id==='swan')swanYaw=clamp(swanYaw+delta,-1.6,1.6);
  if(nearest.id==='moon-mirror')moonYaw=clamp(moonYaw+delta,-1.2,1.2);
  if(nearest.id==='pool-mirror')poolYaw=clamp(poolYaw+delta,-1.2,1.2);
  if(nearest.id==='rail')railT=clamp(railT+delta*.7);
  if(nearest.id==='rail'&&railT>.993)railT=1;
 }
 if(keys.has('KeyE')&&!lastE&&nearest&&!['solar-mirror','swan','moon-mirror','rail','pool-mirror'].includes(nearest.id))markAndAct(nearest.id);
 lastE=keys.has('KeyE');
 let status='';
 if(stage===2)status=`镜面 ${Math.round(sunYaw/DEG)}° · 观察光是否到达上层`;
 if(stage===5)status=`影子的吻合度 ${Math.round(n1Score*100)}% · ${n1Exposure?'正在受月光照耀':'女神未受月光照耀'}`;
 if(stage===6)status=`两半月石 ${Math.round(railT*100)}% · ${n2Direct&&n2Reflected?'两者都在光里':'寻找两束月光'}`;
 if(stage===7)status=oldReady?'高处的冠饰被旧镜照亮':'沿廊改变月位，抬头看那片冠饰';
 if(stage===8)status=`水桥：直射 ${poolAExposure?'已到':'未到'} · 返照 ${poolBExposure?'已到':'未到'}`;
 $('#alignment').textContent=status;
}
function drawMap(){
 const c=$('#plan'),g=c.getContext('2d'),W=c.width,H=c.height,cx=W/2,cy=H/2,S=11;
 g.clearRect(0,0,W,H);g.fillStyle='#1c3740';g.fillRect(0,0,W,H);
 const xy=(r,a)=>[cx+r*S*Math.cos(a*DEG),cy+r*S*Math.sin(a*DEG)];
 for(const r of [4.5,8,10.5,11.2,14.8,19.1]){g.beginPath();g.arc(cx,cy,r*S,0,2*Math.PI);g.lineWidth=r===19.1?3:1;g.strokeStyle=r===10.5?'#e2d2a360':'#a5bec069';g.stroke();}
 for(let a=15;a<360;a+=30){const [x,z]=xy(10.5,a);g.beginPath();g.arc(x,z,3.2,0,7);g.fillStyle='#f1e1bd';g.fill();}
 for(let a=20;a<340;a+=20){const [x,z]=xy(11.3,a),[X,Z]=xy(14.5,a);g.beginPath();g.moveTo(x,z);g.lineTo(X,Z);g.strokeStyle='#51aeb788';g.lineWidth=1;g.stroke();}
 for(const [p,q,color] of [[F1,T1,'#ffe2a0'],[F2,T2,'#ffe2a0'],[M,T3,'#ffe2a0'],[roofFoot,roofTop,'#ffe2a0'],[radial(12,oldAngle,6),radial(17.2,oldAngle,6),'#b4d9f5']]){g.beginPath();g.moveTo(cx+p[0]*S,cy+p[2]*S);g.lineTo(cx+q[0]*S,cy+q[2]*S);g.strokeStyle=color;g.lineWidth=4;g.stroke();}
 const [x,z]=[cx+player.position[0]*S,cy+player.position[2]*S];g.beginPath();g.arc(x,z,6,0,7);g.fillStyle='#fff';g.fill();
 $('#map-legend').textContent=`当前 ${chapters[stage][0]} · ${night?'月位':'日位'} H ${phase.toFixed(1)}° · 楼层 +${Math.round(player.position[1])}m`;
}
function updateHUD(){
 const [title,goal,detail]=chapters[stage];$('#chapter').textContent=title;$('#objective').textContent=goal;$('#detail').textContent=detail;
 $('#phase-label').textContent=(night?'☾ 月位':'☼ 日位')+` · H ${phase.toFixed(1)}°`;
 $('#phase-fill').style.width=`${clamp(phase/150)*100}%`;
}
function updateCelestial(){
 const direction=night?moonDirection(phase):sunDirection(phase);
 const lightPos=scale(direction,70);celestial.position.copy(V(lightPos));celestial.target.position.set(0,8,0);celestial.target.updateMatrixWorld();
 celestial.color.setHex(night?0xc3d9ff:0xffe0ac);celestial.intensity=night?2.0:3.7;
 hemi.color.setHex(night?0x7d9fb5:0xc7e4f2);hemi.intensity=night?1.1:2.2;
 scene.background.setHex(night?0x0e1d30:0xa9c5c7);scene.fog.color.copy(scene.background);
 sunOrb.visible=!night;stars.material.opacity=night?.68:0;
}
function cameraUpdate(dt){
 const p=V(player.position),look=p.clone().add(new THREE.Vector3(0,1.4,0));
 const distanceWanted=overview?22:cameraDistance;
 const raw=look.clone().add(new THREE.Vector3(Math.sin(cameraYaw)*Math.cos(cameraPitch)*distanceWanted,Math.sin(cameraPitch)*distanceWanted+1.1,Math.cos(cameraYaw)*Math.cos(cameraPitch)*distanceWanted));
 const trace=new THREE.Raycaster(look,raw.clone().sub(look).normalize(),.1,distanceWanted);
 const hit=trace.intersectObjects([...art.occluders,...world.occluders].filter(m=>m.visible),false)[0];
 if(hit)raw.copy(look).add(raw.sub(look).normalize().multiplyScalar(Math.max(.7,hit.distance-.24)));
 camera.position.lerp(raw,Math.min(1,dt*9));camera.lookAt(look);
 avatar.position.set(...player.position);avatar.rotation.y=cameraYaw+Math.PI;
}
function startGame(resume=false){
 if(resume&&!load()){toast('没有可用存档，从入口开始。');}
 if(!resume){stage=0;night=false;apple=false;player.teleport(radial(14,20,0));checkpoint={stage:0,position:[...player.position],phase:0};save();}
 started=true;$('#welcome').classList.add('hidden');$('#journey').classList.remove('hidden');$('#controls').classList.remove('hidden');
 camera.position.set(player.position[0]+3,player.position[1]+4,player.position[2]+4);updateHUD();
}
$('#start').addEventListener('click',()=>startGame());
$('#resume').addEventListener('click',()=>startGame(true));
$('#close-map').addEventListener('click',()=>$('#map').classList.add('hidden'));
$('#return').addEventListener('click',()=>$('#ending').classList.add('hidden'));
$('#restart').addEventListener('click',()=>{try{localStorage.removeItem(SAVE);}catch{}location.reload();});
try{if(localStorage.getItem(SAVE))$('#resume').classList.remove('hidden');}catch{}
window.addEventListener('keydown',e=>{
 if(['Space','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Tab'].includes(e.code))e.preventDefault();
 keys.add(e.code);
});
window.addEventListener('keyup',e=>keys.delete(e.code));
window.addEventListener('blur',()=>keys.clear());
$('#scene').addEventListener('pointerdown',e=>{dragging=true;$('#scene').setPointerCapture(e.pointerId);});
$('#scene').addEventListener('pointermove',e=>{if(dragging){cameraYaw-=e.movementX*.006;cameraPitch=clamp(cameraPitch+e.movementY*.004,-.1,1.1);}});
$('#scene').addEventListener('pointerup',()=>dragging=false);
$('#scene').addEventListener('wheel',e=>{cameraDistance=clamp(cameraDistance+e.deltaY*.008,3.1,11);},{passive:true});
window.addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
let last=performance.now();
function frame(now){
 requestAnimationFrame(frame);const dt=Math.min(.05,Math.max(0,(now-last)/1000));last=now;elapsed+=dt;
 if(!started){art.update(elapsed,false,0);camera.position.set(31,31,31);camera.lookAt(0,10,0);renderer.render(scene,camera);return;}
 if(!ended){
  const toggle=(code,prior,callback)=>{const held=keys.has(code);if(held&&!prior)callback();return held;};
  lastH=toggle('KeyH',lastH,()=>toast(hints[stage],7));
  lastX=toggle('KeyX',lastX,respawn);
  lastTab=toggle('Tab',lastTab,()=>{$('#map').classList.toggle('hidden');drawMap();});
  const forward=[-Math.sin(cameraYaw),-Math.cos(cameraYaw)],right=[Math.cos(cameraYaw),-Math.sin(cameraYaw)];
  const w=Number(keys.has('KeyW')||keys.has('ArrowUp'))-Number(keys.has('KeyS')||keys.has('ArrowDown'));
  const d=Number(keys.has('KeyD')||keys.has('ArrowRight'))-Number(keys.has('KeyA')||keys.has('ArrowLeft'));
  player.update(dt,{move:[forward[0]*w+right[0]*d,forward[1]*w+right[1]*d],jump:keys.has('Space')},world.support,collision);
  phase=activePhase();
  if(stage===4&&player.position[1]>=23.8&&radialLength(player.position)>15.6)iris=clamp(iris+dt*.23);
  if(stage===4&&player.position[1]<21.1&&angle(player.position)>305)night=true;
  art.update(elapsed,night,iris);scene.updateMatrixWorld(true);
  updateCelestial();updateSolar();updateMoon(dt);interactions(dt);advance();updateHUD();
  if(!$('#map').classList.contains('hidden'))drawMap();
 }
 if(lastToast&&elapsed>lastToast){$('#toast').classList.remove('show');lastToast=0;}
 upperArmillary.userData.apple.visible=!apple;
 cameraUpdate(dt);renderer.render(scene,camera);
}
// A test hook only for isolated visual fixtures; real route QA uses key input.
if(debug)window.__dysisQA={get state(){return{stage,phase,night,apple,position:[...player.position],grounded:player.grounded,ready:{swan:n1Bridge.enabled,pair:pairReady,old:oldReady,pool:poolReady},exposure:{n1Exposure,n2Direct,n2Reflected,poolAExposure,poolBExposure}};},
  fixture(n,pos){if(!Number.isInteger(n)||n<0||n>9||!Array.isArray(pos)||pos.length!==3)return;stage=n;night=n>=5;iris=n>=5?1:0;player.teleport(pos);checkpoint={stage:n,position:[...pos],phase:0};},
  phaseAt:p=>{const prior=[...player.position];player.teleport(p);const value=activePhase();player.teleport(prior);return value;}
};
requestAnimationFrame(frame);
