import * as THREE from '../vendor/three.module.js';

// Original procedural study models. The goddess and swan deliberately have
// different silhouettes; their final sculpted replacements can share these pivots.
const palette = {
  stone: 0xe6dfd0,
  bronze: 0xa58146,
  dark: 0x263442,
};

function stoneMaterial(material) {
  return material || new THREE.MeshStandardMaterial({
    color: palette.stone, roughness: 0.73, metalness: 0.025,
  });
}

function metalMaterial(color = palette.bronze, roughness = 0.32) {
  return new THREE.MeshStandardMaterial({color, roughness, metalness: 0.8});
}

function mesh(geometry, material, parent, x = 0, y = 0, z = 0) {
  const object = new THREE.Mesh(geometry, material);
  object.position.set(x, y, z);
  object.castShadow = true;
  object.receiveShadow = true;
  if (parent) parent.add(object);
  return object;
}

function sphere(parent, material, position, scale, width = 20, height = 14) {
  const object = mesh(new THREE.SphereGeometry(1, width, height), material, parent, ...position);
  object.scale.set(...scale);
  return object;
}

function limb(parent, material, from, to, r0, r1 = r0) {
  const a = new THREE.Vector3(...from);
  const b = new THREE.Vector3(...to);
  const d = b.clone().sub(a);
  const object = mesh(new THREE.CylinderGeometry(r1, r0, d.length(), 12), material, parent);
  object.position.copy(a).add(b).multiplyScalar(0.5);
  object.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
  return object;
}

function plinth(parent, material, radius = 0.87) {
  mesh(new THREE.CylinderGeometry(radius, radius + 0.08, 0.12, 48), material, parent, 0, 0.06, 0);
  mesh(new THREE.CylinderGeometry(radius - 0.06, radius - 0.01, 0.15, 48), material, parent, 0, 0.19, 0);
  mesh(new THREE.CylinderGeometry(radius, radius, 0.055, 48), material, parent, 0, 0.292, 0);
}

function drapedRobe(height = 2.6, bottomRadius = 0.75, topRadius = 0.31) {
  const segments = 72;
  const rings = 22;
  const vertices = [];
  const uvs = [];
  const indices = [];
  for (let j = 0; j <= rings; j += 1) {
    const t = j / rings;
    const skirt = Math.pow(1 - t, 1.55);
    const radius = topRadius + (bottomRadius - topRadius) * skirt;
    const waist = 0.055 * Math.exp(-Math.pow((t - 0.71) / 0.13, 2));
    for (let i = 0; i <= segments; i += 1) {
      const a = i / segments * Math.PI * 2;
      const fold = (0.025 + 0.045 * (1 - t)) * Math.cos(a * 13 + t * 1.1)
        + 0.018 * Math.sin(a * 6 - t * 1.9);
      const r = radius - waist + fold;
      vertices.push(Math.cos(a) * r, t * height, Math.sin(a) * r * 0.71);
      uvs.push(i / segments, t);
      if (i < segments && j < rings) {
        const k = j * (segments + 1) + i;
        indices.push(k, k + segments + 1, k + 1, k + 1, k + segments + 1, k + segments + 2);
      }
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function createHead(parent, material, y = 3.28) {
  sphere(parent, material, [0, y, 0.02], [0.25, 0.33, 0.235], 24, 18);
  // A quiet, closed-eye face, intended to read as a carved figure at game distance.
  const nose = mesh(new THREE.ConeGeometry(0.065, 0.16, 5), material, parent, 0, y - 0.015, 0.235);
  nose.rotation.x = Math.PI / 2;
  sphere(parent, material, [0, y - 0.135, 0.204], [0.083, 0.026, 0.034], 12, 8);
  const hair = sphere(parent, material, [0, y + 0.067, -0.055], [0.272, 0.298, 0.242], 24, 16);
  hair.name = 'Carved hair';
  for (let i = 0; i < 7; i += 1) {
    const a = -1.17 + i * 0.39;
    sphere(parent, material, [Math.sin(a) * 0.219, y + 0.19, Math.cos(a) * 0.2 - 0.055], [0.061, 0.078, 0.046], 10, 8);
  }
  sphere(parent, material, [0, y + 0.02, -0.27], [0.13, 0.135, 0.11], 14, 10);
  const lidMaterial = new THREE.MeshStandardMaterial({color: 0xb8af9d, roughness: 0.9});
  for (const sign of [-1, 1]) {
    const eye = mesh(new THREE.TubeGeometry(new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(sign * 0.035, y + 0.014, 0.23),
      new THREE.Vector3(sign * 0.106, y - 0.009, 0.228),
      new THREE.Vector3(sign * 0.166, y + 0.004, 0.205),
    ), 10, 0.007, 5, false), lidMaterial, parent);
    eye.castShadow = false;
  }
}

export function createGoddess(material, {arms = true} = {}) {
  const group = new THREE.Group();
  group.name = 'Dysis · daylight goddess';
  const stone = stoneMaterial(material);
  const bronze = metalMaterial(0x9f824e, 0.49);
  plinth(group, stone, 0.88);
  mesh(drapedRobe(2.49, 0.76, 0.36), stone, group, 0, 0.32, 0);
  sphere(group, stone, [0, 2.87, 0], [0.44, 0.33, 0.27]);
  limb(group, stone, [0, 2.94, 0], [0, 3.11, 0], 0.135, 0.12);
  createHead(group, stone, 3.36);

  // One hand rests over the heart, one opens calmly beside the robe.
  if (arms) {
    limb(group, stone, [-0.39, 2.97, 0], [-0.63, 2.54, 0.04], 0.155, 0.12);
    sphere(group, stone, [-0.63, 2.54, 0.04], [0.125, 0.13, 0.125]);
    limb(group, stone, [-0.63, 2.54, 0.04], [-0.76, 2.19, 0.19], 0.11, 0.085);
    sphere(group, stone, [-0.775, 2.14, 0.22], [0.105, 0.135, 0.071]);
    limb(group, stone, [0.39, 2.97, 0], [0.59, 2.62, 0.19], 0.155, 0.105);
    sphere(group, stone, [0.59, 2.62, 0.19], [0.11, 0.12, 0.11]);
    limb(group, stone, [0.59, 2.62, 0.19], [0.12, 2.71, 0.35], 0.1, 0.073);
    sphere(group, stone, [0.055, 2.73, 0.351], [0.15, 0.065, 0.05]);
  }

  const belt = mesh(new THREE.TorusGeometry(0.357, 0.022, 8, 48), bronze, group, 0, 2.24, 0);
  belt.rotation.x = Math.PI / 2;
  belt.scale.y = 0.72;
  const circlet = mesh(new THREE.TorusGeometry(0.247, 0.015, 6, 40), bronze, group, 0, 3.54, -0.005);
  circlet.rotation.x = Math.PI / 2;
  sphere(group, bronze, [0, 3.6, 0.206], [0.043, 0.07, 0.025], 10, 8);
  group.userData.kind = 'goddess';
  group.userData.height = 3.72;
  group.userData.profileFront = new THREE.Vector3(0, 0, 1);
  return group;
}

function taperedTube(curve, radii, segments = 52, radialSegments = 14) {
  const frames = curve.computeFrenetFrames(segments, false);
  const positions = [];
  const uv = [];
  const index = [];
  for (let j = 0; j <= segments; j += 1) {
    const t = j / segments;
    const p = curve.getPointAt(t);
    const radius = radii(t);
    for (let i = 0; i <= radialSegments; i += 1) {
      const a = i / radialSegments * Math.PI * 2;
      const v = p.clone().addScaledVector(frames.normals[j], radius * Math.cos(a))
        .addScaledVector(frames.binormals[j], radius * Math.sin(a));
      positions.push(v.x, v.y, v.z);
      uv.push(i / radialSegments, t);
      if (j < segments && i < radialSegments) {
        const k = j * (radialSegments + 1) + i;
        index.push(k, k + 1, k + radialSegments + 1, k + 1, k + radialSegments + 2, k + radialSegments + 1);
      }
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geometry.setIndex(index);
  geometry.computeVertexNormals();
  return geometry;
}

function swanWing(side, material) {
  const shape = new THREE.Shape();
  shape.moveTo(-1.18, 0.67);
  shape.bezierCurveTo(-1.07, 1.26, -0.9, 1.79, -0.52, 1.73);
  shape.bezierCurveTo(-0.32, 1.68, -0.46, 1.41, -0.23, 1.45);
  shape.bezierCurveTo(0.18, 1.43, 0.63, 1.01, 0.48, 0.77);
  shape.bezierCurveTo(0.05, 0.51, -0.57, 0.43, -1.18, 0.67);
  const geometry = new THREE.ExtrudeGeometry(shape, {depth: 0.07, bevelEnabled: true, bevelSegments: 2, steps: 1, bevelSize: 0.027, bevelThickness: 0.028, curveSegments: 14});
  const group = new THREE.Group();
  const wing = mesh(geometry, material, group, 0, 0.05, side * 0.43);
  if (side < 0) wing.scale.z = -1;
  for (let i = 0; i < 7; i += 1) {
    const t = i / 6;
    const feather = sphere(group, material,
      [-0.87 + t * 0.94, 1.04 + Math.sin(t * Math.PI) * 0.18, side * (0.53 + Math.sin(t * Math.PI) * 0.025)],
      [0.105, 0.38 - t * 0.15, 0.045], 12, 10);
    feather.rotation.z = -0.42 - t * 0.9;
  }
  return group;
}

export function createSwan(material) {
  const group = new THREE.Group();
  group.name = 'Dysis · moonlit swan';
  const stone = stoneMaterial(material);
  const bronze = metalMaterial(0xad8c4d, 0.38);
  const eye = new THREE.MeshStandardMaterial({color: 0x233444, roughness: 0.38, metalness: 0.12});
  plinth(group, stone, 0.88);
  sphere(group, stone, [-0.26, 0.98, 0], [1.06, 0.59, 0.53], 28, 20);
  sphere(group, stone, [0.43, 1.04, 0], [0.43, 0.52, 0.4], 22, 18);
  const neck = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.43, 1.04, 0),
    new THREE.Vector3(0.81, 1.44, 0),
    new THREE.Vector3(0.66, 1.88, 0),
    new THREE.Vector3(0.61, 2.26, 0),
    new THREE.Vector3(0.88, 2.53, 0),
    new THREE.Vector3(1.21, 2.56, 0),
  ]);
  mesh(taperedTube(neck, t => 0.225 - 0.11 * Math.sin(t * Math.PI / 2)), stone, group);
  sphere(group, stone, [1.21, 2.56, 0], [0.255, 0.212, 0.205], 24, 16);
  const beak = mesh(new THREE.ConeGeometry(0.128, 0.43, 4), bronze, group, 1.58, 2.495, 0);
  beak.rotation.z = -Math.PI / 2;
  beak.scale.z = 0.55;
  for (const side of [-1, 1]) {
    sphere(group, eye, [1.28, 2.621, side * 0.174], [0.029, 0.033, 0.02], 10, 8);
    group.add(swanWing(side, stone));
  }
  for (let i = 0; i < 5; i += 1) {
    const feather = sphere(group, stone, [-1.26, 1.06 + i * 0.035, (i - 2) * 0.085], [0.48, 0.105, 0.095], 16, 10);
    feather.rotation.z = -0.15 - 0.045 * i;
  }
  group.userData.kind = 'swan';
  group.userData.height = 2.78;
  group.userData.profileDirection = new THREE.Vector3(1, 0, 0);
  group.userData.silhouettePlaneNormal = new THREE.Vector3(0, 0, 1);
  return group;
}

export function createMirrorStatue(material) {
  const group = new THREE.Group();
  group.name = 'Dysis · mirror bearer';
  const stone = stoneMaterial(material);
  const bronze = metalMaterial(0xb69a5e, 0.27);
  const body = createGoddess(stone, {arms: false});
  body.position.z = -0.55;
  body.scale.setScalar(1.2);
  group.add(body);
  const assembly = new THREE.Group();
  assembly.name = 'Mirror and bronze frame · pitch together';
  assembly.position.set(0, 2.5, 0.24);
  group.add(assembly);
  // The optical disk has its geometry normal along local +Z, with no local
  // rotation; world normal = local +Z transformed by matrixWorld.
  const mirror = mesh(new THREE.CircleGeometry(1.3, 64), new THREE.MeshPhysicalMaterial({
    color: 0xcbdfe5, metalness: 0.96, roughness: 0.07, clearcoat: 1,
    clearcoatRoughness: 0.035, side: THREE.DoubleSide,
  }), assembly);
  mirror.name = 'Optical mirror disk';
  const diskBackGeometry = new THREE.CylinderGeometry(1.315, 1.315, 0.065, 64);
  diskBackGeometry.rotateX(Math.PI / 2);
  mesh(diskBackGeometry, bronze, assembly, 0, 0, -0.044);
  mesh(new THREE.TorusGeometry(1.322, 0.045, 10, 72), bronze, assembly);
  mesh(new THREE.TorusGeometry(1.25, 0.012, 6, 72), bronze, assembly, 0, 0, 0.008);
  for (const side of [-1, 1]) {
    limb(group, stone, [side * 0.47, 3.57, -0.53], [side * 1.14, 3.16, -0.18], 0.16, 0.12);
    sphere(group, stone, [side * 1.14, 3.16, -0.18], [0.12, 0.13, 0.12]);
    limb(group, stone, [side * 1.14, 3.16, -0.18], [side * 1.06, 1.77, 0.12], 0.12, 0.083);
    sphere(group, stone, [side * 1.06, 1.72, 0.16], [0.14, 0.10, 0.085]);
  }
  for (let i = 0; i < 24; i += 1) {
    const a = i / 24 * Math.PI * 2;
    const rivet = sphere(assembly, bronze, [Math.cos(a) * 1.321, Math.sin(a) * 1.321, 0.04], [0.023, 0.023, 0.018], 8, 6);
    rivet.castShadow = false;
  }
  group.userData.kind = 'mirror';
  group.userData.mirrorDisk = mirror;
  group.userData.mirrorAssembly = assembly;
  group.userData.mirrorLocalCenter = new THREE.Vector3(0, 2.5, 0.24);
  group.userData.mirrorLocalNormal = new THREE.Vector3(0, 0, 1);
  group.userData.mirrorRadius = 1.3;
  return group;
}

export function createArmillary(options = {}) {
  const group = new THREE.Group();
  group.name = 'Dysis · celestial armillary';
  const stone = stoneMaterial(options.material);
  const bronze = metalMaterial(0xb89451, 0.27);
  const darkerBronze = metalMaterial(0x806642, 0.4);
  const silver = metalMaterial(0xbdced9, 0.22);
  plinth(group, stone, 0.96);
  const pedestalProfile = [
    new THREE.Vector2(0.67, 0.31), new THREE.Vector2(0.64, 0.4),
    new THREE.Vector2(0.4, 0.47), new THREE.Vector2(0.29, 0.84),
    new THREE.Vector2(0.39, 0.94), new THREE.Vector2(0.41, 1.05),
  ];
  mesh(new THREE.LatheGeometry(pedestalProfile, 48), stone, group);
  const instrument = new THREE.Group();
  instrument.position.y = 2.07;
  group.add(instrument);
  const rings = [
    {r: 1.29, rx: 0, ry: 0, rz: 0, w: 0.036},
    {r: 1.17, rx: Math.PI / 2, ry: 0, rz: 0, w: 0.03},
    {r: 1.08, rx: 0.58, ry: 0.63, rz: 0, w: 0.024},
    {r: 0.96, rx: -0.81, ry: -0.43, rz: 0.21, w: 0.022},
  ];
  rings.forEach((r, i) => {
    const ring = mesh(new THREE.TorusGeometry(r.r, r.w, 9, 100), i === 0 ? darkerBronze : bronze, instrument);
    ring.rotation.set(r.rx, r.ry, r.rz);
  });
  const equator = mesh(new THREE.TorusGeometry(1.2, 0.07, 4, 96), bronze, instrument);
  equator.rotation.x = Math.PI / 2;
  equator.scale.z = 0.7;
  for (let i = 0; i < 24; i += 1) {
    const a = i / 24 * Math.PI * 2;
    const tick = mesh(new THREE.BoxGeometry(0.025, 0.05, i % 3 === 0 ? 0.14 : 0.07), darkerBronze, instrument, Math.cos(a) * 1.2, 0.04, Math.sin(a) * 1.2);
    tick.rotation.y = -a + Math.PI / 2;
  }
  limb(instrument, bronze, [0, -1.36, 0], [0, 1.4, 0], 0.025);
  sphere(instrument, bronze, [0, 1.43, 0], [0.07, 0.07, 0.07], 12, 8);

  const cradle = new THREE.Group();
  cradle.name = 'Empty moon cradle';
  cradle.position.set(0, 1.99, 0);
  group.add(cradle);
  const cup = mesh(new THREE.TorusGeometry(0.295, 0.027, 8, 36), bronze, cradle, 0, -0.08, 0);
  cup.rotation.x = Math.PI / 2;
  for (let i = 0; i < 3; i += 1) {
    const a = i / 3 * Math.PI * 2;
    const arm = new THREE.QuadraticBezierCurve3(
      new THREE.Vector3(Math.cos(a) * 0.06, -0.4, Math.sin(a) * 0.06),
      new THREE.Vector3(Math.cos(a) * 0.33, -0.24, Math.sin(a) * 0.33),
      new THREE.Vector3(Math.cos(a) * 0.285, 0, Math.sin(a) * 0.285),
    );
    mesh(new THREE.TubeGeometry(arm, 14, 0.022, 6, false), bronze, cradle);
  }
  const apple = new THREE.Group();
  apple.name = 'Golden apple';
  apple.position.set(0, 2.15, 0);
  group.add(apple);
  const gold = new THREE.MeshStandardMaterial({color: 0xeeb54f, metalness: 0.68, roughness: 0.22, emissive: 0xa85411, emissiveIntensity: 0.2});
  sphere(apple, gold, [-0.071, 0, 0], [0.225, 0.259, 0.239], 24, 18);
  sphere(apple, gold, [0.071, 0, 0], [0.225, 0.259, 0.239], 24, 18);
  const stem = limb(apple, darkerBronze, [0, 0.21, 0], [0.06, 0.36, 0], 0.017, 0.011);
  stem.name = 'Apple stem';
  const leaf = sphere(apple, bronze, [0.13, 0.313, 0], [0.11, 0.026, 0.041], 12, 8);
  leaf.rotation.z = 0.35;
  apple.visible = options.apple !== false;
  const moonBead = sphere(instrument, silver, [0.94, 0.45, 0.3], [0.135, 0.135, 0.135], 20, 14);
  group.userData.apple = apple;
  group.userData.cradle = cradle;
  group.userData.instrument = instrument;
  group.userData.moonBead = moonBead;
  group.userData.kind = 'armillary';
  return group;
}
