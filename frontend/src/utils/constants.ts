/** Default map center: geographic center of the contiguous US */
export const DEFAULT_CENTER: [number, number] = [39.8283, -98.5795];
export const DEFAULT_ZOOM = 5;

/** CARTO dark basemap */
export const TILE_URL =
  'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>';
export const TILE_SUBDOMAINS = 'abcd';
export const TILE_MAX_ZOOM = 19;

/** Default maximum segments per request */
export const DEFAULT_MAX_SEGMENTS = 200;
