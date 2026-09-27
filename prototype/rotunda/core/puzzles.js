/**
 * Rendering-independent rules for the rotunda's moon puzzles.
 *
 * Progress records are deliberately separate from live light and geometry.
 * Discovering or completing a puzzle never holds a sculpture in its moon form.
 */

const MAX_FRAME_DT = 0.1;
const PROGRESS_VERSION = 1;
const MAX_PROGRESS_IDS = 256;

const clamp01 = (value) => Math.min(1, Math.max(0, value));

function nonNegativeDuration(value, name) {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError(`${name} must be a finite, non-negative number.`);
  }
  return value;
}

/**
 * Reversible B -> C form blend. Only actual moon exposure raises the blend.
 * `grace` is optional, local to this instance, and measured in simulation time.
 * Large frame deltas are capped so resuming a suspended tab cannot pop forms.
 */
export class MoonForm {
  value = 0;

  constructor({ riseTime = 0.35, fallTime = 0.35, grace = 0 } = {}) {
    this.riseTime = nonNegativeDuration(riseTime, 'riseTime');
    this.fallTime = nonNegativeDuration(fallTime, 'fallTime');
    this.grace = nonNegativeDuration(grace, 'grace');
    this._graceRemaining = 0;
  }

  update(exposed, dt) {
    const step = Number.isFinite(dt) ? Math.min(MAX_FRAME_DT, Math.max(0, dt)) : 0;
    this.value = Number.isFinite(this.value) ? clamp01(this.value) : 0;

    if (exposed === true) {
      // Re-entering the light cancels any pending fade and starts a fresh grace.
      this._graceRemaining = this.grace;
      if (step > 0) {
        this.value = this.riseTime === 0 ? 1 : clamp01(this.value + step / this.riseTime);
      }
      return this.value;
    }

    const graceUsed = Math.min(this._graceRemaining, step);
    this._graceRemaining = Math.max(0, this._graceRemaining - graceUsed);
    const fadeStep = step - graceUsed;
    if (fadeStep > 0) {
      this.value = this.fallTime === 0 ? 0 : clamp01(this.value - fadeStep / this.fallTime);
    }
    return this.value;
  }
}

function validPoint(point, dimensions) {
  if (!Array.isArray(point) || point.length !== dimensions) return false;
  // Index explicitly: Array#every skips holes in malformed coordinate arrays.
  for (let axis = 0; axis < dimensions; axis += 1) {
    if (!Number.isFinite(point[axis])) return false;
  }
  return true;
}

/**
 * Compare corresponding, physically projected landmarks with target landmarks.
 * Points may be 2D coordinates in the receiver plane or 3D world coordinates.
 * Both sets must share dimensions and units; no centering, rotation, or scaling
 * is applied, because a correct shape in the wrong place must not solve a mural.
 *
 * Returns 1 at exact alignment, 0 at/above positionTolerance, and a linear score
 * between. The worst landmark sets the score, so a misplaced wing cannot be
 * hidden by averaging many correctly positioned body points.
 */
export function shadowAlignment(
  projectedPoints,
  targetPoints,
  { positionTolerance = 0.22 } = {},
) {
  if (!Number.isFinite(positionTolerance) || positionTolerance <= 0
      || !Array.isArray(projectedPoints) || !Array.isArray(targetPoints)
      || projectedPoints.length === 0 || projectedPoints.length !== targetPoints.length) {
    return 0;
  }

  const dimensions = targetPoints[0]?.length;
  if (dimensions !== 2 && dimensions !== 3) return 0;

  let maxError = 0;
  for (let i = 0; i < targetPoints.length; i += 1) {
    const projected = projectedPoints[i];
    const target = targetPoints[i];
    if (!validPoint(projected, dimensions) || !validPoint(target, dimensions)) return 0;
    let errorSquared = 0;
    for (let axis = 0; axis < dimensions; axis += 1) {
      errorSquared += (projected[axis] - target[axis]) ** 2;
    }
    maxError = Math.max(maxError, Math.sqrt(errorSquared));
  }

  return clamp01(1 - maxError / positionTolerance);
}

/** Matching sockets alone are insufficient: both pieces must currently be lit. */
export function pairAlignment(
  movingSocket,
  fixedSocket,
  exposedA,
  exposedB,
  tolerance = 0.3,
) {
  if (exposedA !== true || exposedB !== true
      || !validPoint(movingSocket, 3) || !validPoint(fixedSocket, 3)
      || !Number.isFinite(tolerance) || tolerance < 0) return false;

  const distance = Math.hypot(
    movingSocket[0] - fixedSocket[0],
    movingSocket[1] - fixedSocket[1],
    movingSocket[2] - fixedSocket[2],
  );
  return distance <= tolerance;
}

/**
 * A live test, never a latch. Grace-blended geometry is not proof of exposure;
 * both optical branches and both current C forms must be ready simultaneously.
 */
export function dualBridgeReady(exposureA, exposureB, blendA, blendB, threshold = 0.92) {
  return exposureA === true && exposureB === true
    && Number.isFinite(threshold) && threshold >= 0 && threshold <= 1
    && Number.isFinite(blendA) && blendA >= threshold && blendA <= 1
    && Number.isFinite(blendB) && blendB >= threshold && blendB <= 1;
}

function validProgressId(id) {
  return typeof id === 'string' && id.length > 0 && id.length <= 128
    && id.trim() === id && !/[\u0000-\u001f\u007f]/u.test(id);
}

function assertProgressId(id) {
  if (!validProgressId(id)) {
    throw new TypeError('Puzzle ids must be non-empty, trimmed strings of at most 128 characters.');
  }
}

function validateProgress(data) {
  if (typeof data === 'string') data = JSON.parse(data);
  if (data === null || typeof data !== 'object' || Array.isArray(data)) {
    throw new TypeError('Night progress must be a JSON object.');
  }
  const keys = Reflect.ownKeys(data);
  const expected = ['version', 'discovered', 'completed'];
  if (keys.length !== expected.length || expected.some((key) => !Object.hasOwn(data, key))) {
    throw new TypeError('Night progress only accepts version, discovered, and completed.');
  }
  if (data.version !== PROGRESS_VERSION) {
    throw new RangeError(`Unsupported night progress version: ${String(data.version)}.`);
  }
  for (const key of ['discovered', 'completed']) {
    const ids = data[key];
    if (!Array.isArray(ids) || ids.length > MAX_PROGRESS_IDS
        || Array.from(ids).some((id) => !validProgressId(id)) || new Set(ids).size !== ids.length) {
      throw new TypeError(`${key} must contain at most ${MAX_PROGRESS_IDS} unique, valid puzzle ids.`);
    }
  }
  const discovered = new Set(data.discovered);
  if (data.completed.some((id) => !discovered.has(id))) {
    throw new TypeError('Every completed puzzle must also be discovered.');
  }
  return data;
}

/**
 * Persistent journal only. Exposures, blend values, socket positions, rotations,
 * and route readiness are intentionally absent from this save schema. A caller
 * must evaluate current MoonForm/optical state each frame for collision routes.
 * Moving sculptures retain position/yaw in the scene controller, not here.
 */
export class NightProgress {
  #discovered = new Set();
  #completed = new Set();

  constructor(savedState) {
    if (savedState !== undefined) {
      const data = validateProgress(savedState);
      this.#discovered = new Set(data.discovered);
      this.#completed = new Set(data.completed);
    }
  }

  get discovered() { return new Set(this.#discovered); }
  get completed() { return new Set(this.#completed); }

  discover(id) {
    assertProgressId(id);
    if (this.#discovered.has(id)) return false;
    if (this.#discovered.size >= MAX_PROGRESS_IDS) throw new RangeError('Too many discovered puzzles.');
    this.#discovered.add(id);
    return true;
  }

  complete(id) {
    assertProgressId(id);
    this.discover(id);
    const isNew = !this.#completed.has(id);
    this.#completed.add(id);
    return isNew;
  }

  hasDiscovered(id) { return this.#discovered.has(id); }
  hasCompleted(id) { return this.#completed.has(id); }

  toJSON() {
    return {
      version: PROGRESS_VERSION,
      discovered: [...this.#discovered].sort(),
      completed: [...this.#completed].sort(),
    };
  }

  static fromJSON(jsonOrObject) { return new NightProgress(jsonOrObject); }
}
