import * as THREE from '../vendor/three.module.js';
import {DEG, polar, segmentDistanceXZ, clamp} from '../core/math.js';

const V = a => new THREE.Vector3(...a);
export function makeWorld(scene, materials) {
  const surfaces = [], occluders = [], blockers = [];
  const stone = materials.lightStone;
  const add = (mesh, shadow=true) => {
    scene.add(mesh); mesh.castShadow=shadow; mesh.receiveShadow=true;
    if(shadow) occluders.push(mesh);
    return mesh;
  };
  function quad(a,b,width,material=stone,{solid=true,shadow=true,name='walk'}={}) {
    const dx=b[0]-a[0], dz=b[2]-a[2], l=Math.hypot(dx,dz)||1;
    const ox=-dz/l*width/2, oz=dx/l*width/2;
    const points=[a[0]+ox,a[1],a[2]+oz,a[0]-ox,a[1],a[2]-oz,
      b[0]+ox,b[1],b[2]+oz,b[0]-ox,b[1],b[2]-oz];
    const g=new THREE.BufferGeometry();
    g.setAttribute('position',new THREE.Float32BufferAttribute(points,3));
    g.setIndex([0,2,1,1,2,3]);g.computeVertexNormals();
    const mesh=add(new THREE.Mesh(g,material),shadow); mesh.name=name;
    const surface={mesh,a:[...a],b:[...b],width,enabled:solid,kind:'strip',
      heightAt(x,z){ const q=segmentDistanceXZ([x,0,z],this.a,this.b);
        const dot=(x-this.a[0])*(this.b[0]-this.a[0])+(z-this.a[2])*(this.b[2]-this.a[2]);
        const len2=(this.b[0]-this.a[0])**2+(this.b[2]-this.a[2])**2;
        return dot>=-.02&&dot<=len2+.02&&q.distance<=this.width/2?q.y:null; }};
    surfaces.push(surface);
    surface.update=(aa,bb,enabled=true)=>{
      surface.a=[...aa];surface.b=[...bb];surface.enabled=enabled;mesh.visible=enabled;
      const xx=bb[0]-aa[0],zz=bb[2]-aa[2],ll=Math.hypot(xx,zz)||1;
      const sx=-zz/ll*width/2,sz=xx/ll*width/2;
      const p=mesh.geometry.attributes.position;
      [[aa[0]+sx,aa[1],aa[2]+sz],[aa[0]-sx,aa[1],aa[2]-sz],
       [bb[0]+sx,bb[1],bb[2]+sz],[bb[0]-sx,bb[1],bb[2]-sz]].forEach((v,i)=>p.setXYZ(i,...v));
      p.needsUpdate=true;g.computeVertexNormals();g.computeBoundingSphere();
    };
    return surface;
  }
  function annulus(inner,outer,y,start=7,end=353,holes=[],material=stone) {
    // Each cell is shared by rendering and collision. No invisible floor across
    // the light wells, including cells partially cut by a corridor.
    const vertices=[], cells=[];
    const steps=Math.ceil((end-start)/2), bands=Math.ceil((outer-inner)/.65);
    for(let i=0;i<steps;i++)for(let j=0;j<bands;j++) {
      const a=(start+(end-start)*i/steps)*DEG,b=(start+(end-start)*(i+1)/steps)*DEG;
      const r=inner+(outer-inner)*j/bands,R=inner+(outer-inner)*(j+1)/bands;
      const corners=[polar(r,a,y),polar(R,a,y),polar(R,b,y),polar(r,b,y)];
      const center=polar((r+R)/2,(a+b)/2,y);
      if(holes.some(h=>h(center)||corners.some(h)))continue;
      for(const k of [0,2,1,0,3,2])vertices.push(...corners[k]);
      cells.push({a,b,r,R});
    }
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.computeVertexNormals();
    const mesh=add(new THREE.Mesh(g,material));mesh.name=`Stone gallery +${y}m`;
    surfaces.push({mesh,kind:'ring',enabled:true,heightAt(x,z){let a=Math.atan2(z,x);if(a<0)a+=2*Math.PI;const r=Math.hypot(x,z);
      return cells.some(c=>a>=c.a&&a<=c.b&&r>=c.r&&r<=c.R)?y:null;}});
    return mesh;
  }
  function box(size,pos,material=stone,{block=true,shadow=true}={}){
    const mesh=add(new THREE.Mesh(new THREE.BoxGeometry(...size),material),shadow);mesh.position.set(...pos);
    if(block)blockers.push({kind:'box',position:pos,size,mesh});return mesh;
  }
  function disk(radius,y,x=0,z=0,material=stone){
    const mesh=add(new THREE.Mesh(new THREE.CylinderGeometry(radius,radius,.28,64),material));mesh.position.set(x,y-.14,z);
    surfaces.push({mesh,enabled:true,kind:'disk',heightAt(X,Z){return Math.hypot(X-x,Z-z)<=radius?y:null;}});return mesh;
  }
  function stairs(radius,a0,a1,y0,y1,width=2.2,material=stone) {
    const steps=Math.ceil(Math.abs(y1-y0)/.17), result=[];
    for(let i=0;i<steps;i++){
      const a=(a0+(a1-a0)*i/steps)*DEG,b=(a0+(a1-a0)*(i+1)/steps)*DEG;
      const yy=y0+(y1-y0)*(i+1)/steps;
      result.push(quad(polar(radius,a,yy),polar(radius,b,yy),width,material));
      const p=polar(radius,(a+b)/2,yy-.09);
      const riser=box([width,.18,Math.abs(b-a)*radius+.035],p,material,{block:false});riser.rotation.y=-(a+b)/2;
    }return result;
  }
  function straightStairs(a,b,width=2.2,material=stone){
    const n=Math.ceil(Math.abs(b[1]-a[1])/.17);
    for(let i=0;i<n;i++){
      const mix=(t,y)=>[a[0]+(b[0]-a[0])*t,y,a[2]+(b[2]-a[2])*t];
      const y=a[1]+(b[1]-a[1])*(i+1)/n;
      quad(mix(i/n,y),mix((i+1)/n,y),width,material);
    }
  }
  function line(points,color=0xab8750,opacity=1){
    const g=new THREE.BufferGeometry().setFromPoints(points.map(V));
    return add(new THREE.Line(g,new THREE.LineBasicMaterial({color,transparent:opacity<1,opacity})),false);
  }
  function support(x,z,fromY,maxDrop){
    let best=null;
    for(const s of surfaces){if(!s.enabled||!s.mesh.visible)continue;const y=s.heightAt(x,z);
      if(y!==null&&y<=fromY+.001&&y>=fromY-maxDrop-.001&&(best===null||y>best))best=y;}
    return best;
  }
  function blocked(p,r,h){
    if(Math.hypot(p[0],p[2])>20.15)return true;
    // The full-height carved wall closes the zero-degree seam. The center is
    // not a way around it on any gallery.
    if(p[0]>8.7&&Math.abs(p[2])<.85+r&&p[1]<24.2)return true;
    return blockers.some(o=>{if(o.mesh&&!o.mesh.visible)return false;
      if(o.kind==='box')return Math.abs(p[0]-o.position[0])<o.size[0]/2+r&&Math.abs(p[2]-o.position[2])<o.size[2]/2+r&&p[1]+h>o.position[1]-o.size[1]/2+.02&&p[1]<o.position[1]+o.size[1]/2-.02;
      return false;});
  }
  return {surfaces,occluders,blockers,add,quad,annulus,box,disk,stairs,straightStairs,line,support,blocked};
}

export function stripHole(a,b,width){return p=>segmentDistanceXZ(p,a,b).distance<width/2;}
export function sectorHole(r0,r1,a0,a1){return p=>{const r=Math.hypot(p[0],p[2]);let a=Math.atan2(p[2],p[0])/DEG;if(a<0)a+=360;return r>r0&&r<r1&&a>a0&&a<a1;};}

export function labelSprite(text,{color='#decaa0',size=256,scale=1.5}={}){
  const c=document.createElement('canvas');c.width=size*2;c.height=size;
  const ctx=c.getContext('2d');ctx.font='500 58px Georgia, serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle=color;ctx.fillText(text,size,size/2);
  const texture=new THREE.CanvasTexture(c);
  const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,transparent:true,depthWrite:false}));sprite.scale.set(scale*2,scale,1);return sprite;
}
