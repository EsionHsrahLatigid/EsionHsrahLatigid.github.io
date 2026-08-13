# EsionHsrahLatigid Web

Official static web presence and public plugin catalog for EsionHsrahLatigid.
The site follows the canonical `ehl-design` system: monochrome, hard-edged,
compact, serif-led identity with controlled structural noise.

## Local preview

```sh
python3 -m http.server 4173 -d site
```

Open <http://localhost:4173/>.

## Verification

```sh
python3 scripts/verify_site.py
node --check site/app.js
xmllint --noout site/sitemap.xml site/assets/logos/*.svg site/assets/social/*.svg
```

## Deployment

Pushes to `main` deploy the `site/` directory through GitHub Actions to:

<https://esionhsrahlatigid.github.io/>

The workflow uses the supported GitHub Pages artifact and deployment actions.

## Brand assets

The SVG files under `site/assets/logos/` are canonical EHL identity assets.
Repository visibility does not grant a public logo license; reuse requires
permission from EsionHsrahLatigid.
