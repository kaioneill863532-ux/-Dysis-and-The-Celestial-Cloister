import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEG, add, sub, scale, dot, cross, length, normalize, distance, polar,
  reflect, mirrorNormal, sunDirection, moonDirection, rayPlane, projectShadow,
  segmentDistanceXZ, unwrapAngle, uniformPhase, connectionPhase,
} from '../prototype/rotunda/core/math.js';

function near(actual, expected, tolerance = 1e-10) {
  assert.ok(Math.abs(actual - expected) <= tolerance,
    `Expected ${actual} to be within ${tolerance} of ${expected}`);
}

function vectorNear(actual, expected, tolerance = 1e-10) {
  assert.equal(actual.length, expected.length);
  actual.forEach((value, index) => near(value, expected[index], tolerance));
}

test('vectors and polar positions follow the east/up/south convention without mutation', () => {
  const a = [1, 2, 3];
  const b = [4, 5, 6];
  vectorNear(add(a, b), [5, 7, 9]);
  vectorNear(sub(a, b), [-3, -3, -3]);
  vectorNear(scale(a, 2), [2, 4, 6]);
  near(dot(a, b), 32);
  vectorNear(cross([1, 0, 0], [0, 1, 0]), [0, 0, 1]);
  vectorNear(polar(4, 0, 6), [4, 6, 0]);
  vectorNear(polar(4, Math.PI / 2, 6), [0, 6, 4]);
  vectorNear(normalize([0, 0, 0]), [0, 0, 0]);
  near(distance(a, b), Math.sqrt(27));
  assert.deepEqual(a, [1, 2, 3]);
  assert.deepEqual(b, [4, 5, 6]);
});

test('both celestial paths stay on their original fixed declination circles', () => {
  const polarAxis = [0, Math.sin(35 * DEG), -Math.cos(35 * DEG)];
  for (let hourAngle = -720; hourAngle <= 720; hourAngle += 7) {
    const sun = sunDirection(hourAngle);
    const moon = moonDirection(hourAngle);
    near(length(sun), 1);
    near(length(moon), 1);
    near(dot(sun, polarAxis), Math.sin(-21 * DEG));
    near(dot(moon, polarAxis), Math.sin(20 * DEG));
    vectorNear(sunDirection(hourAngle + 360), sun);
    vectorNear(moonDirection(hourAngle + 360), moon);
    assert.ok(Math.asin(sun[1]) / DEG <= 34 + 1e-10);
    assert.ok(Math.asin(moon[1]) / DEG <= 75 + 1e-10);
  }
  near(Math.asin(sunDirection(0)[1]) / DEG, 34);
  near(Math.asin(moonDirection(180)[1]) / DEG, 75);
  assert.ok(sunDirection(-45)[0] > 0, 'morning sun is in the east');
  assert.ok(sunDirection(45)[0] < 0, 'afternoon sun is in the west');
});

test('mirror reflection preserves length and reverses only the normal component', () => {
  const incoming = [3, -2, 4];
  const normal = [0, 7, 0];
  const reflected = reflect(incoming, normal);
  vectorNear(reflected, [3, 2, 4]);
  near(length(reflected), length(incoming));
  near(dot(reflected, normalize(normal)), -dot(incoming, normalize(normal)));
  vectorNear(reflect(reflected, normal), incoming);
  vectorNear(reflect(incoming, [0, 0, 0]), incoming);
});

test('a tilted mirror gives the proposed rising shrine branch and shared crossing', () => {
  const incoming = normalize([1, -Math.tan(20 * DEG), 0]);
  const mirror = [0, 6, 3];
  const shrine = [8, 10, -2];
  const crossing = [4.8, 8.4, 0];
  const outgoing = normalize(sub(shrine, mirror));
  const normal = mirrorNormal(incoming, outgoing);
  near(length(normal), 1);
  vectorNear(reflect(incoming, normal), outgoing);
  assert.ok(outgoing[1] > 0, 'the reflected ray rises toward the shrine');
  vectorNear(rayPlane(mirror, outgoing, crossing, [0, 0, 1]).point, crossing);

  // A perfectly vertical mirror preserves the downward vertical component.
  const verticalMirror = reflect(incoming, [1, 0, 0]);
  near(verticalMirror[1], incoming[1]);
  vectorNear(mirrorNormal(incoming, incoming), [0, 0, 0]);
});

test('ray-plane intersections reject parallel and backward rays and preserve ray parameters', () => {
  const planePoint = [0, 0, 0];
  const planeNormal = [0, 3, 0];
  const hit = rayPlane([1, 4, 3], [0, -2, 0], planePoint, planeNormal);
  near(hit.t, 2);
  vectorNear(hit.point, [1, 0, 3]);
  assert.equal(rayPlane([1, 4, 3], [1, 0, 0], planePoint, planeNormal), null);
  assert.equal(rayPlane([1, 4, 3], [0, 1, 0], planePoint, planeNormal), null);
  assert.equal(rayPlane([1, 4, 3], [0, 0, 0], planePoint, planeNormal), null);
  assert.equal(rayPlane([1, 4, 3], [0, -1, 0], planePoint, [0, 0, 0]), null);
  assert.equal(rayPlane([1, 0, 3], [1, 0, 0], planePoint, planeNormal), null);
  near(rayPlane([1, 0, 3], [0, -1, 0], planePoint, planeNormal).t, 0);
});

test('the 20-degree oculus ray reaches L3 near radius 12m and clears the closed iris', () => {
  const upperRim = [-4.5, 24, 0];
  const incoming = [Math.cos(20 * DEG), -Math.sin(20 * DEG), 0];
  const landing = rayPlane(upperRim, incoming, [0, 18, 0], [0, 1, 0]);
  vectorNear(landing.point, [11.984864516727736, 18, 0]);
  near(landing.point[0], 12, 0.02);
  near(distance(upperRim, landing.point) * Math.sin(20 * DEG), 6);

  const irisHeight = 23.3;
  const irisHit = rayPlane(upperRim, incoming, [0, irisHeight, 0], [0, 1, 0]);
  assert.ok(Math.hypot(irisHit.point[0], irisHit.point[2]) < 4.5,
    'the 9m initial aperture does not require opening for this centreline');
});

test('parallel-light shadow projection handles translated silhouettes and world points', () => {
  const localVertices = [[0, 1, 0], [2, 1, 0]];
  const origin = [3, 2, 5];
  const direction = [1, -1, 0];
  const floor = [0, 0, 0];
  const normal = [0, 1, 0];
  const expected = [[6, 0, 5], [8, 0, 5]];
  const fromLocal = projectShadow(localVertices, origin, direction, floor, normal);
  const fromWorld = projectShadow([[3, 3, 5], [5, 3, 5]], null, direction, floor, normal);
  fromLocal.forEach((vertex, index) => vectorNear(vertex, expected[index]));
  fromWorld.forEach((vertex, index) => vectorNear(vertex, expected[index]));
  assert.deepEqual(projectShadow([[0, 1, 0]], null, [1, 0, 0], floor, normal), [null]);
  assert.deepEqual(projectShadow([[0, -1, 0], [0, 1, 0]], null, direction, floor, normal),
    [null, [1, 0, 0]]);
  assert.deepEqual(localVertices, [[0, 1, 0], [2, 1, 0]]);
});

test('XZ segment distances clamp to endpoints and interpolate support height', () => {
  const a = [0, 3, 0];
  const b = [10, 9, 0];
  const middle = segmentDistanceXZ([5, 200, 2], a, b);
  near(middle.t, 0.5);
  near(middle.distance, 2);
  near(middle.y, 6);
  assert.deepEqual(segmentDistanceXZ([-3, 4, 0], a, b), { t: 0, distance: 3, y: 3 });
  assert.deepEqual(segmentDistanceXZ([13, 4, 0], a, b), { t: 1, distance: 3, y: 9 });
  assert.deepEqual(segmentDistanceXZ([3, 4, 4], a, [0, 9, 0]),
    { t: 0, distance: 5, y: 3 });
});

test('uniform phase is clamped and linear across an unwrapped seam in either direction', () => {
  const start = 350 * DEG;
  const end = 430 * DEG;
  const nearStart = unwrapAngle(10 * DEG, (start + end) / 2);
  near(nearStart, 370 * DEG);
  near(uniformPhase(nearStart, start, end, 20, 60), 30);
  near(uniformPhase(390 * DEG, start, end, 20, 60), 40);
  near(uniformPhase(440 * DEG, start, end, 20, 60), 60);
  near(uniformPhase(340 * DEG, start, end, 20, 60), 20);
  near(uniformPhase(390 * DEG, end, start, 20, 60), 40);
  near(uniformPhase(440 * DEG, end, start, 20, 60), 20);
  near(uniformPhase(340 * DEG, end, start, 20, 60), 60);
  near(uniformPhase(3 * Math.PI, 0, 4 * Math.PI, 0, 100), 75);
  near(uniformPhase(1, 0, 0, 20, 60), 20);
});

test('an axis-crossing connection keeps its authored phase despite the atan2 discontinuity', () => {
  const a = [12, 18, 0];
  const b = [-4.5, 24, 0];
  const points = [a, [1, 22, 0], [0.0001, 22, 0], [0, 22, 0], [-0.0001, 22, 0], b];
  const phase = 53;
  const source = sunDirection(phase);
  assert.equal(Math.atan2(points[1][2], points[1][0]), 0);
  assert.equal(Math.atan2(points.at(-1)[2], points.at(-1)[0]), Math.PI);
  for (const point of points) {
    const progress = segmentDistanceXZ(point, a, b).t;
    const result = connectionPhase(phase, phase, progress);
    near(result, phase);
    vectorNear(sunDirection(result), source);
  }
  near(connectionPhase(53), 53);
  near(connectionPhase(53, 55, -1), 53);
  near(connectionPhase(53, 55, 0.5), 54);
  near(connectionPhase(53, 55, 2), 55);
});
