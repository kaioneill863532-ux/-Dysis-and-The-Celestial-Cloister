/**
 * Pure geometry for the rotunda prototype. Vectors are [x, y, z] arrays:
 * x points east, y points up and z points south. Angles are radians unless
 * a function explicitly accepts an hour angle in degrees.
 */
export const DEG = Math.PI / 180;

const EPSILON = 1e-10;
const TAU = Math.PI * 2;
const LATITUDE = 35 * DEG;
const SUN_DECLINATION = -21 * DEG;
const MOON_DECLINATION = 20 * DEG;

export const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
export const lerp = (a, b, t) => a + (b - a) * t;
export const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
export const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
export const scale = (v, amount) => [v[0] * amount, v[1] * amount, v[2] * amount];
export const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
export const cross = (a, b) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
export const length = (v) => Math.hypot(v[0], v[1], v[2]);
export const distance = (a, b) => length(sub(a, b));

/** Return a new unit vector, or [0, 0, 0] for a zero vector. */
export function normalize(v) {
  const magnitude = length(v);
  return magnitude === 0 ? [0, 0, 0] : scale(v, 1 / magnitude);
}

/** Position at an azimuth measured by atan2(z, x), with theta in radians. */
export function polar(radius, theta, y = 0) {
  return [radius * Math.cos(theta), y, radius * Math.sin(theta)];
}

/**
 * Reflect a propagation vector across a plane. The input normal need not be
 * normalized; the result preserves the incident vector's magnitude. A zero
 * normal leaves the direction unchanged.
 */
export function reflect(incoming, normal) {
  const n = normalize(normal);
  return sub(incoming, scale(n, 2 * dot(incoming, n)));
}

/**
 * Unit plane normal that reflects incoming toward outgoing. Both arguments
 * describe propagation, not vectors pointing back at the light source.
 * Equal directions have no unique bisector and return [0, 0, 0].
 */
export function mirrorNormal(incoming, outgoing) {
  return normalize(sub(normalize(incoming), normalize(outgoing)));
}

function orbitDirection(hourAngleDegrees, declination) {
  const hourAngle = hourAngleDegrees * DEG;
  const east = -Math.cos(declination) * Math.sin(hourAngle);
  const north = Math.sin(declination) * Math.cos(LATITUDE)
    - Math.cos(declination) * Math.cos(hourAngle) * Math.sin(LATITUDE);
  const up = Math.sin(declination) * Math.sin(LATITUDE)
    + Math.cos(declination) * Math.cos(hourAngle) * Math.cos(LATITUDE);
  return [east, up, -north];
}

/**
 * Unit direction TOWARD the sun, using the original prototype's fixed orbit:
 * latitude 35 degrees, declination -21 degrees. Negate for light propagation.
 */
export function sunDirection(hourAngleDegrees) {
  return orbitDirection(hourAngleDegrees, SUN_DECLINATION);
}

/**
 * Unit direction TOWARD the moon: latitude 35 degrees, declination +20 degrees,
 * with the original moon hour angle H - 180 degrees. Negate for propagation.
 */
export function moonDirection(hourAngleDegrees) {
  return orbitDirection(hourAngleDegrees - 180, MOON_DECLINATION);
}

/**
 * Intersect origin + t * dir with a plane. Returns { point, t } only for the
 * forward ray (t >= 0), otherwise null. Neither dir nor normal must be unit
 * length; t is a ray parameter, not necessarily a distance. Parallel,
 * coplanar and degenerate rays/planes return null.
 */
export function rayPlane(origin, dir, point, normal) {
  const directionLength = length(dir);
  const normalLength = length(normal);
  if (directionLength === 0 || normalLength === 0) return null;

  const n = scale(normal, 1 / normalLength);
  const denominator = dot(dir, n);
  if (Math.abs(denominator) <= EPSILON * directionLength) return null;

  const t = dot(sub(point, origin), n) / denominator;
  if (!Number.isFinite(t) || t < 0) return null;
  return { point: add(origin, scale(dir, t)), t };
}

/**
 * Project a silhouette along parallel light rays onto a wall plane.
 * When origin is null/undefined, vertices are already world-space points.
 * Otherwise each vertex is local and origin + vertex is its world position;
 * this function applies translation only, never rotation or scale.
 * lightDirection points in the direction light TRAVELS. The returned array
 * preserves vertex order and contains a point array or null per vertex.
 * Null means that vertex's forward ray does not reach the wall plane.
 */
export function projectShadow(vertices, origin, lightDirection, wallPoint, wallNormal) {
  return vertices.map((vertex) => {
    const worldPoint = origin == null ? vertex : add(origin, vertex);
    return rayPlane(worldPoint, lightDirection, wallPoint, wallNormal)?.point ?? null;
  });
}

/**
 * Closest point on segment a--b in the horizontal XZ plane. Returns clamped
 * segment parameter t, horizontal distance, and the segment's interpolated y.
 * A segment with no horizontal extent deterministically uses endpoint a.
 */
export function segmentDistanceXZ(point, a, b) {
  const dx = b[0] - a[0];
  const dz = b[2] - a[2];
  const squaredLength = dx * dx + dz * dz;
  const t = squaredLength === 0 ? 0 : clamp(
    ((point[0] - a[0]) * dx + (point[2] - a[2]) * dz) / squaredLength,
  );
  return {
    t,
    distance: Math.hypot(point[0] - lerp(a[0], b[0], t), point[2] - lerp(a[2], b[2], t)),
    y: lerp(a[1], b[1], t),
  };
}

/**
 * Choose theta's equivalent angle nearest a supplied unwrapped reference.
 * It is the caller's responsibility to select the correct accessible arc;
 * a wrapped atan2 result cannot distinguish multiple turns on its own.
 */
export function unwrapAngle(theta, reference) {
  return theta + TAU * Math.round((reference - theta) / TAU);
}

/**
 * Clamped linear position-to-orbit-phase map. Theta and both endpoints must
 * be UNWRAPPED radians: the interval may cross 2*pi or run in reverse. Phase
 * values share any consistent unit (the celestial functions use degrees).
 * A zero-length interval returns startPhase without a division by zero.
 */
export function uniformPhase(theta, startTheta, endTheta, startPhase, endPhase) {
  if (startTheta === endTheta) return startPhase;
  return lerp(startPhase, endPhase, clamp((theta - startTheta) / (endTheta - startTheta)));
}

/**
 * Phase inside an authored connection, independent of atan2 or floor height.
 * Default endPhase gives a constant phase, including across the rotunda axis.
 * A deliberate transition may supply endPhase and normalized path progress.
 */
export function connectionPhase(startPhase, endPhase = startPhase, progress = 0) {
  return lerp(startPhase, endPhase, clamp(progress));
}
