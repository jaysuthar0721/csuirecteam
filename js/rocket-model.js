import {
  Group, Mesh, MeshStandardMaterial, CylinderGeometry, LatheGeometry,
  ExtrudeGeometry, Shape, Vector2, TorusGeometry,
} from "./vendor/three.module.min.js";

// A visual concept, not flight CAD. Units and proportions are illustrative.
// The viewer supplies an optional texture; geometry also works without a DOM.
export function createRocket(bodyTexture = null) {
  const rocket = new Group();
  const green = new MeshStandardMaterial({ color: 0x1e4d2b, roughness: 0.34, metalness: 0.2 });
  const gold = new MeshStandardMaterial({ color: 0xc8c372, roughness: 0.32, metalness: 0.55 });
  const white = new MeshStandardMaterial({ color: 0xf1f3ed, roughness: 0.43, metalness: 0.12, map: bodyTexture });
  const metal = new MeshStandardMaterial({ color: 0xa0aaa5, roughness: 0.28, metalness: 0.8 });
  const graphite = new MeshStandardMaterial({ color: 0x151d19, roughness: 0.58, metalness: 0.25 });

  function part(name, geometry, material, y = 0) {
    const mesh = new Mesh(geometry, material);
    mesh.name = name;
    mesh.position.y = y;
    rocket.add(mesh);
    return mesh;
  }

  part("airframe", new CylinderGeometry(0.31, 0.31, 5.6, 64), white, -0.35);

  // Tangent-ogive silhouette with an explicit closed tip.
  const radius = 0.31;
  const length = 1.9;
  const rho = (radius * radius + length * length) / (2 * radius);
  const profile = [];
  for (let step = 0; step <= 48; step++) {
    const y = (step / 48) * length;
    const r = Math.max(0, Math.sqrt(rho * rho - y * y) + radius - rho);
    profile.push(new Vector2(step === 48 ? 0 : r, y));
  }
  part("nosecone", new LatheGeometry(profile, 64), green, 2.45);
  part("nose shoulder", new CylinderGeometry(0.316, 0.316, 0.075, 64), gold, 2.43);
  part("upper band", new CylinderGeometry(0.313, 0.313, 0.14, 64), green, 2.23);
  part("avionics band", new CylinderGeometry(0.313, 0.313, 0.07, 64), gold, -0.3);
  part("lower band", new CylinderGeometry(0.313, 0.313, 0.16, 64), green, -2.12);

  // Small separation seams, kept flush with the airframe.
  for (const y of [1.1, -0.45, -1.45]) {
    const seam = part("airframe seam", new TorusGeometry(0.311, 0.006, 6, 64), graphite, y);
    seam.rotation.x = Math.PI / 2;
  }

  const fin = new Shape();
  fin.moveTo(0.29, -1.92);
  fin.lineTo(0.97, -2.63);
  fin.lineTo(0.97, -3.08);
  fin.lineTo(0.29, -2.98);
  fin.closePath();
  const finGeometry = new ExtrudeGeometry(fin, { depth: 0.044, bevelEnabled: true, bevelSegments: 1, steps: 1, bevelSize: 0.006, bevelThickness: 0.006 });
  finGeometry.translate(0, 0, -0.022);
  for (let i = 0; i < 4; i++) {
    const mesh = part(`fin ${i + 1}`, finGeometry, green);
    mesh.rotation.y = (i * Math.PI) / 2;
  }
  part("motor retainer", new CylinderGeometry(0.313, 0.313, 0.13, 64), metal, -3.15);
  part("nozzle shell", new CylinderGeometry(0.2, 0.14, 0.18, 48, 1, true), graphite, -3.28);
  const lip = part("nozzle lip", new TorusGeometry(0.14, 0.016, 8, 48), metal, -3.37);
  lip.rotation.x = Math.PI / 2;

  return rocket;
}
