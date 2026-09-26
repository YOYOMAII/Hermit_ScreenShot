# Code screenshots

## Download for friends (Mac & Windows)

**Share this link:** **[github.com/YOYOMAII/HermitScreenshot/releases/latest](https://github.com/YOYOMAII/HermitScreenshot/releases/latest)**

| Platform | Download | Run |
|----------|----------|-----|
| **Mac** | `HermitScreenshot-Mac.zip` | Unzip → right-click `HermitScreenshot.app` → **Open** → **Open** |
| **Windows** | `HermitScreenshot-Windows.zip` | Unzip → `HermitScreenshot.exe` (SmartScreen: **More info** → **Run anyway**) |

Copy-paste messages for friends: **[SHARE-WITH-FRIENDS.md](SHARE-WITH-FRIENDS.md)**. Full user guide: **[GETTING-STARTED.md](GETTING-STARTED.md)**.

---

Turn HTML and CSS source files into PNGs that resemble the Visual Studio Code Light editor. The program reads your files without changing them, keeps indentation and line numbers, and makes one image for each group of 20 lines.

## Install

Use Python 3.9 or newer. In this folder, run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate with `.venv\Scripts\activate` instead.

## Use from the command line

```bash
python code_screenshot.py index.html
python code_screenshot.py index.html style.css
python code_screenshot.py examples/index.html examples/style.css
```

Images go into `./code_screenshots/` (relative to the folder where you run the command). By default, `index.html` produces `index1.png`, `index2.png`, and so on. The PNG contains only the editor, without a file/language/range bar. The final image is shorter when fewer than 20 lines remain. All images in one command use the same width, and long lines increase that shared width instead of wrapping or being cut off.

Vertical guides connect matched, aligned HTML opening and closing tags (such as `<main>` and `</main>`) and CSS brace blocks. Multiline HTML tags get a guide for their continuation lines. Unmatched or misaligned code does not get a misleading guide.

Options:

```bash
python code_screenshot.py index.html --lines 25 --font-size 28
python code_screenshot.py style.css --output evidence --theme light-modern
python code_screenshot.py index.html --name-style padded  # index_001.png
python code_screenshot.py index.html --width 1400 --tab-width 4
python code_screenshot.py index.html --font /path/to/FiraCode-Regular.ttf
python code_screenshot.py index.html --active-line 17
python code_screenshot.py index.html --header  # Optional old-style file bar
python code_screenshot.py index.html --fit-width  # Each PNG only as wide as its own lines
```

`--theme` accepts `light` (default), `light-modern`, or `dark`. `--width` sets a minimum, so every source line remains visible. Tabs display at four-space tab stops by default. PNGs are saved with 144 DPI metadata for document insertion.

For input files with the same stem (for example, `index.html` and `index.css`), names include the extension to avoid collisions: `index_html1.png` and `index_css1.png`.

## Use the local upload page

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Drop or choose one or more HTML/CSS files, adjust the settings, and select **Generate screenshots**. Preview each image, download it individually, or download the whole batch as a ZIP. Until they're deleted, the images are also saved under `code_screenshots/<batch ID>/`.

The page runs only on your computer (`127.0.0.1`). It accepts up to 20 files and 40 MB per upload. Uploaded source files are held temporarily for rendering, then removed. Stop the page with Ctrl+C in its terminal.

**Generated files are deleted automatically 1 hour after they are made, whether or not you downloaded them.** Download what you need before then; files you've downloaded stay safely in your Downloads folder. Cleanup runs when the app starts, every 10 minutes while it runs, and before each new batch. It only removes the web page's batch folders (12-character names such as `3f9a0c1b2d4e`). Images you make with `code_screenshot.py` on the command line are never deleted. To keep files longer, change `KEEP_RESULTS_HOURS` in `app.py`.

If port 5000 is already in use, choose another one: `PORT=5050 python app.py` (on Windows PowerShell: `$env:PORT=5050; python app.py`). Open `127.0.0.1`, not `localhost`: on macOS, `localhost:5000` can reach the AirPlay Receiver instead of this page.

Source files must be saved as UTF-8. Minified files with extremely long lines (more than about 2,000 characters at the default font size) are refused, because they can't be shown readably in one image; use the original, formatted file.

## Put screenshots into a Word document (HermitSmart)

Select **HermitSmart** in the top bar (or open [http://127.0.0.1:5000/smart](http://127.0.0.1:5000/smart)). Choose a `.docx` document and one or more HTML/CSS files, set the lines per image, and select **Build Word document**. HermitSmart makes an updated copy of your document; the original is not changed.

- Each page holds two screenshots, scaled to fill their half of the page. Each screenshot is only as wide as its own longest line, so one very long line elsewhere in a file doesn't shrink the other images. Every image uses Word's **In Front of Text** layout and has a text box below it for the caption, in Arial 11 pt.
- The default caption is `Fig {n}: {stem}{part}{ext}`, which gives `Fig 1: index1.html`, `Fig 2: index2.html`, and so on. You can change it with `{n}` (figure number), `{stem}`, `{part}`, `{ext}`, `{file}`, and `{file_no}`. For example, `Fig {file_no}.{part}: {file}` gives `Fig 1.2: index.html`. You can also edit any caption later in Word.
- **Insert position**: *End of document*, *After page N* (0 = before the first page), or *Continue after the last HermitSmart figure*.
- **Continuing**: select **Keep adding to this document** to add more code files to the copy you just built. You can also upload a document HermitSmart made earlier. HermitSmart finds its last figure, fills an empty second slot on that page, and carries on numbering (Fig 7, Fig 8, …). Figures are found by their hidden drawing names, so editing caption text in Word does not break this.

A `.docx` file does not store page numbers. *After page N* counts pages from the page breaks Word saved in the file and from manual page breaks, so check the result in Word. Updated documents and preview images are saved under `smart_documents/<document ID>/` and deleted automatically after 1 hour, like the screenshots. Download your document before then. *Keep adding* also only works within that hour; after that, upload the downloaded `.docx` again to continue.

## Before you submit: check your own work

This program copies your code into images exactly as written. It **does not** check whether your code is correct, complete, or the right version, and it can't know what your teacher or reviewer expects. Before you hand anything in:

- Open every PNG and compare it with your source file. Make sure no lines are missing or cut off and the line numbers run in order.
- Make sure you uploaded the right files and the right version of each file.
- For HermitSmart, open the downloaded `.docx` in Word and check every page. Make sure each image is on the correct page and each caption and figure number is right. Page positions are estimates.
- Keep your original files. The program never changes them, but keep your own backup anyway.

You are responsible for checking the final result yourself.

## Share a desktop app with friends (Mac and Windows)

**What to send (only these):**

| Friend has | Send this |
|------------|-----------|
| **Mac or Windows** | **[Releases / latest](https://github.com/YOYOMAII/HermitScreenshot/releases/latest)** — pick the zip for their OS |

Do **not** send your whole project, `.venv`, `build/`, `dist/`, or `code_screenshots/`. See `releases/WHAT-TO-SEND.txt`.

**Make fresh zip files:**

```bash
chmod +x scripts/export_for_friends.sh
./scripts/export_for_friends.sh
```

That creates the **Mac** zip on your Mac. For **both** Mac and Windows zips without building locally, use **[GitHub Releases](https://github.com/YOYOMAII/HermitScreenshot/releases/latest)** (see below).

**Publish a new release (Mac + Windows zips):** push a tag like `v1.0.5` or run **Actions → Release → Run workflow**. This repo is private, so the workflow publishes the zips to the public download-only repo **[YOYOMAII/HermitScreenshot](https://github.com/YOYOMAII/HermitScreenshot)**. That repo holds only a README, so the "Source code" files GitHub adds to every release contain no app code. Publishing there needs a repo secret named `RELEASES_TOKEN`: a fine-grained token with **Contents: Read and write** on `YOYOMAII/HermitScreenshot`.

Friends do **not** need Python if you send the Mac zip or the Windows zip above.

| Your friend uses | You build on | Ready-to-run output |
|------------------|--------------|---------------------|
| **Mac** | A Mac | `HermitScreenshot-Mac.zip` |
| **Windows** | Windows (or GitHub Actions) | `HermitScreenshot-Windows.zip` |

You cannot make a Windows `.exe` on a Mac (or a Mac `.app` on Windows) with this setup. Build once per platform, or ask a friend on the other OS to run the build script.

**On your Mac:**

```bash
chmod +x scripts/build_desktop.sh
./scripts/build_desktop.sh
```

**On Windows:** double-click `scripts/build_desktop.bat` or run it in Command Prompt.

The first build downloads PyInstaller and pywebview and can take several minutes. The app opens in its own window. Generated files are stored in the user’s app data folder (not next to the `.app`), and still auto-delete after 1 hour.

**First launch:** macOS may say the app is from an unidentified developer — right-click → **Open** → **Open** once. Windows may show SmartScreen for unsigned apps — **More info** → **Run anyway**. For a school project, that is normal unless you pay for code signing.

**Windows note:** The UI uses Microsoft Edge WebView2, which is already on most Windows 10/11 PCs.

To try the desktop window without building:

```bash
pip install -r requirements-desktop.txt
python desktop_app.py
```

## Check the installation

```bash
python -m unittest -v
```
