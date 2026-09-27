/** Authored geometry seed. See docs/rotunda-geometry.md for required floor voids. */
import {
  DEG, add, sub, scale, dot, normalize, polar, sunDirection, moonDirection,
  reflect, mirrorNormal, uniformPhase, unwrapAngle, rayPlane, segmentDistanceXZ, length,
} from './math.js';

export const ROOF_PHASE = 44.2732;

export const WORLD = {
  outerRadius: 20,
  facadeRadius: 19,
  floorHeights: [0, 6, 12, 18],
  roofY: 24,
  ringRadii: [11.2, 14.8],
  columnRadius: 0.45,
  columns: Array.from({ length: 12 }, (_, index) => polar(10.5, (15 + 30 * index) * DEG, 0)),
  oculusRadius: 4.5,
  irisY: 23.3,
};

const d1ArrivalPhase = uniformPhase(55 * DEG, 15 * DEG, 345 * DEG, 0, 8);
const d2FootTheta = 205.76543982788593 * DEG;
const d2FootPhase = 17.249233446200527;
const d2ArrivalPhase = uniformPhase(165 * DEG, 55 * DEG, d2FootTheta, d1ArrivalPhase, d2FootPhase);
const d3ArrivalPhase = 39.45454545454545;

export const PHASE_FIELDS = [
  { startTheta: 15 * DEG, endTheta: 345 * DEG, startPhase: 0, endPhase: 8 },
  { startTheta: 55 * DEG, endTheta: d2FootTheta, startPhase: d1ArrivalPhase, endPhase: d2FootPhase },
  { startTheta: 165 * DEG, endTheta: 270 * DEG, startPhase: d2ArrivalPhase, endPhase: d3ArrivalPhase },
  { startTheta: 270 * DEG, endTheta: 304 * DEG, startPhase: d3ArrivalPhase, endPhase: ROOF_PHASE },
];

/** Keep the assigned departure field throughout a beam traversal, regardless of y. */
export function phaseAtPosition(fieldIndex, point) {
  const field = PHASE_FIELDS[fieldIndex];
  const theta = unwrapAngle(Math.atan2(point[2], point[0]), Math.PI);
  return uniformPhase(theta, field.startTheta, field.endTheta, field.startPhase, field.endPhase);
}

function solveDirectFoot(top, bottomY, fieldIndex, initialPhase) {
  let phase = initialPhase;
  let foot;
  for (let index = 0; index < 40; index += 1) {
    const source = sunDirection(phase);
    foot = sub(top, scale(source, (top[1] - bottomY) / source[1]));
    phase = phaseAtPosition(fieldIndex, foot);
  }
  return foot;
}

const d1Top = polar(14.8, 55 * DEG, 6);
const d2Top = polar(14.8, 165 * DEG, 12);
const mirror = polar(13, 230 * DEG, 14.5);
const d3Top = polar(15, 270 * DEG, 18);
const d3TargetPhase = phaseAtPosition(2, d3Top);

const roofSource = sunDirection(ROOF_PHASE);
const roofHorizontal = normalize([roofSource[0], 0, roofSource[2]]);
const roofRun = 6 * Math.hypot(roofSource[0], roofSource[2]) / roofSource[1];
const roofFootHeading = 304 * DEG;
const roofFootUnit = polar(1, roofFootHeading, 0);
const roofQuadraticB = 2 * roofRun * dot(roofFootUnit, roofHorizontal);
const roofQuadraticC = roofRun ** 2 - WORLD.oculusRadius ** 2;
// The near root reaches the sunward rim; the far root enters the opaque roof first.
const roofFootRadius = (-roofQuadraticB - Math.sqrt(roofQuadraticB ** 2 - 4 * roofQuadraticC)) / 2;
const roofFoot = polar(roofFootRadius, roofFootHeading, 18);
const roofTop = add(roofFoot, scale(roofSource, 6 / roofSource[1]));

export const DAY_RAMPS = [
  { id: 'D1', kind: 'direct', fieldIndex: 0, width: 2.8, top: d1Top,
    foot: solveDirectFoot(d1Top, 0, 0, 0) },
  { id: 'D2', kind: 'direct', fieldIndex: 1, width: 2.8, top: d2Top,
    foot: solveDirectFoot(d2Top, 6, 1, 14) },
  { id: 'D3', kind: 'reflected', fieldIndex: 2, width: 2.8, top: d3Top,
    foot: mirror, mirror,
    mirrorNormal: mirrorNormal(scale(sunDirection(d3TargetPhase), -1), sub(d3Top, mirror)) },
  { id: 'roof', kind: 'direct', fixedPhase: ROOF_PHASE, width: 2.8,
    foot: roofFoot, top: roofTop },
];

/**
 * Support at a candidate world XZ position. No horizontal carry is applied.
 * This is an optical centre-strip query, NOT a full wall/column occlusion test.
 */
export function rampSupport(ramp, point) {
  const phase = ramp.fixedPhase ?? phaseAtPosition(ramp.fieldIndex, point);
  const incoming = scale(sunDirection(phase), -1);
  const anchor = ramp.kind === 'reflected' ? ramp.mirror : ramp.top;
  const direction = ramp.kind === 'reflected' ? reflect(incoming, ramp.mirrorNormal) : incoming;
  const delta = sub(point, anchor);
  const horizontalSquared = direction[0] ** 2 + direction[2] ** 2;
  const t = (delta[0] * direction[0] + delta[2] * direction[2]) / horizontalSquared;
  const supportPoint = add(anchor, scale(direction, t));
  return {
    phase, t, supportPoint, supportY: supportPoint[1],
    lateralError: Math.hypot(supportPoint[0] - point[0], supportPoint[2] - point[2]),
  };
}

export function sampleRamp(ramp, count = 101) {
  return Array.from({ length: count }, (_, index) => {
    const progress = index / (count - 1);
    const point = add(scale(ramp.foot, 1 - progress), scale(ramp.top, progress));
    return { progress, point, ...rampSupport(ramp, point) };
  });
}

export function rampStats(ramp, count = 101) {
  const samples = sampleRamp(ramp, count);
  let maxSlopeDegrees = 0;
  for (let index = 1; index < samples.length; index += 1) {
    const a = samples[index - 1], b = samples[index];
    const run = Math.hypot(b.point[0] - a.point[0], b.point[2] - a.point[2]);
    maxSlopeDegrees = Math.max(maxSlopeDegrees,
      Math.atan2(Math.abs(b.supportY - a.supportY), run) / DEG);
  }
  return {
    startPhase: samples[0].phase,
    endPhase: samples.at(-1).phase,
    maxLateralError: Math.max(...samples.map((sample) => sample.lateralError)),
    maxHeightAdjustment: Math.max(...samples.map((sample) => Math.abs(sample.supportY - sample.point[1]))),
    maxSlopeDegrees,
    minColumnAxisDistance: Math.min(...WORLD.columns.map((column) =>
      segmentDistanceXZ(column, ramp.foot, ramp.top).distance)),
  };
}

const nightMirror = polar(19, 280 * DEG, 14.5);
const nightNormal = mirrorNormal(scale(moonDirection(105), -1), polar(1, 108 * DEG, 0));
const nightRevealDirection = reflect(scale(moonDirection(145), -1), nightNormal);
export const NIGHT_REFLECTION = {
  mirror: nightMirror,
  initialPhase: 105,
  initialRailHeading: 108 * DEG,
  revealPhase: 145,
  mirrorNormal: nightNormal,
  revealDirection: nightRevealDirection,
  target: rayPlane(nightMirror, nightRevealDirection, [0, 6, 0], [0, 1, 0]).point,
  maxBeamHalfWidth: 0.2,
  note: 'Revealing light, not a walkable beam. Requires an L2 floor light well.',
};

const RAY_EPSILON = 1e-10;

/** First hit distance against a closed, finite, vertical cylinder. Direction is unit. */
function cylinderEntry(origin, direction, maxLength, cylinder) {
  if (cylinder.type && cylinder.type !== 'cylinder') return null;
  const { x, z, radius, bottom, top } = cylinder;
  if (![x, z, radius, bottom, top].every(Number.isFinite) || radius < 0 || top < bottom) {
    throw new RangeError('Cylinder requires finite x, z, radius >= 0, bottom and top >= bottom.');
  }
  const ox = origin[0] - x, oz = origin[2] - z;
  const a = direction[0] ** 2 + direction[2] ** 2;
  const c = ox ** 2 + oz ** 2 - radius ** 2;
  let radialEnter = -Infinity, radialExit = Infinity;
  if (a <= RAY_EPSILON ** 2) {
    if (c > RAY_EPSILON) return null;
  } else {
    const b = 2 * (ox * direction[0] + oz * direction[2]);
    const discriminant = b * b - 4 * a * c;
    if (discriminant < -RAY_EPSILON) return null;
    const root = Math.sqrt(Math.max(0, discriminant));
    radialEnter = (-b - root) / (2 * a);
    radialExit = (-b + root) / (2 * a);
  }

  let heightEnter = -Infinity, heightExit = Infinity;
  if (Math.abs(direction[1]) <= RAY_EPSILON) {
    if (origin[1] < bottom || origin[1] > top) return null;
  } else {
    const aY = (bottom - origin[1]) / direction[1];
    const bY = (top - origin[1]) / direction[1];
    heightEnter = Math.min(aY, bY);
    heightExit = Math.max(aY, bY);
  }

  const entry = Math.max(0, radialEnter, heightEnter);
  const exit = Math.min(maxLength, radialExit, heightExit);
  return entry <= exit + RAY_EPSILON && entry <= maxLength ? entry : null;
}

/**
 * Illuminated intervals of one parallel-light ray, measured in metres from
 * origin along normalized direction. A closed opaque cylinder blocks every
 * point beyond its FIRST hit; light does not resume after the far surface.
 * Consequently returns [] or one [{start: 0, end}] interval.
 *
 * Cylinders use the architecture obstacle format:
 * {type:'cylinder', x, z, radius, bottom, top}. Other obstacle types are ignored
 * and require a separate mesh/box occlusion pass. Inside/on an obstacle gives
 * no illuminated interval. The input arrays and obstacles are not mutated.
 */
export function clipRayIntervals(origin, direction, maxLength, cylinders = []) {
  const magnitude = length(direction);
  if (!Number.isFinite(maxLength) || maxLength <= 0 || !Number.isFinite(magnitude) || magnitude === 0) return [];
  const unit = scale(direction, 1 / magnitude);
  let end = maxLength;
  for (const cylinder of cylinders) {
    const hit = cylinderEntry(origin, unit, maxLength, cylinder);
    if (hit !== null) end = Math.min(end, hit);
  }
  return end > RAY_EPSILON ? [{ start: 0, end }] : [];
}

/**
 * Divide a finite optical support plane into clipped narrow rectangular cells.
 * `top` is the emitting aperture/mirror point; `direction` points along light
 * propagation. `bottom` is the target Y plane and may also be above `top` for
 * an upward reflection. Start/end are METRES along each cell's unit ray.
 *
 * Each cell's cylinder radii are conservatively inflated by half its width.
 * This clips the WHOLE rectangle before an edge can penetrate a column, not
 * merely the ray through its centre. It can overclip slightly, up to the cell
 * scale; increasing widthSegments improves that bound. Cylinder heights are
 * unchanged because the width axis is horizontal.
 *
 * Render and collision MUST use these same startPoint/endPoint/width quads.
 * Do not keep the original uncut wide support rectangle enabled underneath.
 * This function handles downstream cylinders only; the aperture/mirror still
 * needs its incoming-light test, plus floor, wall and box occlusion checks.
 */
export function solarBeamCells(top, direction, bottom, width, obstacles = [], widthSegments = 12) {
  if (!Number.isFinite(widthSegments) || widthSegments < 1) throw new RangeError('widthSegments must be at least 1.');
  const magnitude = length(direction);
  if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(bottom) || !Number.isFinite(magnitude) || magnitude === 0) return [];
  const unit = scale(direction, 1 / magnitude);
  if (Math.abs(unit[1]) <= RAY_EPSILON) return [];
  const maxLength = (bottom - top[1]) / unit[1];
  if (maxLength <= RAY_EPSILON) return [];
  const horizontalLength = Math.hypot(unit[0], unit[2]);
  const side = horizontalLength > RAY_EPSILON
    ? [-unit[2] / horizontalLength, 0, unit[0] / horizontalLength]
    : [1, 0, 0];
  const count = Math.floor(widthSegments);
  const cellWidth = width / count;
  const cylinders = obstacles.filter((obstacle) => !obstacle.type || obstacle.type === 'cylinder')
    .map((obstacle) => ({ ...obstacle, radius: obstacle.radius + cellWidth / 2 }));
  const cells = [];
  for (let index = 0; index < count; index += 1) {
    const xoffset = -width / 2 + (index + 0.5) * cellWidth;
    const origin = add(top, scale(side, xoffset));
    const intervals = clipRayIntervals(origin, unit, maxLength, cylinders);
    if (intervals.length === 0) continue;
    const { start, end } = intervals[0];
    cells.push({
      xoffset, width: cellWidth, start, end, origin, direction: [...unit],
      startPoint: add(origin, scale(unit, start)),
      endPoint: add(origin, scale(unit, end)),
      clipped: end < maxLength - RAY_EPSILON,
    });
  }
  return cells;
}
