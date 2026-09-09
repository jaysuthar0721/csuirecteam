// Progressive enhancement: keep the real launch photo until a frame renders.
const stage = document.getElementById("rocket-stage");
const canvas = document.getElementById("rocket-canvas");
const controls = document.getElementById("rocket-controls");
const help = document.getElementById("rocket-help");
const label = document.getElementById("rocket-label");
const subtitle = document.getElementById("rocket-subtitle");

async function startViewer() {
  let renderer;
  let dispose = () => {};
  const showPhoto = () => {
    dispose();
    // Do not strand keyboard focus on a control that is about to disappear.
    const wasFocused = document.activeElement === canvas || controls.contains(document.activeElement);
    stage.classList.remove("is-ready");
    canvas.hidden = true;
    controls.hidden = true;
    help.hidden = true;
    label.textContent = "Ram Rocketry in flight";
    subtitle.textContent = "3D view unavailable · Launch photograph";
    if (wasFocused) {
      stage.tabIndex = -1;
      stage.focus();
    }
  };

  try {
    const [THREE, { createRocket }] = await Promise.all([
      import("./vendor/three.module.min.js"),
      import("./rocket-model.js"),
    ]);

    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "low-power" });
    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.4;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 80);
    const presentation = new THREE.Group();
    presentation.rotation.set(0.1, 0, -0.34);
    scene.add(presentation);

    // Paint and lettering are a texture on the 3D airframe, not a page overlay.
    const paint = document.createElement("canvas");
    paint.width = 512;
    paint.height = 2048;
    const context = paint.getContext("2d");
    if (!context) throw new Error("Canvas textures are unavailable");
    context.fillStyle = "#f1f3ed";
    context.fillRect(0, 0, paint.width, paint.height);
    for (const x of [100, 356]) {
      context.fillStyle = "#1e4d2b";
      context.fillRect(x - 52, 0, 104, 1540);
      context.fillStyle = "#c8c372";
      context.fillRect(x - 58, 0, 4, 1540);
      context.fillStyle = "#ffffff";
      context.textAlign = "center";
      context.font = "700 76px Arial, sans-serif";
      [..."RAM"].forEach((letter, i) => context.fillText(letter, x, 240 + i * 100));
      context.font = "700 51px Arial, sans-serif";
      [..."ROCKETRY"].forEach((letter, i) => context.fillText(letter, x, 640 + i * 76));
      context.fillStyle = "#c8c372";
      context.font = "700 34px Arial, sans-serif";
      context.fillText("CSU", x, 1430);
    }
    const texture = new THREE.CanvasTexture(paint);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
    const rocket = createRocket(texture);
    rocket.position.y = -0.49;
    rocket.rotation.y = -0.95;
    presentation.add(rocket);

    scene.add(new THREE.HemisphereLight(0xf1fff4, 0x365442, 2.4));
    const key = new THREE.DirectionalLight(0xffffff, 4.3);
    key.position.set(-3, 6, 5);
    const fill = new THREE.DirectionalLight(0xc8d9ff, 2);
    fill.position.set(5, 0, 2);
    const rim = new THREE.DirectionalLight(0xf2dca0, 3.8);
    rim.position.set(1, 3, -4);
    scene.add(key, fill, rim);

    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const rotateButton = document.getElementById("rocket-rotate");
    const resetButton = document.getElementById("rocket-reset");
    const events = new AbortController();
    const on = (target, type, callback, options = {}) => target.addEventListener(type, callback, { ...options, signal: events.signal });
    let autoRotate = !motion.matches;
    let visible = false;
    let dragging = false;
    let pointerId = null;
    let lastX = 0;
    let lastFrame = 0;
    let destroyed = false;

    function render() {
      if (!destroyed) renderer.render(scene, camera);
    }
    function animate(time) {
      const delta = lastFrame ? Math.min((time - lastFrame) / 1000, 0.05) : 0;
      lastFrame = time;
      rocket.rotation.y += delta * 0.18;
      render();
    }
    function updateAnimation() {
      if (destroyed) return;
      lastFrame = 0;
      renderer.setAnimationLoop(autoRotate && visible && !document.hidden && !dragging ? animate : null);
      rotateButton.setAttribute("aria-pressed", String(autoRotate));
    }
    function stopAutoRotate() {
      autoRotate = false;
      updateAnimation();
    }
    function resize() {
      if (destroyed) return;
      const width = Math.max(1, stage.clientWidth);
      const height = Math.max(1, stage.clientHeight);
      camera.aspect = width / height;
      // Frame the whole silhouette with room for captions on narrow phones.
      const verticalSpan = Math.max(9.4, 5.2 / camera.aspect);
      camera.position.set(0, 0.05, verticalSpan / (2 * Math.tan(THREE.MathUtils.degToRad(16))));
      camera.lookAt(0, 0.05, 0);
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
      render();
    }
    const resizeObserver = new ResizeObserver(resize);
    const visibilityObserver = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      updateAnimation();
    }, { threshold: 0 });

    dispose = () => {
      if (destroyed) return;
      destroyed = true;
      renderer.setAnimationLoop(null);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();
      events.abort();
      // Shared fin geometry and materials must each be released once.
      const geometries = new Set();
      const materials = new Set();
      rocket.traverse((object) => {
        if (object.geometry) geometries.add(object.geometry);
        if (object.material) materials.add(object.material);
      });
      geometries.forEach((geometry) => geometry.dispose());
      materials.forEach((material) => material.dispose());
      texture.dispose();
      renderer.dispose();
    };

    on(rotateButton, "click", () => {
      autoRotate = !autoRotate;
      updateAnimation();
    });
    on(resetButton, "click", () => {
      rocket.rotation.y = -0.95;
      presentation.rotation.set(0.1, 0, -0.34);
      render();
    });
    on(canvas, "pointerdown", (event) => {
      if (!event.isPrimary || event.button !== 0) return;
      pointerId = event.pointerId;
      dragging = true;
      lastX = event.clientX;
      stopAutoRotate();
      canvas.setPointerCapture(pointerId);
      canvas.classList.add("is-dragging");
    });
    on(canvas, "pointermove", (event) => {
      if (!dragging || event.pointerId !== pointerId) return;
      rocket.rotation.y += (event.clientX - lastX) * 0.012;
      lastX = event.clientX;
      render();
    });
    const endDrag = (event) => {
      if (event.pointerId !== pointerId) return;
      dragging = false;
      pointerId = null;
      canvas.classList.remove("is-dragging");
      updateAnimation();
    };
    on(canvas, "pointerup", endDrag);
    on(canvas, "pointercancel", endDrag);
    on(canvas, "lostpointercapture", endDrag);
    on(canvas, "keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", " "].includes(event.key)) return;
      event.preventDefault();
      if (event.key === " ") {
        autoRotate = !autoRotate;
        updateAnimation();
        return;
      }
      stopAutoRotate();
      if (event.key === "Home") {
        rocket.rotation.y = -0.95;
        presentation.rotation.x = 0.1;
      } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
        rocket.rotation.y += event.key === "ArrowLeft" ? -0.18 : 0.18;
      } else {
        presentation.rotation.x = THREE.MathUtils.clamp(presentation.rotation.x + (event.key === "ArrowUp" ? -0.08 : 0.08), -0.35, 0.35);
      }
      render();
    });
    on(motion, "change", () => { if (motion.matches) stopAutoRotate(); });
    on(document, "visibilitychange", updateAnimation);
    on(canvas, "webglcontextlost", (event) => { event.preventDefault(); showPhoto(); });
    // Keep the viewer intact for back/forward cache; release it on full unload.
    on(window, "pagehide", (event) => {
      if (event.persisted) renderer.setAnimationLoop(null);
      else dispose();
    });
    on(window, "pageshow", () => { resize(); updateAnimation(); });

    resize();
    canvas.hidden = false;
    stage.classList.add("is-ready");
    controls.hidden = false;
    help.hidden = false;
    label.textContent = "Ram Rocketry / 3D";
    subtitle.textContent = "Concept vehicle · Illustrative geometry";
    resizeObserver.observe(stage);
    visibilityObserver.observe(stage);
    updateAnimation();
  } catch (error) {
    showPhoto();
    renderer?.dispose();
    console.warn("Rocket viewer unavailable; showing launch photograph.", error);
  }
}

if (stage && canvas) {
  // Avoid downloading the 3D library on mobile until the viewer is near view.
  if ("IntersectionObserver" in window) {
    const loader = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      loader.disconnect();
      startViewer();
    }, { rootMargin: "160px" });
    loader.observe(stage);
  } else {
    startViewer();
  }
}
