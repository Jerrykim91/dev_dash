'use strict';

// Dimensions and base scene-width percentages keep bounds and rendering in sync.
const ActorAssets = Object.freeze({
  developer: Object.freeze({ id: 'developer', width: 512, height: 640, baseWidth: 22, duration: .96, frames: 4 }),
  cat: Object.freeze({ id: 'cat-layer', width: 512, height: 288, baseWidth: 13, duration: 2.4, frames: 4 }),
  laptop: Object.freeze({ id: 'laptop', width: 640, height: 336, baseWidth: 17, duration: 0, frames: 1 }),
  plantUpperLeft: Object.freeze({ id: 'plant-upper-left', width: 222, height: 433, baseWidth: 13.277511961722489, duration: 0, frames: 1 }),
  plantDeskLeft: Object.freeze({ id: 'plant-desk-left', width: 191, height: 205, baseWidth: 11.423444976076555, duration: 0, frames: 1 }),
  plantFloorLeft: Object.freeze({ id: 'plant-floor-left', width: 252, height: 223, baseWidth: 15.07177033492823, duration: 0, frames: 1 }),
  plantDeskRight: Object.freeze({ id: 'plant-desk-right', width: 177, height: 210, baseWidth: 10.586124401913874, duration: 0, frames: 1 }),
  plantHangingRight: Object.freeze({ id: 'plant-hanging-right', width: 170, height: 436, baseWidth: 10.167464114832537, duration: 0, frames: 1 }),
  plantSideRight: Object.freeze({ id: 'plant-side-right', width: 152, height: 221, baseWidth: 9.090909090909092, duration: 0, frames: 1 }),
  deskBooks: Object.freeze({ id: 'desk-books', width: 950, height: 520, baseWidth: 9, duration: 0, frames: 1 }),
  deskLantern: Object.freeze({ id: 'desk-lantern', width: 650, height: 760, baseWidth: 5, duration: 0, frames: 1 }),
  deskPencils: Object.freeze({ id: 'desk-pencils', width: 650, height: 1200, baseWidth: 4.3, duration: 0, frames: 1 }),
  deskMug: Object.freeze({ id: 'desk-mug', width: 760, height: 700, baseWidth: 5.2, duration: 0, frames: 1 })
});
