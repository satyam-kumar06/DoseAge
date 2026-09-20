# Read this first

The new build was written into this folder on 2026-09-18. Shell access to
your machine is down (a Windows update broke it), so files could be **written
but not moved or deleted**. Everything below is a delete you need to do
yourself, in Explorer or a terminal. Nothing here is used by the new code.

## 1. Required before the app will run

The old frontend was React 19 + Tailwind 4. The new one is React 18 +
Tailwind 3, and the installed packages will fight the new config.

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
npm install
```

## 2. Old frontend files, now unused

These are the previous mock-only UI. They are not imported by anything in the
new build, so the app runs with them present, but delete them to keep the
repo readable:

```
frontend/src/App.css
frontend/src/assets/
frontend/src/constants/
frontend/src/lib/
frontend/src/mocks/
frontend/src/pages/
frontend/src/store/
frontend/src/components/BottomNav.jsx
frontend/src/components/DuplicateBanner.jsx
frontend/src/components/EmptyState.jsx
frontend/src/components/PillSwatch.jsx
frontend/src/components/Shell.jsx
frontend/src/components/SlotCard.jsx
frontend/src/components/TodayRing.jsx
frontend/src/components/icons/
frontend/eslint.config.js
frontend/README.md
claude/                      the original drop of that UI
```

Keep them somewhere if you want the old look back. The design tokens that
survived into the new build are in `frontend/tailwind.config.js`; the Hindi
copy is in `frontend/src/i18n.js`.

## 3. Superseded data files

```
data/medicines_seed.json          -> replaced by data/medicines.csv (50 brands, prices, generics)
backend/prompts/extraction_v1.txt -> replaced by extraction_v2.txt (stricter JSON contract)
```

## 4. Keep these

- `data/test-prescriptions/rx01..rx10.jpg` — your ten real prescriptions.
  These are the Day 1 accuracy test set. Once Bedrock access is granted, run
  each one through the pipeline and record the results.
- `docs/api-contract.md` — still accurate. One difference worth fixing in it:
  slots are `MORNING` / `AFTERNOON` / `NIGHT` in the code, not lowercase.

## 5. What is different from the old API contract

Nothing breaking. The new backend implements every endpoint the contract
lists, plus `POST /doses/{id}/undo`, `GET /parents/{id}/alerts`,
`POST /parents/{id}/refills/check` and `GET /outbox`.
