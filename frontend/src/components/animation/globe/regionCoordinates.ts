/**
 * Maps region/country names to approximate x,y positions on an 800×400 SVG
 * world map using equirectangular projection.
 *
 * x: 0 (180°W) → 800 (180°E)
 * y: 0 (90°N) → 400 (90°S)
 */

export interface RegionPoint {
  x: number
  y: number
  label: string
}

export const REGION_COORDS: Record<string, RegionPoint> = {
  // East Asia
  China:          { x: 640, y: 160, label: 'China' },
  Japan:          { x: 700, y: 155, label: 'Japan' },
  'South Korea':  { x: 680, y: 155, label: 'South Korea' },
  Taiwan:         { x: 670, y: 180, label: 'Taiwan' },

  // Southeast Asia
  Vietnam:        { x: 650, y: 195, label: 'Vietnam' },
  Thailand:       { x: 635, y: 200, label: 'Thailand' },
  Indonesia:      { x: 660, y: 245, label: 'Indonesia' },
  Philippines:    { x: 680, y: 205, label: 'Philippines' },
  Malaysia:       { x: 645, y: 225, label: 'Malaysia' },
  Cambodia:       { x: 645, y: 205, label: 'Cambodia' },
  Myanmar:        { x: 625, y: 190, label: 'Myanmar' },

  // South Asia
  India:          { x: 585, y: 195, label: 'India' },
  Pakistan:       { x: 560, y: 175, label: 'Pakistan' },
  Bangladesh:     { x: 605, y: 190, label: 'Bangladesh' },
  'Sri Lanka':    { x: 590, y: 220, label: 'Sri Lanka' },
  Nepal:          { x: 590, y: 180, label: 'Nepal' },

  // Middle East
  Turkey:         { x: 470, y: 155, label: 'Turkey' },
  UAE:            { x: 515, y: 185, label: 'UAE' },
  'Saudi Arabia': { x: 500, y: 185, label: 'Saudi Arabia' },
  Iran:           { x: 520, y: 165, label: 'Iran' },
  Israel:         { x: 475, y: 170, label: 'Israel' },
  Jordan:         { x: 475, y: 170, label: 'Jordan' },

  // Africa
  Egypt:          { x: 462, y: 185, label: 'Egypt' },
  Morocco:        { x: 390, y: 170, label: 'Morocco' },
  'South Africa': { x: 460, y: 310, label: 'South Africa' },
  Nigeria:        { x: 420, y: 220, label: 'Nigeria' },
  Kenya:          { x: 475, y: 245, label: 'Kenya' },
  Ethiopia:       { x: 480, y: 225, label: 'Ethiopia' },
  Tunisia:        { x: 425, y: 160, label: 'Tunisia' },
  Ghana:          { x: 400, y: 225, label: 'Ghana' },

  // Europe
  Germany:        { x: 425, y: 130, label: 'Germany' },
  Italy:          { x: 432, y: 148, label: 'Italy' },
  France:         { x: 410, y: 138, label: 'France' },
  UK:             { x: 400, y: 122, label: 'UK' },
  Spain:          { x: 395, y: 152, label: 'Spain' },
  Poland:         { x: 440, y: 128, label: 'Poland' },
  Portugal:       { x: 385, y: 152, label: 'Portugal' },
  Netherlands:    { x: 415, y: 124, label: 'Netherlands' },
  Romania:        { x: 455, y: 140, label: 'Romania' },
  Greece:         { x: 450, y: 155, label: 'Greece' },

  // Americas
  USA:            { x: 175, y: 155, label: 'United States' },
  Canada:         { x: 175, y: 120, label: 'Canada' },
  Mexico:         { x: 150, y: 190, label: 'Mexico' },
  Brazil:         { x: 260, y: 270, label: 'Brazil' },
  Colombia:       { x: 210, y: 225, label: 'Colombia' },
  Argentina:      { x: 240, y: 310, label: 'Argentina' },
  Chile:          { x: 225, y: 305, label: 'Chile' },
  Peru:           { x: 215, y: 260, label: 'Peru' },
  Guatemala:      { x: 160, y: 205, label: 'Guatemala' },

  // Oceania
  Australia:      { x: 710, y: 300, label: 'Australia' },
  'New Zealand':  { x: 755, y: 330, label: 'New Zealand' },
}

// Aliases for fuzzy matching
const ALIASES: Record<string, string> = {
  'United States': 'USA',
  'United Kingdom': 'UK',
  'Hong Kong': 'China',
  'Macau': 'China',
  'Republic of Korea': 'South Korea',
  'Korea': 'South Korea',
  'Türkiye': 'Turkey',
  'Viet Nam': 'Vietnam',
  'Burma': 'Myanmar',
  'Emirates': 'UAE',
  'KSA': 'Saudi Arabia',
}

/** Resolve a region name (fuzzy) to a coordinate point */
export function resolveRegion(name: string): RegionPoint | null {
  // Direct match
  if (REGION_COORDS[name]) return REGION_COORDS[name]

  // Alias match
  const aliased = ALIASES[name]
  if (aliased && REGION_COORDS[aliased]) return REGION_COORDS[aliased]

  // Fuzzy: check if name contains a known region
  const lower = name.toLowerCase()
  for (const [key, point] of Object.entries(REGION_COORDS)) {
    if (lower.includes(key.toLowerCase())) return point
  }

  return null
}

/** Center point on the SVG — "Procurement AI HQ" origin for arcs */
export const CENTER_POINT = { x: 400, y: 200 }
