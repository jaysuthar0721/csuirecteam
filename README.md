# Ram Rocketry — CSU Website (Draft)

Draft website for **Ram Rocketry**, the collegiate high-power rocketry organization at Colorado State University. Ram Rocketry is the organization at the center of the site; IREC, the Liquid Propulsion Project, and USLI (via our former team, [Ram Launch Initiative](https://www.engr.colostate.edu/organizations/ramlaunch/)) are its sub-programs, alongside the club's year-round engineering projects.

Built as plain HTML/CSS/JS (no build step) so it can be uploaded directly or served with GitHub Pages.

## Pages

- `index.html` — Home, with an overview of all four programs
- `about.html` — Mission, history (USLI → IREC → Liquid Propulsion), skills
- `projects.html` — Programs & Projects hub: links to IREC/USLI, plus the engineering projects (Active Fin Stabilization, Two-Stage, Glider Rocket, Liquid Propulsion)
- `irec.html` — IREC campaign, our current competition focus
- `liquid-propulsion.html` — The Liquid Propulsion Project: vision, roadmap, and engine specs
- `usli.html` — USLI/Ram Launch Initiative history, with a jump link to CSU's official page
- `sponsors.html` — Funding needs and sponsorship tiers
- `contact.html` — Contact info and message form

## Structure

```
/css/style.css     Design system + all page styles (CSU green/gold theme)
/js/main.js        Mobile nav toggle + active nav highlighting
/js/rocket-viewer.js  Homepage WebGL viewer, controls, and photo fallback
/js/rocket-model.js   Procedural concept rocket geometry (not flight CAD)
/js/vendor/          Three.js r180 ES modules and MIT license
/css/home.css        Homepage layout, program cards, and rocket stage
/assets/           Logo (logo.png), favicon (favicon.png)
/assets/photos/    Real team/launch/build photos used as hero and page-banner backgrounds
```

## Deploying with GitHub Pages

1. Push this repo to GitHub.
2. Go to **Settings → Pages**.
3. Set the source to the branch containing these files (root directory).
4. The site will publish at `https://<username>.github.io/<repo>/`.

## Content sources

Copy is drawn from Ram Rocketry's internal sponsorship packages, team overview docs, and funding materials (Google Drive: *Ram Rocketry / IREC*), plus public info about the club's former NASA USLI program. Hero and page-banner photos are real team/launch/build photography (see `/assets/photos/`); the logo and favicon are the club's actual mark, not a placeholder.

## Homepage rocket

The homepage has a locally rendered, interactive 3D concept rocket in CSU colors. Its geometry is illustrative, not a representation of finalized flight hardware. Drag horizontally or focus the canvas and use the arrow keys to rotate; Home resets the pose, and Space toggles automatic rotation. The visible controls also toggle rotation and reset the view.

The viewer loads when near the viewport, caps rendering resolution, and suspends animation offscreen or while the tab is hidden. Automatic rotation starts disabled when reduced motion is requested. The existing launch photograph stays visible when JavaScript, the 3D module, or WebGL is unavailable. Other pages do not load Three.js.

Three.js **r180 (0.180.0)** is vendored from the [upstream release](https://github.com/mrdoob/three.js/tree/r180/build), with its [MIT license](js/vendor/three.LICENSE.txt). Both `three.module.min.js` and its relative dependency `three.core.min.js` must be deployed together. No package install or build is needed. Serve the repository over HTTP (including GitHub Pages) so browsers can load JavaScript modules; opening `index.html` as a local file may show the photograph instead.
