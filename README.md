# Ram Rocketry — CSU Website (Draft)

Draft website for **Ram Rocketry**, the collegiate high-power rocketry organization at Colorado State University. The site showcases the club as an active, flying organization and covers its transition from NASA's University Student Launch Initiative (USLI) — via our former team, [Ram Launch Initiative](https://www.engr.colostate.edu/organizations/ramlaunch/) — to the International Rocket Engineering Competition (IREC) at Midland, Texas.

Built as plain HTML/CSS/JS (no build step) so it can be uploaded directly or served with GitHub Pages.

## Pages

- `index.html` — Home
- `about.html` — Mission, history, skills
- `projects.html` — Active Fin Stabilization, Two-Stage, Glider Rocket, Liquid Propulsion
- `irec.html` — IREC campaign and the USLI → IREC transition story
- `sponsors.html` — Funding needs and sponsorship tiers
- `contact.html` — Contact info and message form

## Structure

```
/css/style.css     Design system + all page styles (CSU green/gold theme)
/js/main.js        Mobile nav toggle + active nav highlighting
/assets/           Logo, favicon, and hero illustration (SVG)
```

## Deploying with GitHub Pages

1. Push this repo to GitHub.
2. Go to **Settings → Pages**.
3. Set the source to the branch containing these files (root directory).
4. The site will publish at `https://<username>.github.io/<repo>/`.

## Content sources

Copy is drawn from Ram Rocketry's internal sponsorship packages, team overview docs, and funding materials (Google Drive: *Ram Rocketry / IREC*), plus public info about the club's former NASA USLI program. Placeholder avatars are used for the team page — swap in real photos before going live. Real launch/build photography from the team's Drive can also replace the SVG hero art once selected.
