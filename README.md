the first startup will take a few seconds idk why maybe because windows defender

WARNING: tested on 1080p and 1440p, borderless fullscreen, default ENGLISH font

---

## Overview

it's an overlay for CS/min

## usage

-   download and extract folder from releases. run CS Overlay.exe. profit (I hope. I only have one windows pc so it'll be a bother to test...).
-   look at system tray for settings (position, font size, custom format, advanced poll rates). settings save on exit.

## description/explanation/rambles

This app exists because I like to see my CS/min, but overwolf, op gg, u gg, blitz, overlays all cause my game to stutter. I assume this is because of something they do when internally reading game memory to get stats. Post vanguard, this is the only way to get stats like CS, which requires your code to be signed, and a certificate to do so costs a few hundred dollars per year.

This app started from https://github.com/vrevolverrr/league-cs-overlay

The original readme starts at the Creep Score Overlay heading.

Changes from the original are:

-   if 1 is the first digit, then it's 1 pixel thinner
    -   idk it's recent change or something but it meant 100s and teens were sometimes very wrong
    -   dynamically calculate next digit position accordingly
    -   I'm pretty sure the CS numbers are correct for all values, but you can enable Show CS in system tray to make sure it matches
-   tkinter -> win32 (ctypes)
    -   text is anti aliased
    -   doesn't show up in alt tab
    -   system tray stuff
-   windows functions using ctypes
    -   prevent mouse interaction (cursor won't change on hover or click)
    -   only show when league is the active window
-   PIL screenshot -> gdi capture (no PIL dependency)

buildscript.cmd uses python -m PyInstaller to make an executable

Made with 🤖 not ❤️ (i even asked copilot chat for the emojis)

---

EVERYTHING AFTER THIS POINT IS ABOUT THE ORIGINAL/INSPIRATION. LINKS WILL TAKE YOU TO HIS REPO

<h1 align="center">Creep Score Overlay</h1>

<p align="center">
  <b><small>✨ An overlay to show average creep score per minute in League of Legends ✨</small></b>
</p>

## Usage

Download the latest release [here](https://github.com/vrevolverrr/LeagueCSOverlay/releases/tag/v0.0.1) and run the executable! To change the font size, open notepad and type in your desired font size then save the file as "font.cfg" without double quotes in the same directory as the executable.

## Limitations

Currently only supports fullscreen borderless 1920x1080 resolution

## Explanation

A screnshot of the in game creep score counter is taken. The screenshot is cropped so that each frame only contains one digit exactly (10 px wide by 12 px tall).

<p align="center">
  <img src="https://raw.githubusercontent.com/vrevolverrr/LeagueCSOverlay/main/docs/example.png"></img>
</p>

The grayscale of the cropped frames are then compared to grayscale of target frames consisting of digits 0-9 and blank (no digit) to find the most similar digit. This is done by calculating the mean squared error (MSE) between the observed frame and each target frame.

The resulting number is then divided by the game time which is obtained through the game's [LiveClientAPI](https://developer.riotgames.com/docs/lol#game-client-api_live-client-data-api) to obtain the average creep score per minute.

The overlay is just a transparent Tkinter window.

<p align="center">
  <sub><strong>Made with ❤️ Bryan Soong</strong></sub><br>
</p>
