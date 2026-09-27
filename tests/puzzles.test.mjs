import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MoonForm,
  NightProgress,
  dualBridgeReady,
  pairAlignment,
  shadowAlignment,
} from '../prototype/rotunda/core/puzzles.js';

function advance(form, exposed, seconds, step = 0.01) {
  const steps = Math.ceil(seconds / step);
  for (let i = 0; i < steps; i += 1) {
    form.update(exposed, Math.min(step, Math.max(0, seconds - i * step)));
  }
  return form.value;
}

function closeTo(actual, expected, epsilon = 1e-9) {
  assert.ok(Math.abs(actual - expected) <= epsilon, `${actual} should equal ${expected}`);
}

test('a sculpture rises to moon form C and returns to B after losing moonlight', () => {
  const form = new MoonForm();
  closeTo(advance(form, true, 0.35), 1);
  closeTo(advance(form, false, 0.175), 0.5);
  closeTo(advance(form, false, 0.175), 0);
});

test('grace only applies to its own object and exposure cancels a pending fall', () => {
  const ordinary = new MoonForm({ riseTime: 0.2, fallTime: 0.2 });
  const sheltered = new MoonForm({ riseTime: 0.2, fallTime: 0.2, grace: 0.15 });
  advance(ordinary, true, 0.2);
  advance(sheltered, true, 0.2);
  closeTo(advance(ordinary, false, 0.1), 0.5);
  closeTo(advance(sheltered, false, 0.1), 1);
  closeTo(advance(sheltered, false, 0.1), 0.75);
  closeTo(advance(sheltered, true, 0.05), 1);
  closeTo(advance(sheltered, false, 0.15), 1);
  closeTo(advance(sheltered, false, 0.2), 0);
});

test('re-entering light during grace resets the local grace period', () => {
  const form = new MoonForm({ riseTime: 0.1, grace: 0.2 });
  form.update(true, 0.1);
  advance(form, false, 0.15);
  form.update(true, 0.01);
  advance(form, false, 0.15);
  closeTo(form.value, 1);
  advance(form, false, 0.1);
  assert.ok(form.value < 1);
});

test('large and invalid deltas cannot pop or corrupt a moon form', () => {
  const form = new MoonForm();
  closeTo(form.update(true, 100), 0.1 / 0.35);
  const before = form.value;
  for (const dt of [NaN, Infinity, -Infinity, -0.5, undefined]) {
    closeTo(form.update(true, dt), before);
  }
  closeTo(form.update(false, 100), 0);
  for (const option of ['riseTime', 'fallTime', 'grace']) {
    assert.throws(() => new MoonForm({ [option]: -1 }), RangeError);
    assert.throws(() => new MoonForm({ [option]: NaN }), RangeError);
  }
});

test('zero-duration forms still require a positive simulation step', () => {
  const form = new MoonForm({ riseTime: 0, fallTime: 0 });
  closeTo(form.update(true, 0), 0);
  closeTo(form.update(true, 0.01), 1);
  closeTo(form.update(false, 0), 1);
  closeTo(form.update(false, 0.01), 0);
});

const swan = [[0, 0, 0], [0.6, 0.9, 0], [1.3, 0.2, 0], [0.7, -0.1, 0]];

test('swan shadow alignment uses actual projected positions, not just a matching shape', () => {
  closeTo(shadowAlignment(swan, swan), 1);
  const translated = swan.map(([x, y, z]) => [x + 0.3, y, z]);
  closeTo(shadowAlignment(translated, swan), 0);
  const slightOffset = swan.map(([x, y, z]) => [x + 0.11, y, z]);
  closeTo(shadowAlignment(slightOffset, swan), 0.5);
  const reversedSwan = swan.map(([x, y, z]) => [-x, y, z]);
  closeTo(shadowAlignment(reversedSwan, swan), 0);
});

test('a mismatched landmark cannot hide inside an otherwise aligned silhouette', () => {
  const movedWing = swan.map((point) => [...point]);
  movedWing[1][0] += 0.22;
  closeTo(shadowAlignment(movedWing, swan), 0);
  closeTo(shadowAlignment([[1, 2], [2, 3]], [[1, 2], [2, 3]]), 1);
  for (const points of [[], [[0, 0]], [[NaN, 0, 0]], [[0, 0, 0], null]]) {
    closeTo(shadowAlignment(points, swan), 0);
  }
  closeTo(shadowAlignment(swan, swan, { positionTolerance: 0 }), 0);
  const sparsePoint = new Array(3);
  closeTo(shadowAlignment([sparsePoint], [[0, 0, 0]]), 0);
});

test('two sculptures align only with close XYZ sockets and simultaneous exposure', () => {
  assert.equal(pairAlignment([1, 2, 3], [1.2, 2, 3], true, true), true);
  assert.equal(pairAlignment([1, 2, 3], [1, 2.31, 3], true, true), false);
  assert.equal(pairAlignment([1, 2, 3], [1, 2, 3], false, true), false);
  assert.equal(pairAlignment([1, 2, 3], [1, 2, 3], true, false), false);
  assert.equal(pairAlignment([1, 2, NaN], [1, 2, 3], true, true), false);
  assert.equal(pairAlignment([1, 2], [1, 2], true, true), false);
});

test('the final bridge requires both current optical branches and developed C forms', () => {
  assert.equal(dualBridgeReady(true, true, 1, 0.92), true);
  assert.equal(dualBridgeReady(true, true, 1, 0.919), false);
  assert.equal(dualBridgeReady(true, false, 1, 1), false);
  assert.equal(dualBridgeReady(false, true, 1, 1), false);
  assert.equal(dualBridgeReady(true, true, NaN, 1), false);
  assert.equal(dualBridgeReady(true, true, 1, Infinity), false);
  assert.equal(dualBridgeReady(true, true, 1, 1, NaN), false);

  // A retained visual grace must not silently substitute for the missing ray.
  const form = new MoonForm({ riseTime: 0.1, grace: 0.2 });
  form.update(true, 0.1);
  form.update(false, 0.1);
  closeTo(form.value, 1);
  assert.equal(dualBridgeReady(true, false, 1, form.value), false);
});

test('completion records persist but cannot latch a moon form or a bridge', () => {
  const progress = new NightProgress();
  const formA = new MoonForm();
  const formB = new MoonForm();
  advance(formA, true, 0.4);
  advance(formB, true, 0.4);
  assert.equal(dualBridgeReady(true, true, formA.value, formB.value), true);
  progress.complete('water-pavilion');

  advance(formB, false, 0.4);
  closeTo(formB.value, 0);
  assert.equal(progress.hasCompleted('water-pavilion'), true);
  assert.equal(dualBridgeReady(true, false, formA.value, formB.value), false);
  assert.deepEqual(progress.toJSON(), {
    version: 1, discovered: ['water-pavilion'], completed: ['water-pavilion'],
  });
});

test('night journal round-trips, auto-discovers completions and protects its sets', () => {
  const progress = new NightProgress();
  assert.equal(progress.discover('swan-shadow'), true);
  assert.equal(progress.discover('swan-shadow'), false);
  assert.equal(progress.complete('paired-sculptures'), true);
  assert.equal(progress.complete('paired-sculptures'), false);
  assert.equal(progress.hasDiscovered('paired-sculptures'), true);
  progress.completed.add('not-really-complete');
  assert.equal(progress.hasCompleted('not-really-complete'), false);

  const restored = NightProgress.fromJSON(JSON.stringify(progress));
  assert.deepEqual(restored.toJSON(), progress.toJSON());
  assert.equal(restored.hasCompleted('paired-sculptures'), true);
  assert.equal(restored.hasCompleted('swan-shadow'), false);
});

test('night save validation rejects stale schemas, malformed ids and persisted route latches', () => {
  const valid = { version: 1, discovered: [], completed: [] };
  for (const state of [
    null,
    [],
    {},
    { ...valid, version: 2 },
    { ...valid, completed: ['unknown'] },
    { ...valid, discovered: ['duplicate', 'duplicate'] },
    { ...valid, discovered: [''] },
    { ...valid, discovered: [3] },
    { ...valid, discovered: new Array(1) },
    { ...valid, discovered: [' leading-space'] },
    { ...valid, bridgeLocked: true },
    { ...valid, discovered: 'swan-shadow' },
    { ...valid, discovered: ['a\nline'] },
  ]) {
    assert.throws(() => NightProgress.fromJSON(state));
  }
  assert.throws(() => NightProgress.fromJSON('{broken json'));
  assert.throws(() => new NightProgress().complete(''), TypeError);
});
