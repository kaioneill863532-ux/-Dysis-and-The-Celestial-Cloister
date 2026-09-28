import * as THREE from '../vendor/three.module.js';
import {add,sub,scale,normalize,dot,distance,rayPlane,reflect} from '../core/math.js';
import {solarBeamCells} from '../core/layout.js';

export function createOptics(scene,world) {
  const ray=new THREE.Raycaster();
  const point=(a)=>new THREE.Vector3(...a);
  function obstruction(origin,dir,max=80,ignore=[]){
    ray.set(point(add(origin,scale(dir,.045))),point(normalize(dir)));ray.far=max;
    return ray.intersectObjects(world.occluders.filter(m=>m.visible&&!ignore.includes(m)),false)[0]||null;
  }
  function directLit(p,source,ignore=[]){return source[1]>.025&&!obstruction(p,source,80,ignore);}
  function reflectedLit(p,origin,normal,source,radius=.8,ignore=[]){
    const outgoing=reflect(scale(source,-1),normal), offset=sub(p,origin),t=dot(offset,outgoing);
    if(t<0||distance(add(origin,scale(outgoing,t)),p)>radius)return false;
    return directLit(origin,source,ignore)&&!obstruction(origin,outgoing,Math.max(0,t-.1),ignore);
  }
  function path(name,color=0xffdc8a,width=2.8,{origin='b'}={}){
    const material=new THREE.MeshBasicMaterial({color,transparent:true,opacity:.64,side:THREE.DoubleSide,depthWrite:false});
    const surface=world.quad([0,-100,0],[0,-100,1],width,material,{solid:false,shadow:false,name});
    const pieces=Array.from({length:12},()=>world.quad([0,-100,0],[0,-100,1],width/12,material,{solid:false,shadow:false,name:name+' · clipped cell'}));
    const edges=[0,1].map(()=>{const m=new THREE.Line(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color,transparent:true,opacity:.95}));scene.add(m);return m;});
    let live=false;
    return {surface,material,edges,get live(){return live;},
      set(a,b,on=true,walkable=true){live=on;surface.update(a,b,on);surface.enabled=false;surface.mesh.visible=false;
        const start=origin==='a'?a:b,end=origin==='a'?b:a;
        const cells=on?solarBeamCells(start,sub(end,start),end[1],width,world.opticalCylinders||[],12):[];
        pieces.forEach((piece,i)=>{const cell=cells[i];if(!cell){piece.enabled=piece.mesh.visible=false;return;}
          const hit=obstruction(cell.startPoint,cell.direction,cell.end-.03);
          const cut=hit?add(cell.startPoint,scale(cell.direction,Math.max(0,hit.distance))):cell.endPoint;
          piece.update(cell.startPoint,cut,distance(cell.startPoint,cut)>.06);piece.enabled=piece.mesh.visible&&walkable;
        });
        const d=normalize([b[0]-a[0],0,b[2]-a[2]]),o=[-d[2]*width/2,0,d[0]*width/2];
        edges.forEach((m,i)=>{m.visible=on;m.geometry.dispose();m.geometry=new THREE.BufferGeometry().setFromPoints([point(add(a,scale(o,i?1:-1))),point(add(b,scale(o,i?1:-1)))]);});
      }};
  }
  function rayLine(name,color=0xa9d5f5){
    const line=new THREE.Line(new THREE.BufferGeometry(),new THREE.LineBasicMaterial({color,transparent:true,opacity:.7}));line.name=name;scene.add(line);
    return {mesh:line,set(a,b,on=true){line.visible=on;line.geometry.dispose();line.geometry=new THREE.BufferGeometry().setFromPoints([point(a),point(b)]);}};
  }
  function projectModel(model,planePoint,planeNormal,color=0x19283c){
    const group=new THREE.Group();scene.add(group);const parts=[];const material=new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide,transparent:true,opacity:.88,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-2});
    model.updateMatrixWorld(true);
    model.traverse(m=>{if(!m.isMesh)return;const geo=m.geometry.clone();const original=m.geometry.attributes.position;
      const shadow=new THREE.Mesh(geo,material);shadow.frustumCulled=false;group.add(shadow);parts.push({m,shadow,original});});
    return {group,update(dir){model.updateMatrixWorld(true);const landmarks=[];
      parts.forEach(({m,shadow,original})=>{const out=shadow.geometry.attributes.position;
        for(let i=0;i<original.count;i++){
          const w=new THREE.Vector3().fromBufferAttribute(original,i).applyMatrix4(m.matrixWorld).toArray();
          const hit=rayPlane(w,dir,planePoint,planeNormal);
          // The receiver is a 0.28 m slab centered on planePoint. Keep the
          // authored silhouette just beyond its face, instead of inside it.
          const q=hit?.point||planePoint;out.setXYZ(i,...add(q,scale(planeNormal,.16)));
          if(i%29===0)landmarks.push(q);
        }out.needsUpdate=true;shadow.geometry.computeBoundingSphere();});return landmarks;}};
  }
  return {obstruction,directLit,reflectedLit,path,rayLine,projectModel};
}
