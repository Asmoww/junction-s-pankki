# S-Pankki pitch deck

- `S-Pankki-pitch.pptx`: editable deck (16:9, 10 slides, presenter notes on every slide).
- `S-Pankki-pitch.pdf`: the same deck as PDF for the submission.
- `build_spankki.py`: rebuilds the .pptx from `shots/` (python-pptx). Re-run after new screenshots:
  `python docs/slides/build_spankki.py`, then export to PDF from PowerPoint/Keynote/LibreOffice.
- `shots/`: real screenshots of the live app (Emma, English, 390×844 at 2×), 14 Nov.

Built from Rasmus's Claude's plan (`docs/SLIDES-PLAN.md` on `review/rasmus-research-coach`, d2ef6d2) with changes
explained in the PR #1 reply. Headlines are DRAFTS for Rasmus to approve or replace (his rule: no AI-written slide text
without his OK). Stage version (3:00): slides 1, 2, 3, live demo, 7, 9, 10. Recheck every number on the final build;
slide 7's trap score comes from the latest `scripts/run_traps.py --eu` run.
