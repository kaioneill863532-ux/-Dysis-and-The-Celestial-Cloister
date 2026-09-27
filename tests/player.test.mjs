import test from 'node:test';
import assert from 'node:assert/strict';
import { PlayerMotor } from '../prototype/rotunda/core/player.js';

const free = () => false;
function supports(heightAt) {
  return (x, z, fromY, maxDrop) => {
    const candidates = heightAt(x, z);
    return candidates.filter((y) => y <= fromY + 1e-8 && y >= fromY - maxDrop - 1e-8)
      .sort((a, b) => b - a)[0] ?? null;
  };
}
const floor = supports(() => [0]);
function run(player, seconds, input, support = floor, blocked = free) {
  const frames = Math.ceil(seconds * 120);
  for (let i = 0; i < frames; i += 1) player.update(seconds / frames, input, support, blocked);
}
function approximately(actual, expected, tolerance = 1e-6) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} should be near ${expected}`);
}

test('world movement is normalized and stays grounded on a floor', () => {
  const player = new PlayerMotor();
  run(player, 1, { move: [1, 1] });
  approximately(Math.hypot(player.position[0], player.position[2]), 3.2);
  approximately(player.position[1], 0);
  assert.equal(player.grounded, true);
});

test('the jump apex is one metre and a held key does not cause bunny hopping', () => {
  const player = new PlayerMotor();
  let highest = 0;
  for (let frame = 0; frame < 150; frame += 1) {
    player.update(1 / 120, { move: [0, 0], jump: true }, floor, free);
    highest = Math.max(highest, player.position[1]);
  }
  approximately(highest, 1, 0.002);
  assert.equal(player.grounded, true);
  approximately(player.position[1], 0);
});

test('coyote time allows a jump just after walking beyond a ledge', () => {
  const ledge = supports((x) => x <= 0 ? [0] : []);
  const player = new PlayerMotor({ position: [-0.1, 0, 0] });
  run(player, 0.1, { move: [1, 0] }, ledge);
  assert.equal(player.grounded, false);
  assert.ok(player.position[0] > 0.13);
  const before = player.position[1];
  player.update(0.02, { move: [0, 0], jump: true }, ledge, free);
  assert.ok(player.velocity[1] > 0);
  assert.ok(player.position[1] > before);
});

test('coyote time expires and cannot become an air jump', () => {
  const ledge = supports((x) => x <= 0 ? [0] : []);
  const player = new PlayerMotor({ position: [-0.1, 0, 0] });
  run(player, 0.1, { move: [1, 0] }, ledge);
  run(player, 0.14, { move: [0, 0] }, ledge);
  player.update(0.01, { move: [0, 0], jump: true }, ledge, free);
  assert.ok(player.velocity[1] < 0);
});

test('walking off a height falls naturally rather than snapping to a lower storey', () => {
  const twoLevels = supports((x) => x <= 0 ? [0, -2] : [-2]);
  const player = new PlayerMotor({ position: [-0.1, 0, 0] });
  run(player, 0.12, { move: [1, 0] }, twoLevels);
  assert.equal(player.grounded, false);
  assert.ok(player.position[1] < 0 && player.position[1] > -0.15);
  run(player, 1, { move: [0, 0] }, twoLevels);
  assert.equal(player.grounded, true);
  approximately(player.position[1], -2);
});

test('a ramp supports walking uphill and catches a descending airborne player', () => {
  const ramp = supports((x) => [Math.max(0, x * 0.3)]);
  const walking = new PlayerMotor({ position: [-0.3, 0, 0] });
  run(walking, 1, { move: [1, 0] }, ramp);
  assert.equal(walking.grounded, true);
  assert.ok(walking.position[1] > 0.8);
  approximately(walking.position[1], (walking.position[0] + 0.13) * 0.3, 0.003);

  const falling = new PlayerMotor({ position: [0.5, 2, 0] });
  run(falling, 1, { move: [1, 0] }, ramp);
  assert.equal(falling.grounded, true);
  approximately(falling.position[1], (falling.position[0] + 0.13) * 0.3, 0.003);
});

test('a low solid riser can be stepped onto, but a taller riser blocks movement', () => {
  function stepWorld(height) {
    return {
      support: supports((x) => x >= 0 ? [height] : [0]),
      blocked: (position, radius) => position[0] + radius > 0 && position[1] < height - 1e-7,
    };
  }
  const low = stepWorld(0.4);
  const player = new PlayerMotor({ position: [-0.5, 0, 0] });
  run(player, 0.5, { move: [1, 0] }, low.support, low.blocked);
  assert.ok(player.position[0] > 0.5);
  approximately(player.position[1], 0.4, 0.002);
  assert.equal(player.grounded, true);

  const tall = stepWorld(0.6);
  const stopped = new PlayerMotor({ position: [-0.5, 0, 0] });
  run(stopped, 0.5, { move: [1, 0] }, tall.support, tall.blocked);
  assert.ok(stopped.position[0] < 0);
  approximately(stopped.position[1], 0);
});

test('a jump pressed shortly before landing is buffered, but only once', () => {
  const player = new PlayerMotor({ position: [0, 0.15, 0] });
  player.velocity[1] = -1;
  run(player, 0.1, { move: [0, 0], jump: true });
  assert.ok(player.velocity[1] > 0);
  assert.ok(player.position[1] > 0);
  run(player, 1, { move: [0, 0], jump: true });
  assert.equal(player.grounded, true);
});

test('a falling player under an upper floor cannot attach through its underside', () => {
  const floors = supports(() => [0, 2.7]);
  const player = new PlayerMotor({ position: [0, 2.2, 0] });
  let highest = player.position[1];
  for (let frame = 0; frame < 120; frame += 1) {
    player.update(1 / 120, { move: [0, 0] }, floors, free);
    highest = Math.max(highest, player.position[1]);
  }
  approximately(highest, 2.2);
  approximately(player.position[1], 0);
  assert.equal(player.grounded, true);
});

test('ceiling contact stops a jump before the player penetrates an upper floor', () => {
  const ceilingY = 2.3;
  const slabTop = 2.5;
  const ceiling = (position, _radius, height) => position[1] + height > ceilingY
    && position[1] < slabTop;
  const floors = supports(() => [0, slabTop]);
  const player = new PlayerMotor();
  let highest = 0;
  for (let frame = 0; frame < 120; frame += 1) {
    player.update(1 / 120, { jump: frame === 0 }, floors, ceiling);
    highest = Math.max(highest, player.position[1]);
  }
  assert.ok(highest <= ceilingY - player.height + 1e-5);
  assert.ok(highest > 0.5);
  approximately(player.position[1], 0);
});

test('edge assistance reaches only 0.13m and rejects support above the query', () => {
  const ledge = supports((x) => x <= 0 ? [0] : []);
  const close = new PlayerMotor({ position: [0.12, 0, 0] });
  close.update(0.01, {}, ledge, free);
  assert.equal(close.grounded, true);
  const outside = new PlayerMotor({ position: [0.15, 0, 0] });
  outside.update(0.01, {}, ledge, free);
  assert.equal(outside.grounded, false);
  assert.ok(outside.position[1] < 0);
  const invalid = new PlayerMotor();
  invalid.update(0.01, {}, () => 10, free);
  assert.equal(invalid.grounded, false);
  assert.ok(invalid.position[1] < 0);
});

test('wall collisions slide without increasing movement speed', () => {
  const player = new PlayerMotor({ position: [-0.5, 0, 0] });
  const wall = (position, radius) => position[0] + radius > 0;
  run(player, 1, { move: [1, 1] }, floor, wall);
  assert.ok(player.position[0] <= -player.radius + 0.001);
  assert.ok(player.position[2] > 2);
  assert.ok(Math.hypot(player.velocity[0], player.velocity[2]) <= player.speed + 1e-6);
});

test('teleport resets motion and rejects invalid coordinates; invalid dt does not move', () => {
  const player = new PlayerMotor();
  player.update(0.05, { move: [1, 0], jump: true }, floor, free);
  player.teleport([4, 3, 2]);
  assert.deepEqual(player.position, [4, 3, 2]);
  assert.deepEqual(player.velocity, [0, 0, 0]);
  assert.equal(player.grounded, false);
  for (const dt of [-1, Infinity, NaN]) player.update(dt, {}, floor, free);
  assert.deepEqual(player.position, [4, 3, 2]);
  assert.throws(() => player.teleport([0, NaN, 0]), TypeError);
});
