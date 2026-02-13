# App Routes (`frontend/src/app/`)

## Files
- `layout.tsx`: root document shell and metadata.
- `page.tsx`: landing experience.
- `product/page.tsx`: product workspace route.
- `globals.css`, `tamkin-landing.css`: global and landing-specific styles.

## Refactor Guidance
- Keep route-level files thin; move reusable logic to components/hooks.
- Preserve feature-flag and testing entry behavior.
- Keep global styles token-aligned with Tailwind theme.
