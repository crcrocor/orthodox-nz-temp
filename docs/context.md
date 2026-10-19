# What this site is for

Source: Fr Alexander, 2026-10-19 (decided). This repository is public, so the internal plans behind the site are kept in the private repository crcrocor/orthodox-nz, `docs/context-temp-site.md`; do not copy them here or onto the site.

## Why the site exists

The trust of the Auckland parish, Church of the Resurrection of Christ Russian Orthodox Church Abroad Trust (CC42458), registers:

1. with **Apple Developer** as an organisation, which Apple reviews;
2. with **Google for Nonprofits**, for the free Google Workspace (mail at orthodox.nz). Goodstack verifies the organisation by comparing the application with the official register.

Both reviews look at this site.

## What the reviewers look at

- A real, working website of the organisation on its own domain, not a placeholder.
- The legal name, register number, address and contacts match the Charities Register and are the same on every page:
  - Church of the Resurrection of Christ Russian Orthodox Church Abroad Trust
  - CC42458 — https://register.charities.govt.nz/Charity/CC42458
  - 455–461 Dominion Road, Mount Eden, Auckland 1024
  - info@orthodox.nz
  - controlling trust: Russian Orthodox Church (Abroad) Auckland Trust Board, CC33927
- Donations: who receives the money and what it is for. Tax credits and receipts: only what has been verified. Inland Revenue's list of approved donee organisations shows CC42458 and CC33927 by name (checked 2026-10-19; the list gives names only). The bank accounts on the site are in other names ("Russian Orthodox Church Trust Board", "Russian Orthodox Church Benevolent Fund"), and on the register the donations are reported by CC33927, not CC42458. Until the account holder is confirmed, the site makes no tax claim and the pages carry a `TODO(content)`.

## What Apple checks when the trust enrols

From Apple's enrolment page (https://developer.apple.com/programs/enroll/, read 2026-10-19), for an organisation:

- a legal entity that can enter into contracts with Apple (no trade names or branches);
- the person who enrols must have the legal authority to bind the organisation;
- a D-U-N-S number, which Apple uses to verify the organisation's identity, legal entity status and address;
- a public, functional website on a domain associated with the organisation — a registrar's parking page is refused (orthodox.nz showed one until 2026-10-19);
- a work e-mail address on the organisation's domain.

What this means for us (2026-10-19; open questions, not decisions):

- The D&B (Dun & Bradstreet) record behind the D-U-N-S number gives Apple the organisation's name and address, so it should show the register's current legal name, with "Trust" (added 11/04/2025). That Apple requires an exact match is a hypothesis from an earlier Claude analysis, not stated on Apple's page. Apple's lookup tool: https://developer.apple.com/enroll/duns-lookup/.
- CC42458 has no NZBN on the register (CC33927 has one). Whether D&B confirms CC42458 as a legal entity decides which trust enrols: a question for a lawyer and the accountant.
- The e-mail domain should be the organisation's. The register still gives orthodox.net.nz as the website; changing it (and the D&B record) to orthodox.nz allows an @orthodox.nz address. crcrocor@gmail.com does not qualify.
- The register says a priest and a parish council run CC42458 (open data, "EntityStructure"). Who may sign for the trust is not checked; whoever enrols needs that authority, or Apple asks a person who can confirm it.

The open questions are tracked in `docs/todo-and-blessings.md`.

## Priorities

1. The same, exact details on the home, About, Contact, Privacy and Donations pages and in the footer.
2. Correct, current information — better than the old site, where much is out of date. Outdated items come first in `docs/todo-and-blessings.md`.
3. The deanery frame: this is the website of the New Zealand Deanery, and the Church of the Resurrection in Auckland is one of its communities. The legal entities behind the site are still that parish's trusts, and the site says so (the publisher in the footer, the About page).
4. Typography and everything else.

## Not on this site

- Plans (apps, payment methods, future services): internal; publishing them needs a blessing.
- Online donation forms: none; the Donations page gives bank details only.
