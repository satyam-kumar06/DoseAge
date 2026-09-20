# DoseWise recording runbook

Assume nothing. Follow top to bottom. Every command is meant to be typed
exactly as written.

**Where you type commands:** open **PowerShell**. Press the Windows key, type
`powershell`, press Enter. A blue window opens. That is your terminal.

**Your project folder:** `C:\Users\sonug\OneDrive\Documents\DoseAge`

Total time if nothing goes wrong: about 3 hours. Budget 5.

---

# PART 0: Fix the repo first (15 minutes)

Do not skip this. Right now your local git repo is in a broken state and a
folder called `docs` is missing.

## 0.1 Check what is actually there

```powershell
cd C:\Users\sonug\OneDrive\Documents\DoseAge
dir
```

Look at the list. You want to see `.git` and `docs`. If `dir` does not show
hidden items, run this instead:

```powershell
dir -Force
```

## 0.2 If `.git` is missing

Your work is safe on GitHub. Re-clone into a fresh folder:

```powershell
cd C:\Users\sonug\Documents
git clone https://github.com/satyam-kumar06/DoseWise.git DoseWise-clean
cd DoseWise-clean
git log --oneline -5
```

You should see `1e58042 backend updates and SMS feature added` at the top.
From here on, **work in `C:\Users\sonug\Documents\DoseWise-clean`**, not the
OneDrive folder. OneDrive is what has been corrupting the repo. Git and
OneDrive fight over the same files.

## 0.3 If `.git` is present but git says something is wrong

```powershell
cd C:\Users\sonug\OneDrive\Documents\DoseAge
git status
```

If it says `not a git repository`, go do 0.2.

If it says you are on a branch called `clean-main`, run:

```powershell
git checkout -f main
git status
```

It should now say `On branch main` and `nothing to commit, working tree clean`.

## 0.4 Fix your git name

You have commits under two different names. Fix it so future ones match:

```powershell
git config --global user.name "Satyam Kumar"
git config --global user.email "satyam.k.2105@gmail.com"
```

## 0.5 CRITICAL: fix the stale deploy config

Open `infra\samconfig.toml` in any text editor (Notepad works).

Find this line:

```
parameter_overrides = "Stage=\"dev\" BedrockRegion=\"ap-south-1\" BedrockModelId=\"global.anthropic.claude-haiku-4-5-20251001-v1:0\" DemoMode=\"1\" AlarmEmail=\"ashwin.yadav736dmy@gmail.com\""
```

Change `global.anthropic.claude-haiku-4-5-20251001-v1:0` to
`apac.amazon.nova-pro-v1:0` so the line reads:

```
parameter_overrides = "Stage=\"dev\" BedrockRegion=\"ap-south-1\" BedrockModelId=\"apac.amazon.nova-pro-v1:0\" DemoMode=\"1\" AlarmEmail=\"ashwin.yadav736dmy@gmail.com\""
```

**Why this matters:** that file still points at the Claude model that your AWS
India account cannot pay for. If you run `sam deploy` without fixing it, your
whole scan pipeline breaks with `INVALID_PAYMENT_INSTRUMENT` and you will lose
an hour debugging it at 2am.

Save the file. Then commit:

```powershell
git add infra/samconfig.toml
git commit -m "Point samconfig at Nova, not the unbillable Claude profile"
git push
```

---

# PART 1: Install the two tools you need (20 minutes)

## 1.1 OBS Studio (records your screen)

1. Go to https://obsproject.com
2. Click the big **Windows** download button
3. Run the installer, click Next through everything
4. Open OBS. It will show an "Auto-Configuration Wizard". Click
   **Cancel**. You do not need it.

### Set OBS up once

1. In the bottom middle, find the box labelled **Sources**
2. Click the **+** button
3. Choose **Display Capture**
4. Name it `Screen`, click OK, click OK again
5. You should now see your own screen inside OBS (it will look like an
   infinite mirror, that is normal)

Now the settings:

1. Click **Settings** (bottom right)
2. Click **Output** on the left
   - Recording Path: click Browse, pick your Desktop, make a new folder
     called `DoseWise-clips`
   - Recording Quality: **High Quality, Medium File Size**
   - Recording Format: **MP4**
3. Click **Video** on the left
   - Base Resolution: `1920x1080`
   - Output Resolution: `1920x1080`
   - FPS: `60`
4. Click **Audio** on the left
   - Desktop Audio: your speakers (this captures the Hindi voice)
   - Mic/Auxiliary Audio: **Disabled** (you are recording narration
     separately, and your mic picking up room noise will ruin the clips)
5. Click **OK**

**To record:** click **Start Recording** (bottom right). **To stop:** click
**Stop Recording**. Each recording saves as a separate MP4 in your
`DoseWise-clips` folder.

## 1.2 Clipchamp (stitches the clips together)

Already on Windows 11. Press Windows key, type `Clipchamp`, press Enter. Sign
in with a Microsoft account if it asks. If you do not have it, get it free
from the Microsoft Store.

---

# PART 2: Get the app running against AWS (20 minutes)

## 2.1 Find your API URL

```powershell
cd C:\Users\sonug\OneDrive\Documents\DoseAge
aws cloudformation describe-stacks --stack-name dosewise-dev --region ap-south-1 --profile dosewise --query "Stacks[0].Outputs" --output table
```

You will get a table. Find the row whose key is `ApiUrl` and copy the value.
It looks like `https://abc123xyz.execute-api.ap-south-1.amazonaws.com`.

**Write it down.** Every step below calls it `<YOUR-API-URL>`.

## 2.2 Confirm the backend is alive

Replace `<YOUR-API-URL>` with what you copied:

```powershell
curl <YOUR-API-URL>/health
```

You want to see `"backend":"aws"` and a bunch of `true` values. If you see
`false` anywhere or get an error, stop and fix that before recording.

## 2.3 Point the frontend at AWS

Create a file at `frontend\.env.local`. In PowerShell:

```powershell
cd C:\Users\sonug\OneDrive\Documents\DoseAge\frontend
notepad .env.local
```

Notepad will ask if you want to create a new file. Say yes. Type this one
line, replacing the URL:

```
VITE_API_BASE=<YOUR-API-URL>
```

Save (Ctrl+S) and close Notepad.

## 2.4 Start the frontend

```powershell
cd C:\Users\sonug\OneDrive\Documents\DoseAge\frontend
npm install
npm run dev
```

It will print something like `Local: http://localhost:5173/`. **Leave this
PowerShell window open.** Closing it kills the app.

Open a **second** PowerShell window for any further commands.

---

# PART 3: Prepare clean demo data (15 minutes)

## 3.1 Wipe the old data

In your second PowerShell window:

```powershell
cd C:\Users\sonug\OneDrive\Documents\DoseAge
python data/reset_demo.py --yes
```

## 3.2 Reload the medicine dataset

```powershell
python data/load_dataset.py
```

It should print a count of items written. If it prints an error about
credentials, run `aws configure --profile dosewise` and re-enter your keys.

## 3.3 Create the demo family, in Hindi

**This happens ONCE, now, before any recording.** Onboarding never appears in
the video. Every clip starts from the app already logged in.


1. Open Chrome
2. Go to `http://localhost:5173`
3. Go through onboarding
4. **Parent name:** `Kamla` (or your grandmother's name)
5. **Language: select Hindi.** This is the single most important setting in
   the whole demo. If this is English, the Hindi voice never plays and you
   lose your best 20 seconds.
6. **Parent phone:** your SNS-verified number
7. **Caregiver phone:** your SNS-verified number

## 3.3b The two prescriptions (5 minutes)

Both files already exist in `data\test-prescriptions\`. Nothing to write,
nothing to photograph.

| Clip | File | What it is |
| --- | --- | --- |
| 1 | `rx01.jpg` | Real handwritten AIIMS OPD sheet, prescribed by molecule |
| 2 | `rx_gp.jpg` | Printed private clinic sheet, prescribed by brand |

**Scan rx01 first and confirm it. Then scan rx_gp.** Order is not optional.

### What rx01 gives you

Handwritten, on an AIIMS letterhead, and written the way government hospitals
actually write: molecule names, not brands.

| On the sheet | Resolves to |
| --- | --- |
| Tab. Thyroxine 75mg OD | Thyroxine Sodium |
| Tab. Metformin SR 500mg OD | Metformin |
| Syp. Cremaffin | Liquid Paraffin + Milk of Magnesia |
| Cap. Eidofe Forte | no match |

Leave Eidofe Forte unmatched on screen. It shows the app being honest about
what it could not verify, which reads better than a suspiciously clean list.

### What rx_gp gives you

Thyronorm 75, Glycomet 500, Dolo 650, Calpol 650, Shelcal 500, Pan 40,
Ecosprin 75. All seven resolve.

### Three duplicates fire, all real

- **Thyroxine Sodium**: AIIMS wrote "Thyroxine", the private doctor wrote
  "Thyronorm". Same drug, molecule versus brand.
- **Metformin**: "Metformin SR" on one sheet, "Glycomet" on the other. Same
  again.
- **Paracetamol**: Dolo 650 and Calpol 650, inside rx_gp itself.

The first two are the strongest thing in your demo. A government hospital
writes the molecule, a private clinic writes the brand, and nobody in that
chain connects them. Say exactly that over the shot.

### Test the pair before you record

Scan rx01, confirm, scan rx_gp, check the amber banner names Thyroxine. If a
medicine reads wrong, fix it on the review screen while recording and say so
out loud. A caregiver correcting one field is the safety story working, not
the demo failing.

### Do not use the other nine on camera

rx02, rx04, rx05, rx06, rx08, rx09 and rx10 all show patient names, hospital
IDs, addresses or diagnoses, and rx08 carries a face photograph. Whether or
not they are synthetic, nobody watching can tell. Keep them for the private
accuracy run.

rx07 is an AVIF file with a `.jpg` name, which is why it crashed the scan.

---

## 3.4 Verify the Hindi voice actually plays

Before you record anything, prove the audio works:

1. Confirm at least one medicine so a dose exists
2. Open the reminder screen
3. Click the **Listen** button
4. You should hear a Hindi sentence

If you hear nothing: click anywhere on the page first (browsers block audio
until you interact), then click Listen again. If you hear English, your
parent language is set wrong. Go back and fix it.

**Do not proceed until you have heard Hindi come out of your speakers.**

## 3.5 Clean up Chrome for recording

1. Press `Ctrl+Shift+N` for an Incognito window (no bookmarks, no extensions)
2. Press `Ctrl+Shift+B` to hide the bookmarks bar if it shows
3. Press `Ctrl` and `+` twice to zoom to 125%
4. Close every other tab
5. Press `F11` for fullscreen when recording the app itself

---

# PART 4: Record the clips (60 minutes)

You are recording **8 separate clips**. Record each one, stop, check it, move
on. Do not try to do it in one take.

Between clips, hit Stop Recording in OBS. Each clip becomes its own MP4.

**Record everything silent.** No talking. Narration comes later.

---

## CLIP 1: The scan of the first prescription

**Target length:** 25 seconds

**Before you hit record:** be on the app's home screen, logged in, nothing
else on screen.

**Steps:**
1. Start Recording in OBS
2. Wait 2 seconds doing nothing
3. Click the **Scan** tab
4. Click **Take a photo** / upload
5. Choose **`rx01.jpg`** from `data\test-prescriptions\`
6. Let the progress list run all the way through (reading the handwriting,
   matching salts, checking duplicates)
7. When the review screen appears, wait 3 seconds
8. Click **Confirm all**
9. Wait 2 seconds
10. Stop Recording

**If the scan fails:** try again. If it fails twice, check
`curl <YOUR-API-URL>/health` again.

**Note:** `cardiology_clean` and `family_demo` are JSON fixture files used only
in offline mode. Running against AWS you upload real images and Bedrock really
reads them. Use your handwritten photos, not the JSON.

**Do not use rx01 to rx10 on camera.** They are real patients' prescriptions
with names, hospital IDs, addresses and diagnoses on them. Keep them for
accuracy testing only. (Also worth knowing: rx07 is an AVIF file with a .jpg
name, which is why it crashed the scan earlier.)

---

## CLIP 2: The duplicate catch (THE MOST IMPORTANT CLIP)

**Target length:** 35 seconds

**Before you hit record:** be back on the app home screen, with clip 1's
medicines already confirmed.

**Steps:**
1. Start Recording
2. Wait 2 seconds
3. Click **Scan**
4. Upload **`rx_gp.jpg`** from `data\test-prescriptions\`
5. Let it process
6. The review screen loads with an **amber banner at the top**
7. **DO NOT TOUCH ANYTHING FOR 6 FULL SECONDS.** Count it out loud in your
   head. The two pill strips slide together with the salt name between them,
   labelled "already taking" and "just scanned". This animation is your entire
   pitch. Let it breathe.
8. Slowly scroll down the medicine list so the judge sees the detail
9. Scroll back up to the banner
10. Wait 2 seconds
11. Click **Confirm all**
12. Stop Recording

**If the amber banner does not appear:** you skipped clip 1, or the data was
reset in between. Redo clip 1 first. The banner only fires because the first
prescription is already on the list.

**Record this clip twice.** You will use a frozen frame from it as your video's
opening shot, so you want a clean take.

---

## CLIP 3: The Hindi reminder (your emotional peak)

**Target length:** 25 seconds

**Before you hit record:** turn your speaker volume up. OBS is capturing
desktop audio, so whatever you hear is what gets recorded.

**Steps:**
1. Start Recording
2. Wait 2 seconds
3. Open the reminder screen (the full screen takeover with the big pill and
   the big button)
4. Click **Listen** so the Hindi voice plays
5. **Say nothing. Do nothing.** Let the full Hindi sentence finish.
6. Wait 2 more seconds of silence after it ends
7. Stop Recording

**Do not tap the big button in this clip.** You need the dose to go unanswered
so the escalation fires for clip 5.

**Check the clip before moving on:** open the MP4 and confirm you can actually
hear the Hindi. If the audio is silent, go back to OBS Settings, Audio, and
make sure Desktop Audio is set to your speakers, not Disabled.

---

## CLIP 4: The Step Functions console

**Target length:** 20 seconds

**Steps:**
1. Open a new Chrome tab
2. Go to https://ap-south-1.console.aws.amazon.com/states/home
3. Click your **escalation** state machine
4. Click **Executions**
5. Find the execution that is currently **Running** (it started when you
   ignored the dose in clip 3)
6. Click it to open the graph view
7. Start Recording
8. Slowly scroll the graph so the whole workflow is visible
9. Point your mouse at the **Wait** state that is highlighted
10. Hold there 3 seconds
11. Stop Recording

**If there is no running execution:** the escalation may already have
finished. Redo clip 3 to trigger a new one, then come straight here.

---

## CLIP 5: The SMS arriving on your phone

**Target length:** 15 seconds

This one is recorded **on your phone**, not your laptop.

**Android:** swipe down twice from the top, tap **Screen record**.
**iPhone:** swipe down from the top right, tap the **record** circle. (If you
do not see it: Settings, Control Centre, add Screen Recording.)

**Steps:**
1. Start the phone screen recording
2. Open your Messages app
3. Show the reminder SMS
4. Scroll to show the nudge SMS
5. Scroll to show the family alert SMS
6. Stop recording
7. Email the video to yourself, or use a USB cable, and put it in your
   `DoseWise-clips` folder

**If the SMS has not arrived:** the escalation waits 30 seconds per stage in
demo mode, so give it 2 minutes. If nothing arrives after 5 minutes, check
that your number is still verified in SNS.

---

## CLIP 6: The family dashboard

**Target length:** 20 seconds

**Steps:**
1. Start Recording
2. Open the **Family** tab
3. Let the adherence ring animate in, wait 3 seconds
4. Scroll slowly to the **Jan Aushadhi savings** card
5. Hold 3 seconds on it so the exact generic name is readable
6. Scroll to **Refill Radar**
7. Hold 3 seconds
8. Stop Recording

---

## CLIP 7: The AWS architecture proof

**Target length:** 40 seconds

**Steps:**
1. Open https://ap-south-1.console.aws.amazon.com/cloudformation
2. Click the **dosewise-dev** stack
3. Click the **Resources** tab
4. Start Recording
5. Scroll slowly through the resource list so the sheer number is visible
6. Open a new tab, go to the Step Functions console, show both state machines
   side by side in the list
7. Open a new tab, go to DynamoDB, click your table, show the item count
8. Stop Recording

---

## CLIP 8: The closing frame

**Target length:** 8 seconds

Open your README or make a simple slide with the DoseWise name and the line
"No pill should be a mistake." Record 8 seconds of it sitting still.

---

# PART 5: Record the narration (30 minutes)

## 5.1 Open the recorder

Press the Windows key, type `Sound Recorder`, press Enter. (On older Windows
it is called `Voice Recorder`.)

## 5.2 How to read it

- Sit close to your laptop mic, about 30cm
- Close the window, turn off the fan, kill any background noise
- Read at a normal speaking pace, not fast
- **Record each numbered block as its own recording.** If you fluff a line,
  stop, delete it, redo just that block. Do not try to do it in one take.
- Read it like you are explaining it to a friend, not reading a script

## 5.3 The script, word for word

**Block 1** (goes over the cold open, about 18 seconds)

> This is a real problem in my house. My grandmother takes seven pills a day,
> prescribed by three different doctors who never speak to each other. Two of
> them are the same medicine under different brand names. DoseWise is a
> serverless app that catches that.

**Block 2** (goes over clip 1, about 22 seconds)

> You photograph the prescription. Amazon Bedrock reads the handwriting and
> returns structured JSON: brand, strength, one dash zero dash one frequency,
> duration, and the exact line it read it from. This one is clean, so we
> confirm it.

**Block 3** (goes over clip 2, about 32 seconds)

> Now the second doctor. The government hospital wrote Thyroxine, the
> molecule. The private clinic wrote Thyronorm, the brand. Same drug, and no
> pharmacist in that chain would connect them. Same story again with
> Metformin and Glycomet. DoseWise never changes a prescription. It flags the
> overlap and sends you to your doctor. Nothing is saved until a human
> confirms this screen.

**Block 4** — SILENCE. Record nothing. Clip 3's Hindi audio carries this.

**Block 5** (goes over clips 4 and 5, about 20 seconds)

> If she does not tap, a Step Functions workflow waits, nudges once, waits
> again, and then messages me. Real SMS, from the real deployed stack.

**Block 6** (goes over clip 6, about 15 seconds)

> The family side shows adherence, names the exact Jan Aushadhi generic to ask
> the chemist for, and warns before a strip runs out.

**Block 7** (goes over clip 7, about 35 seconds)

> All serverless. React and Vite on the front. API Gateway HTTP API into
> Lambda. Bedrock with Nova Pro for extraction, Textract as a cheap OCR hint,
> Polly for the Hindi voice, SNS for the SMS, S3 for the scans, DynamoDB
> single table with a GSI and TTL. Two Step Functions workflows: an Express
> one for the scan pipeline, and a Standard one for dose escalation, because
> in a Standard workflow the waiting is free. Forty-seven resources, one SAM
> template, one command to deploy.

**Block 8** (goes over a text slide, about 13 seconds)

> Three things I learned. Circular dependencies in CloudFormation are caught
> by sam validate lint, not by deploying and waiting. Cross-region inference
> profiles bill through Marketplace, which an AWS India account cannot pay by
> card, so I rebuilt on the Converse API and moved to Nova. And the review
> screen is not a nice-to-have. It is the entire safety argument.

**Block 9** (goes over the closing frame, about 5 seconds)

> DoseWise. No pill should be a mistake.

## 5.4 Where the files go

Sound Recorder saves to `Documents\Sound Recordings`. Copy all of them into
your `DoseWise-clips` folder so everything is in one place.

---

# PART 6: Edit it together (45 minutes)

## 6.1 Start a project

1. Open Clipchamp
2. Click **Create a new video**
3. Click **Import media**
4. Select everything in your `DoseWise-clips` folder, including the phone
   video and all the narration files

## 6.2 Build the timeline

Drag clips onto the timeline in this order. The timeline is the strip at the
bottom.

| Order | What | Trim to |
| --- | --- | --- |
| 1 | Clip 2, frozen on the banner | 2 sec |
| 2 | Clip 1 | 22 sec |
| 3 | Clip 2, full | 32 sec |
| 4 | Clip 3 | 20 sec |
| 5 | Clip 4 | 12 sec |
| 6 | Clip 5 (phone) | 8 sec |
| 7 | Clip 6 | 15 sec |
| 8 | Clip 7 | 35 sec |
| 9 | A text slide with your three learnings | 13 sec |
| 10 | Clip 8 | 5 sec |

That totals 2 minutes 44 seconds. You have 16 seconds of slack.

**To make the frozen opening frame:** drag clip 2 onto the timeline, right
click it, choose **Freeze frame**, then trim it to 2 seconds.

**To trim a clip:** click it on the timeline, then drag its left or right edge
inward.

## 6.3 Add the narration

Drag each narration recording onto the audio track below the video, lining it
up with the matching clip. Block 1 under the opening, block 2 under clip 1,
and so on.

**Block 4 does not exist.** Leave that stretch silent so the Hindi plays alone.

## 6.4 Balance the audio

Click clip 3 on the timeline, find the **Audio** tab, and make sure its volume
is at 100%. That is the Hindi voice and it must be clearly audible.

For every other clip, set volume to **0%**. You do not want mouse clicks and
UI noises under your narration.

## 6.5 Export

1. Click **Export** (top right)
2. Choose **1080p**
3. Wait. It takes a few minutes.
4. The MP4 lands in your Downloads folder

## 6.6 Watch it once, all the way through

Check these five things:

- [ ] Total length is under 3:00
- [ ] The Hindi voice is clearly audible
- [ ] No narration talks over the Hindi
- [ ] You can read the text on screen without squinting
- [ ] The duplicate banner is on screen long enough to actually read

---

# PART 7: Upload to YouTube (10 minutes)

1. Go to https://youtube.com, sign in
2. Click the **camera icon with a +** (top right), choose **Upload video**
3. Drag in your MP4
4. **Title:** `DoseWise: catching duplicate medicines for elderly parents | AWS First Commit`
5. **Description:** paste this, filling in your links:

```
DoseWise flags same-salt duplicates across prescriptions and reminds elderly
parents by voice in Hindi. Built for the First Commit AWS hackathon.

Fully serverless: Lambda, Bedrock, Step Functions, DynamoDB, S3, SNS, Polly,
Textract, API Gateway.

Repo: https://github.com/satyam-kumar06/DoseWise
Live app: <YOUR-URL-IF-DEPLOYED>

DoseWise never changes a prescription. It flags issues for a doctor or
pharmacist to confirm.
```

6. **Audience:** select **No, it's not made for kids**
7. Click **Next** three times
8. On the Visibility page, choose **Unlisted**
9. Click **Save**
10. Copy the link. That goes in your submission form.

---

# Things that will go wrong, and what to do

**The scan spins forever.** Your API URL is wrong in `frontend\.env.local`, or
the stack is down. Run the health check again.

**Every medicine says "salt not matched".** The brands on that prescription
are not in your 63-brand dataset. Use the `cardiology_clean` and `family_demo`
fixtures, which are guaranteed to match.

**The Hindi voice does not play.** Click anywhere on the page first, then hit
Listen. Browsers block audio until you interact with the page.

**No amber duplicate banner.** You need TWO scans. The first prescription must
already be confirmed before you scan the second.

**The SMS never arrives.** Your number fell out of the SNS sandbox verified
list. Re-verify it in the SNS console.

**OBS records a black screen.** Right click the OBS shortcut, choose Run as
administrator, and add the Display Capture source again.

---

# If a judge asks something awkward

**"How accurate is the handwriting reading?"**
> It varies. That is exactly why nothing is saved until a human confirms the
> review screen. Every field shows the original line it was read from, so a
> caregiver can check rather than trust.

**"What if the brand is not in your dataset?"**
> Then it still gets scanned, scheduled and reminded, it just does not get the
> duplicate check. The matcher runs on a curated dataset of 63 Indian brands.
> Growing that is a data task, not a code task.

**"Is this giving medical advice?"**
> No. It flags that two brands share a molecule, which is a deterministic
> lookup, and routes that to a doctor or pharmacist. It never changes a dose.

**Never say:** "100% accurate", "works on any prescription", "AI doctor".
