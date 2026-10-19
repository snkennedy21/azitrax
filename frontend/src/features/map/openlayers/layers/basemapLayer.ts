import TileLayer from "ol/layer/Tile.js";
import ImageTile from "ol/source/ImageTile.js";

export function createBasemapLayer(apiKey: string) {
  return new TileLayer({
    source: new ImageTile({
      attributions:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
      url: `https://{a-d}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${encodeURIComponent(apiKey)}`,
    }),
  });
}
