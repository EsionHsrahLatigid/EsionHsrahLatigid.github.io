# EHL Web

Static GitHub Pages starter for the EsionHsrahLatigid web presence.

## What is here

- `site/` contains the deployable static site.
- `.github/workflows/deploy.yml` publishes `site/` to GitHub Pages with Actions.

## GitHub Pages setup

1. Create a GitHub repository for this folder.
2. Push `main`.
3. In repository settings, set Pages source to GitHub Actions.
4. Let the workflow deploy the `site/` artifact.

## URL

For a GitHub.com project site, the default URL is:

`https://<owner>.github.io/<repository>`

If the repository is private, Pages availability and visibility depend on the plan and organization settings.

## Local preview

Serve the `site/` directory with any static server, for example:

`python3 -m http.server 8000 -d site`

Then open `http://localhost:8000`.
