import type { ComfortFeature } from '../types/comfort';

/** Generate a unique client-side ID for a street segment based on street name + first coordinate. */
export const getSegmentId = (f: ComfortFeature): string => {
  const geom = f.geometry;
  if (geom.type === 'MultiLineString') {
    const firstCoord = geom.coordinates[0][0];
    return `${f.properties.street_name}#${firstCoord[0].toFixed(5)},${firstCoord[1].toFixed(5)}`;
  } else if (geom.type === 'LineString') {
    const firstCoord = geom.coordinates[0];
    return `${f.properties.street_name}#${firstCoord[0].toFixed(5)},${firstCoord[1].toFixed(5)}`;
  }
  return `${f.properties.street_name}#unknown`;
};
