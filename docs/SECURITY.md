# Security Boundaries

## Trust Model

- Browser input, URL state, cookies, headers, provider responses, uploaded
  data, and external references are untrusted.
- User and tenant identity are resolved server-side. Request JSON never chooses
  the authoritative tenant.
- Authorization is enforced in both service and repository layers.
- Public contracts exclude credentials, session tokens, CSRF values, private
  paths, raw provider bodies, and private notes.

## Web Mutations

- Use same-origin routes, bounded bodies, allowlisted redirects, CSRF checks,
  secure cookie attributes, optimistic concurrency, and generic errors.
- Local/test identity is process-local and must never be presented as hosted
  or production authentication.
- Optional Supabase tables in an exposed schema require RLS and least privilege.

## Product Boundary

The product is research-only. Authentication does not authorize broker action,
trading, recommendation, autonomous execution, or payment collection.
