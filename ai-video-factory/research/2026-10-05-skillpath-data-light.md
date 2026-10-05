# Research: SkillPath Africa promo — skillpath-data-light (owner's own product; promotional)

Every claim is checked against the SkillPath Africa codebase (homepage claims rule in its README:
"a claim here must be checkable against the running site").

| Claim | Source in the app repo |
|---|---|
| Short video lessons in coding, freelancing, design, marketing and everyday work tools | lib/i18n.ts home.heroSubtitle |
| First lesson of every path free, no account, no card | README "Homepage claims" (lessons.is_free_preview) |
| KSh 500 a path, paid once, no subscription, keep it for life | lib/pricing.ts SINGLE_COURSE_PRICE; i18n home.value.payOnceBody |
| Bundle: any 10 paths for KSh 1,000, buyer chooses which ten | lib/pricing.ts BUNDLE_PRICE / BUNDLE_COURSE_COUNT; README bundle section |
| Five areas: Business & Freelancing, Marketing & Growth, Design & Creative, Tech & Programming, Productivity & Tools | lib/courses.ts COURSE_CATEGORY_LABEL |
| Pay with M-Pesa | README: M-Pesa STK Push + manual M-Pesa fallback |
| English or Kiswahili | lib/i18n.ts + LanguageToggle |
| Every lesson shows its data cost first; "Made in Kenya, for Kenyan phones" | i18n home.value.dataBody / home.heroBadge; components/DataSaverNote.tsx |
| Built in levels, from zero | README levels table (0046) |

Not claimed: learner numbers, reviews, testimonials, job outcomes, earnings (README: 0 reviews so far).
Characters are illustrative. Landing link given by the owner: https://jacksonlumumba2026-web.github.io/Skillforge/

## Sources
- https://github.com/jacksonlumumba2026-web/skillforge/blob/main/lib/pricing.ts
- https://github.com/jacksonlumumba2026-web/skillforge/blob/main/lib/i18n.ts
- https://github.com/jacksonlumumba2026-web/skillforge/blob/main/lib/courses.ts
- https://github.com/jacksonlumumba2026-web/skillforge/blob/main/README.md
