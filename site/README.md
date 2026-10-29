# Archived PCS launch preview

This directory preserves an earlier static preview. The current public website
is [proof-carrying-science-site](https://github.com/Tommaso-R-Marena/proof-carrying-science-site),
with [the beginner investigation](https://proof-carrying-science-site.marenatommaso.workers.dev/experience.html)
on the existing Cloudflare Workers hostname. Website changes and deployment gates
belong in that separate repository. Serving this directory does not reproduce the
current website, Commons backend or research/game pages.

To inspect this historical preview locally from the core repository root:

```sh
python -m http.server 8000 --bind 127.0.0.1 --directory site
```

Open `http://127.0.0.1:8000/` or `http://127.0.0.1:8000/demo.html`.
The browser demonstration is illustrative and does not replace the production
Lean authority or independent package replay.

Core, website and CertiForge source publication is already authorized. Long-term
branding, contact/domain choices and third-party rights remain separately scoped
requirements; a custom domain is optional. Preserve non-claims about biological,
clinical, GxP and regulatory validity. Current project instructions are in the
[root README](../README.md), not this archived preview.
