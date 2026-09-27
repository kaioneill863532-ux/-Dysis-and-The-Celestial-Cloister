import * as THREE from '../vendor/three.module.js';
import {MODULE} from '../core/proportions.js';

const TAU = Math.PI * 2;
const DEG = Math.PI / 180;

// These ratios are a coherent fantasy-classical module, not an archaeological
// reconstruction of a particular Greek order.
export const ROTUNDA_PROPORTIONS = Object.freeze({
  diameter: 40,
  storyHeight: 6,
  bayCount: 12,
  bayAngle: 30,
  innerColumnAxisRadius: 10.5,
  columnShaftDiameter: MODULE.columnDiameter,
  columnShaftHeight: 4.7,
  columnBaseHeight: 0.44,
  capitalHeight: 0.49,
  columnOverallHeight: 5.64,
  columnOverallDiameterRatio: 5.64 / 0.7,
  humanReferenceHeight: 1.7,
  columnToHumanHeightRatio: 5.64 / 1.7,
  innerAxisChord: 2 * 10.5 * Math.sin(Math.PI / 12),
  facadeArchClearHalfSpan: 4.35,
  facadeArchSpringHeight: 3.48,
  facadeArchRise: 1.98,
  facadeArchRingThickness: 0.26,
  nicheFrameWidth: MODULE.nicheWidth,
  nicheFrameHeight: MODULE.nicheHeight,
  nicheFrameAspect: MODULE.nicheHeight / MODULE.nicheWidth,
  proportionNotes: 'The inner columns carry a lintel, the outer piers carry arches; the 4.52:2.80 niche frame is near phi. The plan uses twelve circular bay modules.',
  entablatureHeight: 0.29,
  galleryInnerRadius: 11.2,
  galleryOuterRadius: 14.5,
  outerNicheBand: [14.5, 19.2],
  roofWalkHeight: 24,
  irisHeight: 23.10,
  irisClosedClearRadius: 4.5,
  irisOpenClearRadius: 14,
});

function seededNoise(x, z, seed = 17) {
  const n = Math.sin(x * 127.1 + z * 311.7 + seed * 74.7) * 43758.5453;
  return n - Math.floor(n);
}

function marbleTexture() {
  const size = 128;
  const pixels = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const cloud = Math.sin(x * 0.067 + Math.sin(y * 0.054) * 2.2)
        + Math.sin(y * 0.043 + Math.sin(x * 0.025) * 1.1);
      const vein = Math.pow(Math.max(0, Math.sin(x * 0.075 + y * 0.027 + cloud * 0.62)), 15);
      const grain = seededNoise(x, y) * 5;
      const tone = 247 - vein * 21 - grain;
      const i = (y * size + x) * 4;
      pixels[i] = tone;
      pixels[i + 1] = tone - 1;
      pixels[i + 2] = tone - 4;
      pixels[i + 3] = 255;
    }
  }
  const texture = new THREE.DataTexture(pixels, size, size, THREE.RGBAFormat);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}

function makeMaterials() {
  const stoneMap = marbleTexture();
  return {
    stone: new THREE.MeshStandardMaterial({color: 0xe5decb, map: stoneMap, roughness: 0.79, metalness: 0.015}),
    lightStone: new THREE.MeshStandardMaterial({color: 0xf1e8d5, map: stoneMap, roughness: 0.71, metalness: 0.025}),
    warmStone: new THREE.MeshStandardMaterial({color: 0xcbb997, map: stoneMap, roughness: 0.87, metalness: 0}),
    darkStone: new THREE.MeshStandardMaterial({color: 0x7d8b91, roughness: 0.81, metalness: 0.05}),
    bronze: new THREE.MeshStandardMaterial({color: 0xb3945e, roughness: 0.42, metalness: 0.7}),
    relief: new THREE.MeshStandardMaterial({color: 0xd2c7ad, map: stoneMap, roughness: 0.84}),
    iris: new THREE.MeshStandardMaterial({color: 0xc1aa79, map: stoneMap, roughness: 0.49, metalness: 0.23, side: THREE.DoubleSide}),
    water: new THREE.MeshPhysicalMaterial({color: 0x729aab, roughness: 0.17, metalness: 0.22, clearcoat: 1, clearcoatRoughness: 0.12, transparent: true, opacity: 0.77, depthWrite: false}),
    sea: new THREE.MeshStandardMaterial({color: 0x426e83, roughness: 0.29, metalness: 0.3}),
  };
}

function annularSector(inner, outer, start = 0, sweep = TAU, segments = 72, depth = 0) {
  const positions = [];
  const uvs = [];
  const indices = [];
  const addLayer = y => {
    for (let i = 0; i <= segments; i += 1) {
      const a = start + sweep * i / segments;
      for (const r of [inner, outer]) {
        positions.push(Math.cos(a) * r, y, Math.sin(a) * r);
        uvs.push(Math.cos(a) * r / 4, Math.sin(a) * r / 4);
      }
    }
  };
  addLayer(0);
  for (let i = 0; i < segments; i += 1) {
    const a = i * 2;
    indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
  }
  if (depth > 0) {
    const offset = positions.length / 3;
    addLayer(-depth);
    for (let i = 0; i < segments; i += 1) {
      const a = i * 2;
      indices.push(offset + a, offset + a + 1, offset + a + 2,
        offset + a + 1, offset + a + 3, offset + a + 2);
      indices.push(a, offset + a, a + 2, a + 2, offset + a, offset + a + 2);
      indices.push(a + 1, a + 3, offset + a + 1, a + 3, offset + a + 3, offset + a + 1);
    }
    indices.push(0, 1, offset, 1, offset + 1, offset);
    const last = segments * 2;
    indices.push(last, offset + last, last + 1, last + 1, offset + last, offset + last + 1);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function slottedPetal(inner, outer, minimumZ, maximumZ, depth) {
  const start = -15.25 * DEG;
  const sweep = 30.5 * DEG;
  const points = [];
  const segments = 16;
  for (let i = 0; i <= segments; i += 1) {
    const a = start + sweep * i / segments;
    points.push(new THREE.Vector2(Math.cos(a) * outer, Math.sin(a) * outer));
  }
  for (let i = segments; i >= 0; i -= 1) {
    const a = start + sweep * i / segments;
    points.push(new THREE.Vector2(Math.cos(a) * inner, Math.sin(a) * inner));
  }
  function clip(input, boundary, above) {
    if (!Number.isFinite(boundary)) return input;
    const output = [];
    for (let i = 0; i < input.length; i += 1) {
      const a = input[i];
      const b = input[(i + 1) % input.length];
      const aInside = above ? a.y >= boundary : a.y <= boundary;
      const bInside = above ? b.y >= boundary : b.y <= boundary;
      if (aInside) output.push(a.clone());
      if (aInside !== bInside) {
        const t = (boundary - a.y) / (b.y - a.y);
        output.push(new THREE.Vector2(THREE.MathUtils.lerp(a.x, b.x, t), boundary));
      }
    }
    return output;
  }
  const clipped = clip(clip(points, minimumZ, true), maximumZ, false);
  const shape = new THREE.Shape(clipped);
  shape.closePath();
  const geometry = new THREE.ExtrudeGeometry(shape, {
    depth, bevelEnabled: false, steps: 1, curveSegments: 1,
  });
  // The polygon is drawn in XZ; positive extrusion becomes underside thickness.
  geometry.rotateX(Math.PI / 2);
  return geometry;
}

function flutedShaft(height, radius = 0.35) {
  const radial = 100;
  const rows = 12;
  const vertices = [];
  const uv = [];
  const indices = [];
  for (let j = 0; j <= rows; j += 1) {
    const t = j / rows;
    const envelope = radius * (1 - t * 0.085) + Math.sin(t * Math.PI) * 0.013;
    for (let i = 0; i <= radial; i += 1) {
      const a = i / radial * TAU;
      const r = envelope - 0.018 * (0.5 + 0.5 * Math.cos(20 * a));
      vertices.push(Math.cos(a) * r, t * height, Math.sin(a) * r);
      uv.push(i / radial * 2, t * 3);
      if (i < radial && j < rows) {
        const k = j * (radial + 1) + i;
        indices.push(k, k + radial + 1, k + 1, k + 1, k + radial + 1, k + radial + 2);
      }
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function ellipticalArch(halfSpan, rise, thickness, depth) {
  const shape = new THREE.Shape();
  const segments = 32;
  for (let i = 0; i <= segments; i += 1) {
    const a = i / segments * Math.PI;
    const x = Math.cos(a) * (halfSpan + thickness);
    const y = Math.sin(a) * (rise + thickness);
    if (i === 0) shape.moveTo(x, y); else shape.lineTo(x, y);
  }
  for (let i = segments; i >= 0; i -= 1) {
    const a = i / segments * Math.PI;
    shape.lineTo(Math.cos(a) * halfSpan, Math.sin(a) * rise);
  }
  shape.closePath();
  const geometry = new THREE.ExtrudeGeometry(shape, {depth, bevelEnabled: false, curveSegments: 24});
  geometry.translate(0, 0, -depth / 2);
  return geometry;
}

function smoothstep(a, b, value) {
  const t = THREE.MathUtils.clamp((value - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
}

export function createArchitecture(scene, {
  floorHeights = [0, 6, 12, 18], radius = 20, roofAngle = 2.45,
  decorateFloors = true, createSeam = true, createWater = true,
  facadeSlotFloors = [12], facadeSlotDegrees = 12,
} = {}) {
  const group = new THREE.Group();
  group.name = 'Dysis · architectural dressing';
  scene.add(group);
  const materials = makeMaterials();
  const occluders = [];
  const obstacles = [];
  const disposableGeometries = new Set();
  const floorDecorations = [];
  const roofY = 24;
  const columnRadius = 10.5;

  function add(geometry, material, parent = group, position = [0, 0, 0], occluder = false, name = '') {
    disposableGeometries.add(geometry);
    const object = new THREE.Mesh(geometry, material);
    object.position.set(...position);
    object.castShadow = true;
    object.receiveShadow = true;
    object.name = name;
    parent.add(object);
    if (occluder) {
      object.userData.opticalOccluder = true;
      occluders.push(object);
    }
    return object;
  }
  function band(inner, outer, y, material, parent = group, start = 0, sweep = TAU, depth = 0, solid = false) {
    return add(annularSector(inner, outer, start, sweep, Math.max(8, Math.ceil(96 * sweep / TAU)), depth), material, parent, [0, y, 0], solid);
  }
  function tube(curve, radiusValue, material, parent = group) {
    return add(new THREE.TubeGeometry(curve, 48, radiusValue, 6, false), material, parent);
  }

  const foundation = new THREE.Group();
  foundation.name = 'Island foundation';
  group.add(foundation);
  add(new THREE.CylinderGeometry(radius + 1.25, radius + 2.6, 1.5, 96), materials.warmStone, foundation, [0, -0.79, 0], true, 'Circular bedrock plinth');
  band(radius - 0.15, radius + 1.35, -0.035, materials.stone, foundation, 0, TAU, 0.22, true);
  band(radius + 1.15, radius + 1.36, -0.03, materials.lightStone, foundation, 0, TAU, 0.05);
  const sea = add(new THREE.PlaneGeometry(900, 900, 48, 48), materials.sea, group, [0, -1.18, 0], false, 'Sea');
  sea.rotation.x = -Math.PI / 2;
  sea.receiveShadow = false;
  sea.castShadow = false;
  const seaBase = sea.geometry.attributes.position.array.slice();

  const waterCourt = new THREE.Group();
  waterCourt.name = 'Water court trim';
  group.add(waterCourt);
  band(7.99, 8.15, 0.035, materials.lightStone, waterCourt, 0, TAU, 0.14);
  band(8.15, 8.20, 0.039, materials.bronze, waterCourt);
  let water = null;
  if (createWater) {
    water = add(new THREE.CircleGeometry(7 * MODULE.unit, 96), materials.water, waterCourt, [0, -0.045, 0], false, 'Water court surface');
    water.rotation.x = -Math.PI / 2;
    water.castShadow = false;
    const bottom = add(new THREE.CircleGeometry(7 * MODULE.unit, 64), materials.darkStone, waterCourt, [0, -0.34, 0]);
    bottom.rotation.x = -Math.PI / 2;
    for (let i = 0; i < 3; i += 1) {
      const ripple = band(1.3 + i * 0.91, 1.315 + i * 0.91, -0.039, materials.lightStone, waterCourt);
      ripple.material = new THREE.MeshBasicMaterial({color: 0xa5c7d5, transparent: true, opacity: 0.12, depthWrite: false});
      ripple.userData.ripplePhase = i * 1.8;
      ripple.castShadow = false;
    }
  }

  const colonnades = new THREE.Group();
  colonnades.name = 'Twelve-bay inner colonnade';
  group.add(colonnades);
  const shaftGeometry = flutedShaft(4.7, MODULE.columnDiameter / 2);
  const baseCubeGeometry = new THREE.BoxGeometry(0.95, 0.16, 0.95);
  const capitalCubeGeometry = new THREE.BoxGeometry(0.97, 0.16, 0.97);
  floorHeights.forEach((floor, level) => {
    const story = new THREE.Group();
    story.name = `Colonnade L${level}`;
    colonnades.add(story);
    for (let i = 0; i < 12; i += 1) {
      const a = (15 + 30 * i) * DEG;
      const x = Math.cos(a) * columnRadius;
      const z = Math.sin(a) * columnRadius;
      const column = new THREE.Group();
      column.name = `Column L${level} B${i}`;
      column.position.set(x, floor, z);
      column.rotation.y = -a;
      story.add(column);
      add(baseCubeGeometry, materials.stone, column, [0, 0.08, 0], true);
      add(new THREE.CylinderGeometry(0.46, 0.47, 0.13, 36), materials.lightStone, column, [0, 0.225, 0], true);
      add(new THREE.CylinderGeometry(0.37, 0.44, 0.15, 36), materials.lightStone, column, [0, 0.365, 0], true);
      add(shaftGeometry, materials.lightStone, column, [0, 0.44, 0], true, 'Fluted shaft');
      add(new THREE.CylinderGeometry(0.365, 0.335, 0.09, 36), materials.lightStone, column, [0, 5.185, 0], true);
      add(new THREE.CylinderGeometry(0.46, 0.355, 0.19, 36), materials.lightStone, column, [0, 5.325, 0], true);
      add(capitalCubeGeometry, materials.lightStone, column, [0, 5.50, 0], true);
      add(new THREE.BoxGeometry(0.99, 0.06, 0.99), materials.warmStone, column, [0, 5.61, 0]);
      obstacles.push({type: 'cylinder', x, z, radius: 0.49, bottom: floor, top: floor + 5.65, source: column.name});
    }
    // A true column-and-lintel colonnade: no unsupported arch springing from
    // the middle of a slender shaft. Large arches belong to the outer piers.
    band(10.19, 10.81, floor + 5.93, materials.stone, story, 0, TAU, 0.29, true);
    band(10.08, 10.92, floor + 5.96, materials.lightStone, story, 0, TAU, 0.075);
    band(10.14, 10.86, floor + 5.67, materials.warmStone, story, 0, TAU, 0.055);
    if (decorateFloors) {
      const inlays = new THREE.Group();
      inlays.name = `Floor inlays L${level} — hide with missing floor sectors`;
      group.add(inlays);
      floorDecorations.push(inlays);
      for (let bay = 0; bay < 12; bay += 1) {
        const a = bay * 30 * DEG + 2.5 * DEG;
        // Fine surface markings only; they intentionally cannot act as floors.
        band(11.38, 11.425, floor + 0.016, materials.bronze, inlays, a, 25 * DEG);
        band(14.22, 14.265, floor + 0.016, materials.bronze, inlays, a, 25 * DEG);
        const line = add(new THREE.BoxGeometry(2.68, 0.008, 0.038), materials.warmStone, inlays,
          [12.82 * Math.cos(a), floor + 0.013, 12.82 * Math.sin(a)]);
        line.rotation.y = -a;
      }
    }
  });

  const facade = new THREE.Group();
  facade.name = 'Outer facade piers — open bays';
  group.add(facade);
  const facadeSlotSpecs = [];
  function facadeCourse(inner,outer,y,material,floor,depth,solid,label){
    const width=facadeSlotFloors.includes(floor)?THREE.MathUtils.clamp(facadeSlotDegrees,0,24):0;
    if(width<=0){const course=band(inner,outer,y,material,facade,0,TAU,depth,solid);course.name=`${label} at ${floor+6}m`;return;}
    const course=new THREE.Group();course.name=`${label} · twelve clerestory slots at ${floor+6}m`;facade.add(course);
    for(let bay=0;bay<12;bay++)band(inner,outer,y,material,course,(bay*30+width/2)*DEG,(30-width)*DEG,depth,solid);
  }
  for (let bay = 0; bay < 12; bay += 1) {
    const a = (15 + 30 * bay) * DEG;
    const p = new THREE.Group();
    p.position.set(Math.cos(a) * (radius - 0.56), 0, Math.sin(a) * (radius - 0.56));
    p.rotation.y = -a;
    p.name = `Facade pier B${bay}`;
    facade.add(p);
    add(new THREE.BoxGeometry(0.94, 23.8, 1.14), materials.stone, p, [0, 11.9, 0], true);
    for (const floor of floorHeights) {
      add(new THREE.BoxGeometry(1.13, 0.35, 1.35), materials.lightStone, p, [0, floor + 0.175, 0], true);
      add(new THREE.BoxGeometry(1.15, 0.27, 1.38), materials.lightStone, p, [0, floor + 5.655, 0], true);
      const pilaster = add(new THREE.BoxGeometry(0.15, 4.84, 0.65), materials.lightStone, p, [0.525, floor + 2.875, 0]);
      pilaster.name = 'Outer pilaster face';
    }
    obstacles.push({type: 'orientedBox', x: p.position.x, z: p.position.z, halfX: 0.59, halfZ: 0.7, rotationY: -a, bottom: 0, top: 24, source: p.name});
  }
  for (const floor of floorHeights) {
    if(facadeSlotFloors.includes(floor)&&facadeSlotDegrees>0)facadeSlotSpecs.push({baseFloor:floor,boundaryHeight:floor+6,gapDegrees:facadeSlotDegrees,centersDegrees:Array.from({length:12},(_,i)=>i*30)});
    for (let bay = 0; bay < 12; bay += 1) {
      const a = (15 + 30 * bay) * DEG;
      const b = a + 30 * DEG;
      const r = radius - 0.56;
      const x = (Math.cos(a) + Math.cos(b)) * r / 2;
      const z = (Math.sin(a) + Math.sin(b)) * r / 2;
      const arch = add(ellipticalArch(4.35, 1.98, 0.26, 0.58), materials.stone, facade, [x, floor + 3.48, z], true, `Outer arch ${bay} at ${floor}m`);
      arch.rotation.y = -Math.atan2(Math.sin(b) - Math.sin(a), Math.cos(b) - Math.cos(a));
      const key = add(new THREE.BoxGeometry(0.3, 0.33, 0.68), materials.lightStone, facade, [x, floor + 5.535, z]);
      key.rotation.y = arch.rotation.y;
    }
    facadeCourse(radius-.92,radius+.05,floor+5.93,materials.stone,floor,.25,true,'Exterior cornice');
    facadeCourse(radius-1.02,radius+.13,floor+5.97,materials.lightStone,floor,.065,false,'Exterior cornice lip');
    facadeCourse(radius-.92,radius+.03,floor+5.64,materials.warmStone,floor,.045,false,'Exterior cornice lower moulding');
  }

  const niches = new THREE.Group();
  niches.name = 'Aedicule frames — no back walls';
  group.add(niches);
  // One restrained family of deep frames, away from the cardinal optical axes.
  const nicheSpecs = [];
  for (const floor of [6, 12]) {
    for (const degrees of [45, 135, 225, 315]) {
      const a = degrees * DEG;
      const niche = new THREE.Group();
      niche.position.set(Math.cos(a) * (radius - 1.52), floor, Math.sin(a) * (radius - 1.52));
      niche.rotation.y = -a + Math.PI / 2;
      niche.name = `Empty niche ${degrees} at ${floor}m`;
      niches.add(niche);
      for (const side of [-1, 1]) {
        add(new THREE.BoxGeometry(0.3, 3.05, 0.24), materials.lightStone, niche, [side * 1.18, 1.775, 0], true);
        add(new THREE.BoxGeometry(0.44, 0.18, 0.37), materials.stone, niche, [side * 1.18, 0.335, 0], true);
        add(new THREE.BoxGeometry(0.45, 0.16, 0.4), materials.stone, niche, [side * 1.18, 3.325, 0], true);
      }
      add(ellipticalArch(1.03, 0.87, 0.2, 0.3), materials.lightStone, niche, [0, 3.29, 0], true);
      add(new THREE.BoxGeometry(MODULE.nicheWidth, 0.16, 0.52), materials.lightStone, niche, [0, 4.44, 0]);
      nicheSpecs.push({angle: a, floor, radius: radius - 2.15, width: 1.96, name: niche.name});
    }
  }

  let seam = null;
  if (createSeam) {
    seam = new THREE.Group();
    seam.name = 'Full-height sculpted time seam';
    group.add(seam);
    add(new THREE.BoxGeometry(radius - 9, 23.75, 1.36), materials.stone, seam, [(radius + 9) / 2, 11.875, 0], true, 'Time seam core');
    add(new THREE.BoxGeometry(0.8, 23.87, 1.72), materials.lightStone, seam, [9.32, 11.935, 0], true, 'Atrium end pier');
    obstacles.push({type: 'box', minX: 8.92, maxX: radius + 0.1, minZ: -0.86, maxZ: 0.86, bottom: 0, top: 24, source: seam.name});
    const reliefPanelGeometry = new THREE.BoxGeometry(3.57, 4.65, 0.065);
    for (const sign of [-1, 1]) {
      for (const floor of floorHeights) {
        for (const x of [12, 16.15]) {
          add(reliefPanelGeometry, materials.relief, seam, [x, floor + 2.83, sign * 0.705]);
          for (const dx of [-1.85, 1.85]) add(new THREE.BoxGeometry(0.08, 4.89, 0.12), materials.lightStone, seam, [x + dx, floor + 2.83, sign * 0.725]);
          for (const dy of [0.39, 5.27]) add(new THREE.BoxGeometry(3.76, 0.09, 0.12), materials.lightStone, seam, [x, floor + dy, sign * 0.725]);
          const emblem = new THREE.Group();
          emblem.position.set(x, floor + 3.1, sign * 0.778);
          if (sign < 0) emblem.rotation.y = Math.PI;
          seam.add(emblem);
          const halo = add(new THREE.TorusGeometry(0.66, 0.036, 6, 48), materials.lightStone, emblem);
          halo.scale.y = 1.07;
          for (let ray = 0; ray < 12; ray += 1) {
            const a = ray / 12 * TAU;
            const petal = add(new THREE.SphereGeometry(1, 10, 8), materials.lightStone, emblem, [Math.cos(a) * 0.88, Math.sin(a) * 0.88, 0]);
            petal.scale.set(0.064, 0.2, 0.036);
            petal.rotation.z = a - Math.PI / 2;
          }
          const disc = add(new THREE.CircleGeometry(0.49, 40), sign > 0 ? materials.warmStone : materials.darkStone, emblem, [0, 0, 0.003]);
          disc.castShadow = false;
          // Long shallow drapery-like lines continue the vertical relief order.
          for (const dx of [-0.7, -0.35, 0, 0.35, 0.7]) {
            tube(new THREE.QuadraticBezierCurve3(new THREE.Vector3(x + dx * 0.43, floor + 2.44, sign * 0.797), new THREE.Vector3(x + dx * 0.72, floor + 1.8, sign * 0.81), new THREE.Vector3(x + dx, floor + 0.83, sign * 0.79)), 0.022, materials.lightStone, seam);
          }
        }
      }
    }
  }

  const roof = new THREE.Group();
  roof.name = 'Retracting iris — below fixed roof walks';
  group.add(roof);
  const irisLeaves = [];
  // Rigid two-part petals. Inner panels fold down, then the folded assemblies
  // retract radially beneath the perimeter. No topology morph or scaling is used.
  const outerPetalGeometry = annularSector(10, 15.5, -15.25 * DEG, 30.5 * DEG, 16, 0.075);
  const innerPetalGeometry = annularSector(4.5, 10, -15.25 * DEG, 30.5 * DEG, 16, 0.065);
  innerPetalGeometry.translate(-10, 0, 0);
  const seamNearX = 8.92;
  const seamHalfWidth = 0.86;
  const seamSlotClearance = 0.055;
  // For the +15° petal, local Z = -sin(15°)*world X + cos(15°)*world Z.
  // The complete seam lies BELOW this bound. Folding and radial retraction
  // never change local Z, so a single cut separates both panels for all states.
  const seamSlotZ = -Math.sin(15 * DEG) * seamNearX
    + Math.cos(15 * DEG) * seamHalfWidth + seamSlotClearance;
  for (let i = 0; i < 12; i += 1) {
    const a = (15 + 30 * i) * DEG;
    const radialRoot = new THREE.Group();
    radialRoot.rotation.y = -a;
    radialRoot.position.y = 23.1 - (i % 2) * 0.008;
    radialRoot.name = `Iris petal ${i}`;
    roof.add(radialRoot);
    const carriage = new THREE.Group();
    radialRoot.add(carriage);
    const minimumZ = i === 0 ? seamSlotZ : -Infinity;
    const maximumZ = i === 11 ? -seamSlotZ : Infinity;
    const besideSeam = i === 0 || i === 11;
    const outerGeometry = besideSeam
      ? slottedPetal(10, 15.5, minimumZ, maximumZ, 0.075)
      : outerPetalGeometry;
    const innerGeometry = besideSeam
      ? slottedPetal(4.5, 10, minimumZ, maximumZ, 0.065)
      : innerPetalGeometry;
    if (besideSeam) innerGeometry.translate(-10, 0, 0);
    const outer = add(outerGeometry, materials.iris, carriage, [0, 0, 0], true);
    const hinge = new THREE.Group();
    hinge.position.x = 10;
    carriage.add(hinge);
    const inner = add(innerGeometry, materials.iris, hinge, [0, -0.085, 0], true);
    const pinMinimum = Math.max(-2.58, minimumZ + 0.025);
    const pinMaximum = Math.min(2.58, maximumZ - 0.025);
    const hingePin = add(new THREE.CylinderGeometry(0.06, 0.06, pinMaximum - pinMinimum, 12), materials.bronze, carriage, [10, -0.052, (pinMinimum + pinMaximum) / 2]);
    hingePin.rotation.x = Math.PI / 2;
    // Thin ribs reveal that this is an articulated architectural roof.
    const rib = add(new THREE.BoxGeometry(5.48, 0.026, 0.035), materials.bronze, carriage, [12.74, 0.017, 0]);
    rib.castShadow = false;
    irisLeaves.push({radialRoot, carriage, hinge, outer, inner, hingePin,
      seamSlot: besideSeam ? {minimumZ, maximumZ, clearance: seamSlotClearance} : null});
  }
  band(15.52, 15.81, 23.15, materials.bronze, roof, 0, TAU, 0.13);
  // These are light trim, never collision surfaces. Root owns all fixed roof
  // landings/bridges so their exact optical apertures match the gameplay model.
  const observationSpecs = {
    y: roofY, innerRadius: 4.5, outerRadius: 6,
    bridgeAngle: roofAngle, bridgeCount: 1,
    bridgeWidth: 2.25, bridgeStartRadius: 5.72, bridgeEndRadius: 14.45,
    initialSolarAltitude: 20 * DEG,
    warning: 'Keep the solar approach sector open; no solid disk over the central aperture.',
  };

  // Keep sculpted detail affordable without replacing real occluders with
  // invisible shortcuts. Merge within each column/pier, so raycasts retain
  // tight per-member bounds, and batch purely decorative relief/inlay meshes.
  const retiredOccluders = new Set();
  function batchWithin(parent, recursive = false, decorationsOnly = false) {
    parent.updateWorldMatrix(true, true);
    const inverse = parent.matrixWorld.clone().invert();
    const buckets = new Map();
    const candidates = [];
    if (recursive) parent.traverse(object => { if (object.isMesh) candidates.push(object); });
    else parent.children.forEach(object => { if (object.isMesh) candidates.push(object); });
    for (const object of candidates) {
      if (Array.isArray(object.material) || (decorationsOnly && object.userData.opticalOccluder)) continue;
      const key = `${object.material.uuid}|${Boolean(object.userData.opticalOccluder)}|${object.castShadow}|${object.receiveShadow}`;
      if (!buckets.has(key)) buckets.set(key, []);
      buckets.get(key).push(object);
    }
    for (const objects of buckets.values()) {
      if (objects.length < 2) continue;
      const chunks = [];
      let count = 0;
      for (const object of objects) {
        const geometry = object.geometry.index ? object.geometry.toNonIndexed() : object.geometry.clone();
        geometry.applyMatrix4(inverse.clone().multiply(object.matrixWorld));
        chunks.push(geometry);
        count += geometry.attributes.position.count;
      }
      const position = new Float32Array(count * 3);
      const normal = new Float32Array(count * 3);
      const uv = new Float32Array(count * 2);
      let cursor = 0;
      for (const chunk of chunks) {
        position.set(chunk.attributes.position.array, cursor * 3);
        if (chunk.attributes.normal) normal.set(chunk.attributes.normal.array, cursor * 3);
        if (chunk.attributes.uv) uv.set(chunk.attributes.uv.array, cursor * 2);
        cursor += chunk.attributes.position.count;
        chunk.dispose();
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(position, 3));
      geometry.setAttribute('normal', new THREE.BufferAttribute(normal, 3));
      geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
      geometry.computeBoundingBox();
      geometry.computeBoundingSphere();
      const reference = objects[0];
      const combined = add(geometry, reference.material, parent, [0, 0, 0], Boolean(reference.userData.opticalOccluder), `${parent.name} · stonework`);
      combined.castShadow = reference.castShadow;
      combined.receiveShadow = reference.receiveShadow;
      for (const object of objects) {
        if (object.userData.opticalOccluder) retiredOccluders.add(object);
        object.removeFromParent();
      }
    }
  }
  colonnades.children.forEach(story => {
    story.children.filter(object => object.isGroup).forEach(column => batchWithin(column));
    batchWithin(story, false, true);
  });
  facade.children.filter(object => object.isGroup).forEach(pier => batchWithin(pier));
  batchWithin(facade, false, true);
  niches.children.forEach(niche => batchWithin(niche));
  floorDecorations.forEach(inlays => batchWithin(inlays));
  if (seam) batchWithin(seam, true, true);
  if (retiredOccluders.size) {
    const active = occluders.filter(object => !retiredOccluders.has(object));
    occluders.splice(0, occluders.length, ...active);
  }

  let lastSeaTime = -1;
  let disposed = false;
  function update(time = 0, night = false, irisOpen = 0) {
    if (disposed) return;
    const openness = THREE.MathUtils.clamp(irisOpen, 0, 1);
    for (const leaf of irisLeaves) {
      leaf.hinge.rotation.z = smoothstep(0, 0.66, openness) * Math.PI;
      leaf.carriage.position.x = smoothstep(0.4, 1, openness) * 4;
    }
    // Keep environment motion restrained; puzzle light is the visual priority.
    if (time - lastSeaTime > 0.09 || time < lastSeaTime) {
      const positions = sea.geometry.attributes.position;
      for (let i = 0; i < positions.count; i += 1) {
        const x = seaBase[i * 3];
        const z = seaBase[i * 3 + 1];
        positions.setZ(i, Math.sin(x * 0.028 + time * 0.17) * 0.09 + Math.cos(z * 0.036 - time * 0.13) * 0.06);
      }
      positions.needsUpdate = true;
      sea.geometry.computeVertexNormals();
      lastSeaTime = time;
    }
    if (water) {
      materials.water.color.setHex(night ? 0x294e68 : 0x729aab);
      waterCourt.children.forEach(child => {
        if (child.userData.ripplePhase !== undefined) {
          const t = time * 0.24 + child.userData.ripplePhase;
          child.material.opacity = (night ? 0.06 : 0.09) + Math.sin(t) * 0.025;
          const s = 1 + Math.sin(t * 0.67) * 0.025;
          child.scale.set(s, 1, s);
        }
      });
    }
    materials.sea.color.setHex(night ? 0x182e46 : 0x426e83);
  }

  function dispose() {
    disposed = true;
    group.removeFromParent();
    disposableGeometries.forEach(geometry => geometry.dispose());
    const textures = new Set();
    const allMaterials = new Set(Object.values(materials));
    group.traverse(object => {
      if (object.isMesh && object.material) {
        for (const material of Array.isArray(object.material) ? object.material : [object.material]) allMaterials.add(material);
      }
    });
    allMaterials.forEach(material => {
      if (material.map) textures.add(material.map);
      material.dispose();
    });
    textures.forEach(texture => texture.dispose());
  }

  update(0, false, 0);
  return {
    group, occluders, obstacles, update, dispose, materials,
    proportions: {...ROTUNDA_PROPORTIONS, diameter: radius * 2},
    floorDecorations, colonnades, facade, facadeSlotSpecs, niches, nicheSpecs, seam,
    roof, irisLeaves, observationSpecs, waterCourt, water, sea,
  };
}
