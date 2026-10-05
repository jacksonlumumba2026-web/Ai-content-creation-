# SkillPath Africa — fact sheet and angle bank (🎓 16:00 promo lane, owner 2026-10-05)

The owner's own learning app. Repo: https://github.com/jacksonlumumba2026-web/skillforge
(public). Landing page (owner's link): https://jacksonlumumba2026-web.github.io/Skillforge/
App: https://skillforge-delta-nine.vercel.app (lib/site.ts). Re-check this sheet against the repo
before every promo; prices and features can change.

## Claims we may make (checked 2026-10-05)
| Claim | Where it's true in the app |
|---|---|
| "Made in Kenya, for Kenyan phones" | lib/i18n.ts `home.heroBadge` |
| "Learn a skill that pays. KSh 500 a path." | i18n `home.heroTitle` + lib/pricing.ts `SINGLE_COURSE_PRICE = 500` |
| Short video lessons in coding, freelancing, design, marketing and everyday work tools | i18n `home.heroSubtitle` |
| Watch the first lesson of every path free — no account, no card | README "Homepage claims" (`lessons.is_free_preview`) |
| Pay once, no subscription, keep the path for life | i18n `home.value.payOnceBody`; no recurring billing in the code |
| Bundle: any 10 paths for KSh 1,000, buyer picks which ten | lib/pricing.ts `BUNDLE_PRICE = 1000`, `BUNDLE_COURSE_COUNT = 10` |
| Pay with M-Pesa | README: Daraja STK Push + manual M-Pesa fallback |
| Learn in English or Kiswahili | lib/i18n.ts + LanguageToggle |
| Every lesson shows its data cost before you press play | i18n `home.value.dataBody`; components/DataSaverNote.tsx |
| Built in levels, from zero up; plain language, step by step | README levels (0046); i18n `home.value.beginnerBody` |
| Five areas: Business & Freelancing, Marketing & Growth, Design & Creative, Tech & Programming, Productivity & Tools | lib/courses.ts |
| Certificate on completion | app/certificate, CertificateButton (check it is shown for the path before claiming) |

## Never claim
Number of learners, reviews/ratings, testimonials, "job-ready", jobs or income earned, "notes and
practice task on every lesson" (README: not true for every path yet). Characters are illustrative
and tagged. Don't name or show other platforms' brands; lessons embed YouTube tutorials — don't
claim "our own filmed lessons".

## Angle bank (one per promo; mark USED <date>)
Paths in the catalogue (curated migrations): WordPress Website Building (No-Code); Excel & Spreadsheets
for Work; Bookkeeping & QuickBooks for Small Business; WhatsApp Business & Facebook Marketplace Selling;
Instagram & TikTok Growth; Video Editing; Mobile Photography & Content Creation; Graphic Design;
Presentation Design (PowerPoint & Canva); Copywriting & Content Writing; Virtual Assistance & Data Entry;
Transcription & Translation Freelancing; Customer Service & Virtual Call Center Skills; Python
Programming for Beginners; SQL & Databases; Data Analysis & Visualization; Power BI; UI/UX Design
(Figma); Cybersecurity & Online Safety; IT Support & Help Desk; Personal Finance & Budgeting Basics;
Resume Writing, LinkedIn & Personal Branding; Sales & Lead Generation for Small Business; E-commerce &
Online Selling; Google Ads & Facebook Ads; SEO; Email Marketing; Notion; Zapier automation; AI Tools.

- KSh 500 a path, first lesson free — USED 2026-10-06
- Bundle: any 10 for KSh 1,000 — USED 2026-10-07
- Data cost shown before every lesson — USED 2026-10-08
- Next ideas: a mama mboga's daughter learns WhatsApp Business selling; a matatu tout learns Excel;
  a cyber café owner learns WordPress and builds sites for neighbours; a graduate learns Virtual
  Assistance; learn in Kiswahili; certificates; "try the first lesson tonight, free".
