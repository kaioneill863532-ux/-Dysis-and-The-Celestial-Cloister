import test from 'node:test';
import assert from 'node:assert/strict';
import { DEG, polar, sunDirection, moonDirection, scale, reflect, rayPlane, segmentDistanceXZ, add, sub, dot, normalize } from '../prototype/rotunda/core/math.js';
import {
  WORLD, DAY_RAMPS, ROOF_PHASE, NIGHT_REFLECTION, sampleRamp, rampStats,
  phaseAtPosition, clipRayIntervals, solarBeamCells,
} from '../prototype/rotunda/core/layout.js';

test('all authored day paths remain within the moving 2.8m strip without horizontal carry', () => {
  for (const ramp of DAY_RAMPS) {
    const samples = sampleRamp(ramp, 201);
    for (const sample of samples) {
      assert.ok(sample.t >= -1e-9, `${ramp.id}: support is on the forward ray`);
      assert.ok(sample.lateralError + 0.35 < ramp.width / 2, `${ramp.id}: character fits the light strip`);
      assert.ok(Number.isFinite(sample.supportY));
    }
    assert.ok(Math.abs(samples[0].supportY - ramp.foot[1]) < 1e-7, `${ramp.id}: foot joins its stone landing`);
    assert.ok(Math.abs(samples.at(-1).supportY - ramp.top[1]) < 1e-7, `${ramp.id}: top joins its stone landing`);
    assert.ok(rampStats(ramp).maxSlopeDegrees < 35, `${ramp.id}: walkable gradient`);
  }
});

test('day centre paths clear the column cylinders, while the offset roof strip clears in full width', () => {
  for (const ramp of DAY_RAMPS) {
    const clearance = rampStats(ramp).minColumnAxisDistance;
    assert.ok(clearance > WORLD.columnRadius + 0.35 + 0.1, `${ramp.id}: centre path clears columns`);
  }
  const roof = DAY_RAMPS.find((ramp) => ramp.id === 'roof');
  assert.ok(rampStats(roof).minColumnAxisDistance > WORLD.columnRadius + roof.width / 2 + 0.2);
  const source = sunDirection(ROOF_PHASE);
  const leafPoint = rayPlane(roof.top, scale(source, -1), [0, WORLD.irisY, 0], [0, 1, 0]).point;
  assert.ok(Math.hypot(leafPoint[0], leafPoint[2]) < WORLD.oculusRadius);
  assert.ok(Math.abs(Math.hypot(roof.top[0], roof.top[2]) - WORLD.oculusRadius) < 1e-8);
});

test('the changing day phase stays continuous along each path; the roof connection stays constant', () => {
  for (const ramp of DAY_RAMPS) {
    const samples = sampleRamp(ramp, 201);
    for (let index = 1; index < samples.length; index += 1) {
      assert.ok(Math.abs(samples[index].phase - samples[index - 1].phase) < 0.1);
    }
    if (ramp.id === 'roof') assert.ok(samples.every((sample) => sample.phase === ROOF_PHASE));
    else assert.ok(Math.abs(samples.at(-1).phase - samples[0].phase) > 0.1);
  }
});

test('the revised moon mirror reaches the high entrance crown before a column or seam', () => {
  const cfg = NIGHT_REFLECTION;
  const initial = reflect(scale(moonDirection(cfg.initialPhase), -1), cfg.mirrorNormal);
  assert.ok(Math.abs(initial[1]) < 1e-10);
  const inward = normalize([-cfg.mirror[0],0,-cfg.mirror[2]]);
  assert.ok(dot(initial,inward)>1-1e-10);
  assert.ok(cfg.revealDirection[1] < 0);
  assert.ok(Math.abs(cfg.target[1] - (6+4*1.13)) < 1e-10);
  const radius = Math.hypot(cfg.target[0], cfg.target[2]);
  assert.ok(radius > 10.5 && radius < WORLD.ringRadii[0]);
  const minDistance = Math.min(...WORLD.columns.map((column) =>
    segmentDistanceXZ(column, cfg.mirror, cfg.target).distance));
  assert.ok(minDistance > .49 + cfg.maxBeamHalfWidth);
  const floorPass = rayPlane(cfg.mirror, cfg.revealDirection, [0, 12, 0], [0, 1, 0]);
  assert.ok(floorPass, 'the L2 slab must include an actual light well at this crossing');
  assert.ok(Math.abs(floorPass.point[0] - 8.52733128673989)<1e-8);
  assert.ok(Math.abs(floorPass.point[2] + 9.763182010462254)<1e-8);
  assert.ok(cfg.target[2]<-.86-cfg.maxBeamHalfWidth);
});

test('adjacent day fields agree at the actual stone landings with no catch-up clock', () => {
  for (let index = 0; index < 3; index += 1) {
    const landing = DAY_RAMPS[index].top;
    assert.ok(Math.abs(phaseAtPosition(index, landing) - phaseAtPosition(index + 1, landing)) < 1e-9);
  }
  assert.ok(Math.abs(phaseAtPosition(3, DAY_RAMPS[3].foot) - ROOF_PHASE) < 1e-9);
  assert.ok(Math.abs(phaseAtPosition(1, DAY_RAMPS[1].top) - 12.847412542043745) < 1e-9);
  assert.ok(Math.abs(phaseAtPosition(2, DAY_RAMPS[2].foot) - 29.31849482121147) < 1e-9);
});

test('finite cylinder clipping handles the side, caps, tangency, height misses and inside origins', () => {
  const column = { type: 'cylinder', x: 5, z: 0, radius: 1, bottom: 0, top: 4 };
  const blocked = clipRayIntervals([0, 2, 0], [4, 0, 0], 10, [column]);
  assert.deepEqual(blocked, [{ start: 0, end: 4 }]);
  assert.deepEqual(clipRayIntervals([0, 5, 0], [1, 0, 0], 10, [column]), [{ start: 0, end: 10 }]);
  assert.deepEqual(clipRayIntervals([0, -1, 0], [1, 0, 0], 10, [column]), [{ start: 0, end: 10 }]);
  assert.deepEqual(clipRayIntervals([5, 6, 0], [0, -1, 0], 10, [column]), [{ start: 0, end: 2 }]);
  assert.deepEqual(clipRayIntervals([5, -3, 0], [0, 1, 0], 10, [column]), [{ start: 0, end: 3 }]);
  assert.deepEqual(clipRayIntervals([0, 2, 1], [1, 0, 0], 10, [column]), [{ start: 0, end: 5 }]);
  assert.deepEqual(clipRayIntervals([5, 2, 0], [1, 0, 0], 10, [column]), []);
  assert.deepEqual(clipRayIntervals([0, 2, 0], [0, 0, 0], 10, [column]), []);
  assert.deepEqual(clipRayIntervals([0, 2, 0], [-1, 0, 0], 10, [column]), [{ start: 0, end: 10 }]);
  const second = { ...column, x: 8 };
  assert.deepEqual(clipRayIntervals([0, 2, 0], [1, 0, 0], 10, [second, column]),
    [{ start: 0, end: 4 }], 'light stays blocked behind the first column');
});

test('every rendered narrow cell stays outside a column, including its lateral edges', () => {
  const column = { type: 'cylinder', x: 5, z: 0, radius: 0.5, bottom: 0, top: 4 };
  const cells = solarBeamCells([0, 2, 0], [1, -0.1, 0], 1, 4, [column], 8);
  assert.equal(cells.length, 8);
  assert.ok(cells.some((cell) => cell.clipped));
  assert.ok(cells.some((cell) => !cell.clipped));
  for (const cell of cells) {
    const side = [0, 0, 1];
    for (let along = 0; along <= 60; along += 1) {
      for (const across of [-0.5, -0.25, 0, 0.25, 0.5]) {
        const point = add(add(cell.origin, scale(cell.direction, cell.end * along / 60)),
          scale(side, across * cell.width));
        const insideHeight = point[1] > column.bottom && point[1] < column.top;
        const insideRadius = Math.hypot(point[0] - column.x, point[2] - column.z) < column.radius - 1e-9;
        assert.ok(!(insideHeight && insideRadius), 'a visible/collidable quad must not enter stone');
      }
    }
  }

  // Query the same clipped rectangles used for display, not the uncut parent strip.
  function hasSupport(point) {
    return cells.some((cell) => {
      const delta = sub(point, cell.origin);
      const along = dot(delta, cell.direction);
      return along >= cell.start && along <= cell.end && Math.abs(delta[2]) <= cell.width / 2;
    });
  }
  assert.equal(hasSupport([8, 1.2, 0]), false, 'the shadow behind the pillar has no support');
  assert.equal(hasSupport([8, 1.2, 1.5]), true, 'unobstructed adjacent light stays walkable');
  assert.deepEqual(column, { type: 'cylinder', x: 5, z: 0, radius: 0.5, bottom: 0, top: 4 });
});

test('a small pillar between sampled ray centres still clips the whole-width cells', () => {
  const cells = solarBeamCells([0, 2, 0], [1, -0.1, 0], 1, 4,
    [{ type: 'cylinder', x: 5, z: 0, radius: 0.03, bottom: 0, top: 4 }], 4);
  const middleCells = cells.filter((cell) => Math.abs(cell.xoffset) === 0.5);
  assert.equal(middleCells.length, 2);
  assert.ok(middleCells.every((cell) => cell.clipped), 'half-width inflation catches edge penetration');
});

test('authored D1 loses its column-facing edge while its centre light remains connected', () => {
  const d1 = DAY_RAMPS[0];
  const cylinders = WORLD.floorHeights.flatMap((bottom) => WORLD.columns.map((point) => ({
    type: 'cylinder', x: point[0], z: point[2], radius: 0.49, bottom, top: bottom + 5.65,
  })));
  const phase = phaseAtPosition(0, d1.foot);
  const direction = scale(sunDirection(phase), -1);
  const cells = solarBeamCells(d1.top, direction, 0, d1.width, cylinders);
  assert.ok(cells.some((cell) => cell.clipped), 'the pillar-facing edge really is removed');
  const central = cells.filter((cell) => Math.abs(cell.xoffset) < d1.width / 12);
  assert.equal(central.length, 2);
  assert.ok(central.every((cell) => !cell.clipped), 'the intended centre route remains lit');
});
