# PCS launch-preview website

The current launch-preview site is intentionally static so it can be hosted almost anywhere.

## Preview locally

From the repository root:

```bash
python -m http.server 8000 --directory site
```

Then open:

```text
http://localhost:8000/
```

The interactive demo is:

```text
http://localhost:8000/demo.html
```

## Scope

The browser demo is illustrative. It mirrors the PCS assurance model but does not replace the production Python verifier, real Ed25519 verification, or Lean kernel.

Before making the site public:

1. review company/name/trademark choice;
2. add a contact route;
3. decide whether the repository/site itself should be public;
4. remove the "private design-partner alpha" label only after an external pilot exists;
5. preserve all explicit non-claims around biological, clinical, GxP, and regulatory validity.

## Hosting

The files are deployable to GitHub Pages, Cloudflare Pages, Vercel, Netlify, or any static web host. GitHub Actions runner availability is currently unreliable on this repository, so local preview is the deterministic path today.
