# Getting the team onto the repo

## First: GitHub is not empty

`https://github.com/satyam-kumar06/DoseWise` has **123 files** on `main` at
commit `1e58042`. The whole backend, frontend, infra template, dataset and
tests are all up there.

What is empty is the `.git` folder inside
`C:\Users\sonug\OneDrive\Documents\DoseAge`. OneDrive keeps deleting it. That
is why it looks like nothing is there.

So there are **no files to send anyone**. Your teammates clone. That is the
whole transfer.

---

## Step 1: Get your own copy off OneDrive (10 minutes)

This has now broken your repo three times. Git writes hundreds of small files
into `.git` and OneDrive syncs, locks and removes them underneath it. That is
where the stuck `index.lock` came from, and why `docs/` keeps vanishing.

Open PowerShell:

```powershell
cd C:\Users\sonug\Documents
git clone https://github.com/satyam-kumar06/DoseWise.git DoseWise
cd DoseWise
git log --oneline -3
```

You should see `1e58042` at the top.

**From now on, work in `C:\Users\sonug\Documents\DoseWise`.** Not the
OneDrive folder. Do not move this folder into OneDrive, Dropbox or Google
Drive later.

Once you are happy the clone works, rename the old folder to
`DoseAge-OLD-DO-NOT-USE` so you never open it by accident.

### Bring across the files that only exist locally

Two things are not in the repo yet:

```powershell
cd C:\Users\sonug\Documents\DoseWise
copy "C:\Users\sonug\OneDrive\Documents\DoseAge\data\test-prescriptions\*" "data\test-prescriptions\"
```

And your AWS credentials are in `C:\Users\sonug\.aws\`, which is outside the
project, so nothing to do there.

---

## Step 2: Restore the docs folder (2 minutes)

`docs/` got dropped from the working tree again and your last commit carried
the deletion. Everything is recoverable:

```powershell
cd C:\Users\sonug\Documents\DoseWise
git checkout 0eef93b -- docs/
git add docs/
git commit -m "Restore docs/ (dropped by the OneDrive working tree)"
git push
```

That brings back `AWS-SETUP.md`, `DATASET.md`, `DEMO.md`, `api-contract.md`
and `learnings.md`.

---

## Step 3: Add your teammates (2 minutes)

1. Go to `https://github.com/satyam-kumar06/DoseWise`
2. **Settings** tab
3. **Collaborators** in the left sidebar
4. **Add people**
5. Type their GitHub username, pick **Write** access
6. Repeat for the second person

They get an email invite. They have to accept it before they can push.

Naitik already has commits, so he has probably already got access. Check the
list before inviting him twice.

---

## Step 4: Send them this

Paste this into your group chat, filling in the two blanks:

> Repo: https://github.com/satyam-kumar06/DoseWise
> Check your email for a GitHub invite and accept it first.
>
> Then in a terminal:
>
> ```
> git clone https://github.com/satyam-kumar06/DoseWise.git
> cd DoseWise
> git config user.name "YOUR NAME"
> git config user.email "your@email.com"
> ```
>
> Do not put this folder in OneDrive or Google Drive. Git and cloud sync
> fight and it corrupts the repo.
>
> To run it without needing AWS keys:
>
> ```
> python backend/local_server.py --port 4000 --demo
> ```
>
> and in a second terminal:
>
> ```
> cd frontend
> npm install
> npm run dev
> ```
>
> That runs the whole app offline against saved prescription fixtures.
> Everything except the real Bedrock call and the real SMS works.
>
> Your tasks are in docs/TEAM-SETUP.md under your name.
> Branch naming and the PR rule are in there too. Read it before you push.

---

## Step 5: The rule that stops you stepping on each other

Each person owns folders. If you only touch your own folders, you will almost
never hit a merge conflict.

| Person | Owns |
| --- | --- |
| **A** | `backend/functions/extract`, `backend/functions/salts`, `backend/prompts`, `data/` |
| **B** | `infra/`, `backend/functions/api`, `backend/statemachines`, `backend/functions/notify` |
| **C** | `frontend/`, `docs/screenshots`, video files |

Shared files (`README.md`, `docs/api-contract.md`, `docs/learnings.md`): one
person at a time, and say in the group chat before you edit one.

`backend/common/` is shared by everyone. Announce before touching it.

---

## Step 6: How every change gets in

Nobody commits straight to `main`. Ever. That is how you lose work.

```powershell
git checkout main
git pull
git checkout -b a/accuracy-run
```

Branch names: `a/`, `b/` or `c/` then what you are doing.
`b/amplify-deploy`, `c/empty-states`, `a/expand-dataset`.

Do your work, then:

```powershell
git add -A
git status
git commit -m "Add per-prescription accuracy scores for rx01 to rx10"
git push -u origin a/accuracy-run
```

**Always run `git status` before you commit.** Read the whole list, not just
the first few lines. A commit that silently deletes a folder is exactly how
`docs/` disappeared twice.

Then on GitHub: **Compare & pull request**, describe what you did in two
lines, and **request a review from one of the other two**. They click
Approve, then you click Merge.

The reviews take thirty seconds each and they are themselves evidence of
collaboration for the judges. Do not skip them.

---

## Step 7: Who does what from here

Enough real work for six or seven commits each.

### Person A: AI and data

1. Expand `data/medicines.csv` past 63 brands. Highest leverage thing left in
   the project, and it is pure data entry.
2. Run rx01 to rx10 through the pipeline, write `docs/accuracy.md` with a
   score per prescription.
3. Fill the licence and credits table in `docs/DATASET.md`.
4. Write `docs/test-escalation.md`, the four-case checklist.
5. Move the Hindi and English message texts into
   `backend/prompts/messages.json`.
6. Draft the Builder Center blog in `docs/blog.md`.
7. Fix the `ME-12` false match: it resolves to Met XL (Metoprolol) at 0.93
   confidence, but ME-12 is Mecobalamin. Wrong-drug duplicate alerts are the
   worst bug this app can have.

### Person B: cloud and backend

1. Deploy the frontend to Amplify and produce the live URL. The submission
   asks for it and there is no URL yet.
2. Draw `docs/architecture.png` with official AWS icons.
3. Write `docs/cost.md` from the AWS Pricing Calculator, 1,000 families.
4. Add the CloudWatch dashboard and alarms.
5. Add the graceful-failure path so a Bedrock error still opens the review
   screen for manual entry.
6. Make `DemoMode` a per-family flag instead of a stack parameter.

### Person C: design and frontend

1. Empty states for every list, each with one action button.
2. Loading skeletons instead of spinners.
3. Friendly error messages with a retry button, instead of the raw exception
   dumps currently shown.
4. Fix whatever breaks at 200% phone font size.
5. Contrast check every parent screen, aim for 7:1.
6. Screen reader labels on all icon buttons.
7. Record the video from `docs/DEMO.md`.

---

## About AWS access

**Do not share your AWS keys.** Not in chat, not in a file, not in the repo.

Almost all the work above runs offline with `--demo`. Only Person B needs
real AWS, and they should get their own IAM user in your account:

1. IAM console, **Users**, **Create user**
2. Attach `PowerUserAccess` for now
3. Create an access key for them, send it through something that is not a
   group chat
4. Delete the key after the hackathon

If a key ever leaks, delete it in IAM immediately. Rotating is not optional.
