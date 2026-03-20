# LOS — Local osu! Server

**A user-friendly osu! server that replicates the official Bancho experience on your own machine — completely separate from the official servers, with quality-of-life tools and features every osu! player will love.**

---

## Table of Contents

- [Inspiration](#inspiration)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [Proxy Settings Reference](#proxy-settings-reference)
- [FAQ (Users)](#faq-users)
- [Architecture](#architecture)
- [FAQ (Developers)](#faq-developers)
- [Contributing](#contributing)

---

## Inspiration

In 2018, I got restricted. While learning from my mistakes, I still wanted to experience Bancho without risking any further violations on the official servers. The idea stuck with me, and by 2021 I finally had the knowledge to build it. After a few years away from both the project and the game, I returned in 2026 with renewed passion — and brought LOS to what it is today.

---

## Installation

> ⚠️ **Windows only** — the setup has only been tested on Windows. Linux/macOS support is untested.

The initial setup has a few steps, but once complete you'll have a fully functional local osu! server running on your machine.

### Prerequisites

- Windows 10 or later
- A stable internet connection for downloading dependencies

---

### 1. Download the Source Code

Click the green **Code** button at the top right of this page, then select **Download ZIP**. Once downloaded, extract the ZIP to a folder of your choice.

---

### 2. Install Python

> Skip this step if you already have Python **3.13.12 or later** installed.

1. Download and run the Python installer manager from [python.org/downloads](https://www.python.org/downloads/).

2. During installation, the terminal will ask you several questions. Use the table below as a guide — answer **`y`** to the listed prompts and **`n`** to everything else:

   | Prompt | Answer |
   |--------|--------|
   | Allow paths longer than 260 characters? | `y` |
   | Add commands directory to PATH? | `y` |
   | Install the current latest version of CPython? | `y` |

3. When asked about additional help, enter `n`. Python is now installed!

---

### 3. Install & Configure Mitmproxy

Mitmproxy acts as a local proxy to intercept and redirect osu! traffic to your local server.

#### Step 1 — Install Mitmproxy

1. Download the Windows installer from [mitmproxy.org](https://www.mitmproxy.org/) and run it.
2. At the end of installation, choose to **run mitmproxy** when prompted.
   - If you missed this, search for `mitmproxy.exe` and launch it manually.
3. A terminal window should open with **"Flows"** visible in the top-left corner. Keep this open.

#### Step 2 — Configure Windows Proxy Settings

> ⚠️ After enabling the proxy, **do not refresh this page** — it may temporarily block your connection.

Follow the [Proxy Settings Reference](#proxy-settings-reference) to enable the proxy, then come back here.

#### Step 3 — Install the Mitmproxy Certificate

1. With the proxy enabled, navigate to [https://mitm.it/](https://mitm.it/).
   - You may see a browser security warning — this is expected. In Chrome, click **Advanced → Proceed to site**.
2. Click the green **"Get mitmproxy-ca-cert.p12"** button (next to the Windows logo) and download the certificate.
3. Open the downloaded file and click through all prompts (Next / Yes). The installation should be quick.
   - If a security warning appears, click **Yes** to continue.
4. You should see **"Import Successful"** at the end.

#### Step 4 — Finish Up

You can now **disable the proxy** and **close the mitmproxy terminal**. Setup is complete!

---

## Running the Server

1. Enable the proxy — see [Proxy Settings Reference](#proxy-settings-reference).
2. Navigate to the folder where you extracted the source code.
3. Double-click **`main.py`** — your server is now up and running!
4. To connect to the server, follow the instructions in the [Connecting to the Server](#connecting-to-the-server) section below.

> 💡 If any errors appear and you're concerned about losing your connection, disable the proxy and close the terminal immediately, then report the issue in our [Discord server](https://discord.gg/KcgTtV25En) for help.

---

## Connecting to the Server

1. Go to your osu!.exe file. Right-click and select **Create shortcut**.
2. Right-click the newly created shortcut and select **Properties**.
3. In the **Target** field, add ` --devserver akatsuki.gg` to the end of the existing text. It should look something like this:

   ```
   "C:\Path\To\osu!\osu!.exe" --devserver akatsuki.gg
   ```
4. Click **Apply**, then **OK**.
5. Launch the game using this shortcut, and log in with any username and password. You should now be connected to your local server!

## Proxy Settings Reference

These are the proxy settings used during both installation and when running the server.

1. Open **Windows Settings → Network & Internet → Proxy**.
2. Under **Manual proxy setup**, toggle **"Use a proxy server"** to **On**.
3. Fill in the following values:

   | Field | Value |
   |-------|-------|
   | Proxy IP address | `http://localhost` |
   | Port | `8080` |
   | Exceptions | `*.ppy.sh*; *.ppy.sh/*` |

   > The exceptions ensure osu!'s official domains are never routed through the proxy.

4. Click **Save**.

## FAQ (Users)

*Documentation coming soon.*

---

## Architecture

*Documentation coming soon.*

---

## FAQ (Developers)

*Documentation coming soon.*

---

## Contributing

Since this project is in active production, every commit to `main` must be stable and non-breaking for end users. With that in mind:

- **All changes go through PRs** — this applies to external contributors and my own changes alike.
- **PRs should be reviewed thoroughly** — ideally by another person alongside an AI review (Copilot/Claude). Only merge once everything looks good.
- **Version control is handled automatically** — users will be notified when an update is available. If auto-updates are off, they'll be prompted to update manually. Otherwise, the update applies on next boot.

> In a perfect world nothing slips through, but emergencies happen and things get overlooked — that's understood. The goal is just to keep the bar high.

---

### Code Philosophy

This project leans heavily towards **readability and layered architecture**. Every piece of code should be intentional — if something exists, there should be a clear and understood reason for why it's there. When in doubt, favor clarity over cleverness.

---

### All skill levels are welcome

You don't need to be an expert to contribute. If you're newer to a concept or unsure about something, that's completely fine — questions are encouraged. If anything comes up during development, don't hesitate to join the [Discord and reach out!](https://discord.gg/KcgTtV25En)

---

### Editing `.json` files or database models

The migration system is strict by design. **Never edit an existing versioned model directly.** Instead, create a new version class, set `previous_model` on it, implement the migration, and update the `Current*` alias used throughout the project.

**Example:**

```python
# Original model — do NOT edit this
class UserV1(MigrationModel):
    name: str
    age: int

# Want to add an email field? Create UserV2 instead
class UserV2(MigrationModel, previous_model=UserV1):
    name: str
    age: int
    email: str

    @staticmethod
    def migrate_from_previous(previous_data: dict[str, Any]) -> dict[str, Any]:
        """Migrate from UserV1 to UserV2: add email field."""
        previous_data["email"] = ""
        return previous_data

# Update the alias — this is what the rest of the project references
CurrentUser = UserV2
```

For more detail on how migrations work, see the [jays-tools migration docs](https://github.com/jeevanjohnson/jays-tools/tree/main?tab=readme-ov-file#migrations).

---