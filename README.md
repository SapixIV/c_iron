# c_iron
a python script written with the help of ai for installing a carefully curated group of programs, and helping the user perform intial setup of those programs when they lack a gui.
This script performs the following tasks:

1. Verifies that:
   - It is running on Debian 12.
   - The desktop environment is KDE Plasma.
   - It is located in a folder that contains only:
       - This script file, and
       - (optionally) a folder named "log" (which it will create if needed).
   If any of these conditions is not met, it prints an error message and exits immediately without writing a log.

2. Checks if the program has run successfully before (via a marker file).

3. If it has NOT run before:
   a. Verifies that the following apt packages are installed:
         curl, gpg, pip, python3-pylsp, virt-manager, screenfetch, flatpak, plasma-discover-backend-flatpak.
      If any are missing, it runs:
         sudo apt update && sudo apt upgrade
      and then installs the missing packages.
   b. Adds the Flatpak repository "flathub" by executing:
         flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
      if not already added.
   c. Verifies that the following Flatpak apps are installed:
         Discord, VLC, RetroArch, Prism Launcher, qBittorrent, and Flatseal.
      If any are missing, it installs them using Flatpak.
   d. Executes two ZeroTier-related command sequences:
         i.  Import the ZeroTier GPG key and install ZeroTier.
         ii. Prompt the user for a ZeroTier network ID and join that network.
   e. Creates a marker file indicating that the initial setup completed successfully.
   f. Finally, prompts the user to reboot.

4. If the program has run before, it updates both apt and Flatpak packages.

5. All feedback is printed to the terminal. In the event of errors (with full stack traces), these are logged to a file in a folder named "log". Only the three most recent logs are kept – if a new log is created when there are already three, the oldest log file is deleted.
