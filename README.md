## 🕹️ ScoreBridge Arcade Sync

Automation system to capture high scores (.hi) from emulators in RetroArch (such as FinalBurn Neo), process them using a Python script, and automatically sync them with **iScored**, seamlessly integrated with frontends such as **Attract-Mode Plus**.

After selecting a game in Attract-Mode Plus (AM+) and launching it in RetroArch, at the end of the game, ScoreBridge will look for your initials in the .hi file. It will only submit your score to iScored if it is higher than your existing record, maintaining a single top score.

---

## 📋 Prerequisites on Windows

Before setting up the project, make sure you have installed on your system:
1. **Python** (version 3.x recommended). Make sure to check the *"Add Python to PATH"* box during installation.
2. **RetroArch** configured with the necessary cores (e.g., `fbneo_libretro.dll`).
3. **Attract-Mode Plus** as a gaming frontend.
4. **An active iScored account** with your games created in your Gameroom.

---

## ⚙️ Step by Step Installation and Configuration

### 1. Clone or download the repository
Place the project folder in the path of your choice (for example, `C:\AttractModePlus\ScoreBridge\`).

### 2. Install Python and Dependencies
Install Python 3.x from [python.org/downloads](https://www.python.org/downloads/).

Open a terminal (CMD or PowerShell) in the project folder and install the required libraries for HTTP requests and QR code processing:

pip install requests
pip install opencv-python

### 3. Setup your iScored QR codes folder
Configure all your games in your iScored account. Then, download the ZIP file containing all your game QR codes from the iScored dashboard.

Create a folder named qrcodes inside the project root directory (C:\AttractModePlus\ScoreBridge\qrcodes\). Unzip and place all the QR image files inside this qrcodes folder.

### 4. Review the config_example.json file
Modify the following values and save the file as config.json:

.- default_initials --> set your default initials. 
.- hi_folder --> path to the folder where RetroArch stores the .hi files
.- gameroom --> name of your gameroom in iSocred
.- games --> As you play new games from RetroArch, they will be automatically registered here. If the QR code image exists in the qrcodes/ folder, ScoreBridge will decode it and assign its iscored_id automatically in a single step!

### 5. Check the loader_example.bat file
In the AM+ emulator settings, make sure the executable points to loader.bat:

executable C:\AttractModePlus\ScoreBridge\loader.bat

args "[romfilename]"

rompath C:\AttractModePlus\collections\Arcade\roms\

workpath C:\RetroArch\

romext .zip

system Arcade

In my case, on one hand I have a folder with Retroarch, and on the other a folder with AM+, and within it I have ScoreBridge.