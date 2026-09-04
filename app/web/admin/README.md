# Admin frontend

The admin UI is a standalone module tree served under `/admin`.

- `app.js` bootstraps authentication, layout, and routing.
- `layout.js` owns the navigation structure.
- `router.js` maps shallow hash routes to feature modules.
- `api.js` is the shared admin HTTP boundary.
- `telegram.js`, `resources.js`, `scanner.js`, and `download.js` own their feature views.

The user-facing frontend at `/` and `/web` remains separate. Admin frontend modules keep the existing backend URLs; no `/v2` compatibility layer is introduced.

Internationalization is intentionally only an extension point for now; the UI remains Chinese-first without adding a locale framework.
