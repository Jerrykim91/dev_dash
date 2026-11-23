/**
 * 화면 배율 정책 (HiDPI·4K, docs/visual-standard-v2.md §12)
 * - 캔버스는 장치 픽셀로 그린다: 게임 크기 = CSS 크기 × DPR, 표시 배율 = 1/DPR (Phaser Scale.NONE + zoom).
 * - 카메라 zoom = 장치 픽셀 / 월드 픽셀. 픽셀 아트가 고르게 보이도록 항상 정수(확대) 또는 1/n(전체 보기).
 * - 기본 배율은 화면 크기에 맞춰 보이는 월드 폭이 DEFAULT_VIEW_WORLD_WIDTH 안팎이 되는 정수로 고른다.
 */
export const MAX_DPR = 3;
export const DEFAULT_VIEW_WORLD_WIDTH = 1400;
export const devicePixelRatioOf = (w?: {devicePixelRatio?: number}) => Math.min(MAX_DPR, Math.max(1, w?.devicePixelRatio || 1));
export const DPR = devicePixelRatioOf(typeof window === 'undefined' ? undefined : window);

/** 가장 가까운 픽셀 정렬 배율(정수 또는 1/2, 1/3, 1/4). */
export function pixelZoom(z: number): number {
  if (!(z > 0)) return 1;
  if (z >= 1) return Math.max(1, Math.round(z));
  return 1 / Math.min(4, Math.max(1, Math.round(1 / z)));
}

/** 주어진 값을 넘지 않는 가장 큰 픽셀 정렬 배율(화면에 다 들어가야 하는 전체 보기용). */
export function fitPixelZoom(z: number): number {
  if (!(z > 0)) return 1 / 4;
  if (z >= 1) return Math.floor(z);
  return 1 / Math.min(4, Math.ceil(1 / z));
}

/**
 * 그림 밀도(docs/visual-standard-v2.md §14): HD 그림은 월드 1px에 그림 2px. 카메라 배율 z에서 그림 1px = 장치 z/2 px.
 * - 기본 배율이 홀수 정수(≥3)면 하나 위 짝수로 올려 그림 픽셀이 장치 정수 픽셀에 맞게 한다(3 → 4: 크기 차이가 가장 작은 쪽).
 * - z < 2(그림 1px < 장치 1px)에서는 선형 필터: 정확히 1/2 축소면 2×2 평균이 되어 1배 그림과 같은 결과.
 */
export const ART_DENSITY = 2;
export function preferArtAligned(z: number): number {
  return z >= 3 && Number.isInteger(z) && z % ART_DENSITY !== 0 ? z + 1 : z;
}
export const artFilterLinear = (zoom: number) => zoom < ART_DENSITY;

export function zoomLevels(min: number, max: number): number[] {
  const levels = [1 / 4, 1 / 3, 1 / 2].filter(l => l >= min - 1e-9);
  for (let z = 1; z <= max + 1e-9; z++) if (z >= min - 1e-9) levels.push(z);
  return levels.length ? levels : [pixelZoom(min)];
}

/** 휠·핀치 한 단계: 현재 배율에서 위(dir=1)·아래(dir=-1) 픽셀 정렬 배율로. */
export function stepZoom(current: number, dir: 1 | -1, min: number, max: number): number {
  const levels = zoomLevels(min, max);
  if (dir > 0) return levels.find(l => l > current + 1e-6) ?? levels[levels.length - 1];
  return [...levels].reverse().find(l => l < current - 1e-6) ?? levels[0];
}
