/** Small, rendering-independent character motor. Positions are foot positions. */

const GRAVITY = 18;
const JUMP_SPEED = Math.sqrt(2 * GRAVITY * 1.0);
const MAX_STEP_UP = 0.45;
const SNAP_DOWN = 0.2;
const EDGE_REACH = 0.13;
const COYOTE_TIME = 0.12;
const JUMP_BUFFER = 0.12;
const SUBSTEP = 1 / 120;
const MAX_DT = 0.25;
const EPSILON = 1e-5;
const DIAGONAL = Math.SQRT1_2;
const PROBE_DIRECTIONS = [
  [0, 0], [1, 0], [-1, 0], [0, 1], [0, -1],
  [DIAGONAL, DIAGONAL], [DIAGONAL, -DIAGONAL],
  [-DIAGONAL, DIAGONAL], [-DIAGONAL, -DIAGONAL],
];

function validPosition(position) {
  return Array.isArray(position) && position.length === 3
    && [0, 1, 2].every((axis) => Number.isFinite(position[axis]));
}

/**
 * sampleSupport(x,z,fromY,maxDrop) returns the highest top in
 * [fromY-maxDrop, fromY], or null. It must not return a ceiling above fromY.
 * blocked(footPosition,radius,height) tests the body at a candidate location.
 * Movement is in world X/Z. A held jump does not repeatedly jump on landing.
 */
export class PlayerMotor {
  constructor({ position = [0, 0, 0], radius = 0.27, height = 1.7, speed = 3.2 } = {}) {
    if (!validPosition(position)) throw new TypeError('position must be a finite XYZ array.');
    if (!Number.isFinite(radius) || radius <= 0
        || !Number.isFinite(height) || height <= 0
        || !Number.isFinite(speed) || speed < 0) {
      throw new RangeError('radius and height must be positive; speed must be non-negative.');
    }
    this.position = [...position];
    this.velocity = [0, 0, 0];
    this.grounded = false;
    this.radius = radius;
    this.height = height;
    this.speed = speed;
    this._coyote = 0;
    this._jumpBuffer = 0;
    this._jumpHeld = false;
  }

  teleport(position) {
    if (!validPosition(position)) throw new TypeError('position must be a finite XYZ array.');
    for (let axis = 0; axis < 3; axis += 1) this.position[axis] = position[axis];
    this.velocity.fill(0);
    this.grounded = false;
    this._coyote = 0;
    this._jumpBuffer = 0;
    this._jumpHeld = false;
  }

  _support(x, z, fromY, maxDrop, sampleSupport) {
    let best = null;
    const reach = Math.min(EDGE_REACH, this.radius);
    for (const [dx, dz] of PROBE_DIRECTIONS) {
      const top = sampleSupport(x + dx * reach, z + dz * reach, fromY, maxDrop);
      if (Number.isFinite(top) && top <= fromY + EPSILON
          && top >= fromY - maxDrop - EPSILON && (best === null || top > best)) {
        best = top;
      }
    }
    return best;
  }

  _bodyBlocked(position, blocked) {
    return Boolean(blocked(position, this.radius, this.height));
  }

  _tryJump() {
    if (this._jumpBuffer > 0 && (this.grounded || this._coyote > 0)) {
      this.velocity[1] = JUMP_SPEED;
      this.grounded = false;
      this._coyote = 0;
      this._jumpBuffer = 0;
      return true;
    }
    return false;
  }

  _horizontalCandidate(x, z, sampleSupport, blocked) {
    const y = this.position[1];
    let top = null;
    if (this.grounded) {
      top = this._support(x, z, y + MAX_STEP_UP, MAX_STEP_UP + SNAP_DOWN, sampleSupport);
    }
    const candidate = [x, top === null ? y : top, z];
    if (!this._bodyBlocked(candidate, blocked)) {
      return { position: candidate, supported: this.grounded && top !== null };
    }

    // A body can meet the riser before its small foot probes reach the top.
    // Only a currently grounded body may try a bounded step over a low riser.
    if (!this.grounded || (x === this.position[0] && z === this.position[2])) return null;
    const raisedY = y + MAX_STEP_UP;
    if (this._bodyBlocked([this.position[0], raisedY, this.position[2]], blocked)
        || this._bodyBlocked([x, raisedY, z], blocked)) return null;
    let low = y;
    let high = raisedY;
    for (let i = 0; i < 12; i += 1) {
      const middle = (low + high) / 2;
      if (this._bodyBlocked([x, middle, z], blocked)) low = middle;
      else high = middle;
    }
    const support = this._support(x, z, high + EPSILON, 0.025, sampleSupport);
    return { position: [x, high, z], supported: support !== null };
  }

  _moveHorizontal(dx, dz, sampleSupport, blocked) {
    const apply = (candidate) => {
      if (candidate === null) return false;
      this.position[0] = candidate.position[0];
      this.position[1] = candidate.position[1];
      this.position[2] = candidate.position[2];
      this.grounded = candidate.supported;
      return true;
    };
    const full = this._horizontalCandidate(
      this.position[0] + dx, this.position[2] + dz, sampleSupport, blocked,
    );
    if (apply(full)) return;
    // Slide along a blocking wall rather than cancelling both movement axes.
    if (dx !== 0) apply(this._horizontalCandidate(
      this.position[0] + dx, this.position[2], sampleSupport, blocked,
    ));
    if (dz !== 0) apply(this._horizontalCandidate(
      this.position[0], this.position[2] + dz, sampleSupport, blocked,
    ));
  }

  _moveVertical(dt, sampleSupport, blocked) {
    const oldY = this.position[1];
    const nextY = oldY + this.velocity[1] * dt - 0.5 * GRAVITY * dt * dt;
    this.velocity[1] -= GRAVITY * dt;

    // Only the downward sweep may land. Never query MAX_STEP_UP while airborne:
    // doing so would attach the player to a higher floor through its underside.
    if (nextY <= oldY && this.velocity[1] <= 0) {
      const top = this._support(
        this.position[0], this.position[2], oldY + EPSILON,
        oldY - nextY + 2 * EPSILON, sampleSupport,
      );
      if (top !== null && top >= nextY - EPSILON
          && !this._bodyBlocked([this.position[0], top, this.position[2]], blocked)) {
        this.position[1] = top;
        this.velocity[1] = 0;
        this.grounded = true;
        this._coyote = COYOTE_TIME;
        return;
      }
    }

    const target = [this.position[0], nextY, this.position[2]];
    if (!this._bodyBlocked(target, blocked)) {
      this.position[1] = nextY;
      return;
    }

    // Resolve upward ceiling contact (and solid vertical contacts) without
    // tunnelling. The body sweep is small because update uses fixed substeps.
    if (!this._bodyBlocked(this.position, blocked)) {
      let free = oldY;
      let occupied = nextY;
      for (let i = 0; i < 12; i += 1) {
        const middle = (free + occupied) / 2;
        if (this._bodyBlocked([this.position[0], middle, this.position[2]], blocked)) {
          occupied = middle;
        } else free = middle;
      }
      this.position[1] = free;
    }
    this.velocity[1] = 0;
  }

  update(dt, input = {}, sampleSupport, blocked = () => false) {
    if (typeof sampleSupport !== 'function' || typeof blocked !== 'function') {
      throw new TypeError('sampleSupport and blocked must be functions.');
    }
    const jumping = input.jump === true;
    if (jumping && !this._jumpHeld) this._jumpBuffer = JUMP_BUFFER;
    this._jumpHeld = jumping;
    const elapsed = Number.isFinite(dt) ? Math.min(MAX_DT, Math.max(0, dt)) : 0;
    if (elapsed === 0) return this.position;

    let moveX = Number.isFinite(input.move?.[0]) ? input.move[0] : 0;
    let moveZ = Number.isFinite(input.move?.[1]) ? input.move[1] : 0;
    const length = Math.hypot(moveX, moveZ);
    if (length > 0) { moveX /= length; moveZ /= length; }
    const startX = this.position[0];
    const startZ = this.position[2];
    const count = Math.ceil(elapsed / SUBSTEP);
    const step = elapsed / count;

    for (let i = 0; i < count; i += 1) {
      // Initial spawn/teleport may place feet exactly on a known surface.
      if (!this.grounded && Math.abs(this.velocity[1]) < EPSILON) {
        const top = this._support(
          this.position[0], this.position[2], this.position[1] + EPSILON, 0.025, sampleSupport,
        );
        if (top !== null && !this._bodyBlocked([this.position[0], top, this.position[2]], blocked)) {
          this.position[1] = top;
          this.grounded = true;
        }
      }
      if (this.grounded) this._coyote = COYOTE_TIME;
      this._tryJump();
      this._moveHorizontal(moveX * this.speed * step, moveZ * this.speed * step, sampleSupport, blocked);

      if (this.grounded) this.velocity[1] = 0;
      else this._moveVertical(step, sampleSupport, blocked);

      // A buffered press made just before landing can take off on this frame.
      if (this.grounded) this._tryJump();
      if (!this.grounded) this._coyote = Math.max(0, this._coyote - step);
      this._jumpBuffer = Math.max(0, this._jumpBuffer - step);
    }

    this.velocity[0] = (this.position[0] - startX) / elapsed;
    this.velocity[2] = (this.position[2] - startZ) / elapsed;
    return this.position;
  }
}
