# HermitScreenshot — first-time user guide

**Download (Mac or Windows):** [GitHub Releases — latest version](https://github.com/YOYOMAII/Hermit_ScreenShot/releases/latest)

HermitScreenshot turns your **HTML** and **CSS** files into pictures that look like code in Visual Studio Code. You can download the images or put them into a **Word** document with **HermitSmart**.

Everything runs **on your computer**. Your files are not uploaded to the internet.

---

## What you need

| If you have… | You received… | You need… |
|--------------|---------------|-----------|
| **Mac** (Apple) | `HermitScreenshot-Mac.zip` | Nothing else — unzip and open the app |
| **Windows** | `HermitScreenshot-Windows.zip` | Nothing else — unzip and double-click **`HermitScreenshot.exe`** |
| **Windows** (developer kit) | `HermitScreenshot-Windows-build.zip` | [Python 3](https://www.python.org/downloads/) once, then `scripts\build_desktop.bat` (see below) |

The app is about **21 MB** on Mac because it includes Python and libraries inside the app so you do not install them yourself.

---

## “Untrusted” or blocked app — Mac and Windows

This app is **not signed** with Apple or Microsoft (normal for student/personal projects). Your computer may warn you the first time. **The app only runs locally on your machine** — it does not send your code to a website.

### Mac — “can’t be opened because the developer cannot be verified”

Do **not** only double-click the first time.

1. Unzip `HermitScreenshot-Mac.zip`.
2. **Right-click** (or hold **Control** and click) **HermitScreenshot.app**.
3. Click **Open** (not double-click).
4. In the new dialog, click **Open** again.

After you do this once, you can double-click the app like any other program.

**If it still says the app is “damaged”:**

1. Open **Terminal** (Applications → Utilities → Terminal).
2. Paste this line (change the path if you put the app somewhere else):

```bash
xattr -cr ~/Downloads/HermitScreenshot.app
```

3. Press **Enter**, then try **right-click → Open** again.

**If macOS moved the app to Trash:** put it back from Trash, then use **right-click → Open**.

---

### Windows — “Windows protected your PC” (SmartScreen)

When you run **HermitScreenshot.exe**:

1. You may see a blue window: **“Windows protected your PC”**.
2. Click **More info** (small link, not always obvious).
3. Click **Run anyway**.

You may need to do this **once** per download.

**If you built the app yourself** (`build_desktop.bat`): run SmartScreen steps on  
`dist\HermitScreenshot\HermitScreenshot.exe`.

**If Windows Defender quarantined the file:**

1. Open **Windows Security** → **Virus & threat protection** → **Protection history**.
2. Find **HermitScreenshot** → **Allow** / **Restore** if you trust the file from your classmate.

Only allow files you received from someone you trust.

---

### Why this happens (short)

| System | Reason |
|--------|--------|
| **Mac** | App is not from the App Store and not signed with a paid Apple Developer certificate. |
| **Windows** | `.exe` is not signed with a certificate Microsoft recognizes. |

Signing costs money each year; most school projects skip it.

---

## Install and open (Mac)

1. **Unzip** `HermitScreenshot-Mac.zip`.
2. You should see **HermitScreenshot.app**.
3. **Double-click** to open.

**First time only:** see **[“Untrusted” or blocked app](#untrusted-or-blocked-app--mac-and-windows)** above (right-click → **Open**).

**Tip:** Use the app window that opens. You do not need to install anything else.

---

## Install and open (Windows)

### Option A — `HermitScreenshot-Windows.zip` (usual)

1. **Unzip** `HermitScreenshot-Windows.zip`.
2. Double-click **`HermitScreenshot.exe`** (and **`GETTING-STARTED.md`** if you want the guide).
3. The zip contains **one app file**, not a folder of library code — that is normal.

If Windows SmartScreen warns you, see **[“Untrusted” or blocked app](#untrusted-or-blocked-app--mac-and-windows)** above.

### Option B — you received `HermitScreenshot-Windows-build.zip` (build it yourself)

1. Install **Python 3.9+** from [python.org](https://www.python.org/downloads/).  
   On the installer, check **“Add python.exe to PATH”** if you see it.
2. Unzip the folder.
3. Double-click **`scripts\build_desktop.bat`** and wait (first time can take several minutes).
4. Open **`dist\HermitScreenshot\HermitScreenshot.exe`**.

You only build once. You can zip `dist\HermitScreenshot` and reuse it later.

**WebView2:** The app window uses Microsoft Edge WebView2, which is already on most Windows 10/11 PCs.

---

## Main screen — code screenshots

1. Open **HermitScreenshot**.
2. **Drag and drop** your `.html` or `.css` files onto the page, or click to choose files.
3. Adjust settings if you want (optional):
   - **Lines per image** — default 20 lines per PNG
   - **Theme** — light, light-modern, or dark
   - **Font size**, **width**, etc.
4. Click **Generate screenshots**.
5. **Preview** each image, **download** one file, or **download ZIP** for all.

### Good to know

- Only **`.html`** and **`.css`** files are supported.
- Up to **20 files** per batch; max **40 MB** per upload.
- Your **original files are never changed** — only copies are used.
- Save your downloads: **generated files on the app’s server are deleted after about 1 hour**. Files in your **Downloads** folder stay until you delete them.
- Files must be saved as **UTF-8**. Very long single lines (minified code) may be rejected — use a normal, formatted file.

---

## HermitSmart — put screenshots in Word

1. In the app, click **HermitSmart** in the top bar.
2. Choose your **Word document** (`.docx`). Your original file is **not** modified; you get a **new copy** to download.
3. Add your **HTML/CSS** code files.
4. Set **lines per image** and caption options if needed.
5. Click **Build Word document**.
6. **Download** the updated `.docx` and open it in Microsoft Word.

### Layout

- **Two screenshots per page**, each with a caption below (Arial 11 pt).
- Default captions look like: `Fig 1: index1.html`, `Fig 2: index2.html`, …
- You can edit captions in Word after export.

### Before you submit

HermitScreenshot **does not check** if your code is correct. **You** must:

- Open every image and compare it to your source file (line numbers, no missing lines).
- Open the Word file and check every page, figure number, and caption.
- Keep backups of your original `.html`, `.css`, and `.docx` files.

---

## Privacy and safety

- The app listens only on **your machine** (`127.0.0.1`).
- Closing the app window **quits** the program.
- Temp folders are cleaned automatically after about **1 hour**.

---

## Troubleshooting

| Problem | What to try |
|---------|-------------|
| Mac says app is damaged / won’t open | Right-click app → **Open** → **Open** (see Install Mac above) |
| Windows blocks the app | **More info** → **Run anyway** |
| “Upload too large” | Fewer files or smaller files (limit 40 MB per batch) |
| “Only .html and .css” | Rename or export the correct file type |
| Empty or error after generate | Use formatted source, not one giant minified line |
| Windows build fails | Install Python, run `build_desktop.bat` again, read any red text in the window |
| HermitSmart page position wrong | Word page numbers are estimates — move figures in Word if needed |

---

## Quick checklist

- [ ] Installed or opened the app (Mac `.app` or Windows `.exe`)
- [ ] Uploaded the **right** HTML/CSS files
- [ ] Downloaded PNGs or Word **before** waiting too long
- [ ] Checked every image and caption yourself before submitting

---

For developers and sharing builds, see **README.md** in the full project.
