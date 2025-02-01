#!/usr/bin/env python3
"""
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
"""

import os
import sys
import subprocess
import shutil
import logging
import datetime
import glob
import traceback

# -----------------------------------------------------------------------------
# Global variables and constants
# -----------------------------------------------------------------------------

# Get the directory where this script resides.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Name of the logs folder (must be exactly "log")
LOG_FOLDER = "log"

# Marker file indicating that the initial setup has run successfully.
MARKER_FILE = os.path.join(SCRIPT_DIR, ".setup_complete")

# List of required apt packages and the command that should exist if installed.
APT_REQUIREMENTS = {
    "curl": "curl",
    "gpg": "gpg",
    "pip": "pip",  # some systems might install pip as "pip" or "pip3"
    "python3-pylsp": "pylsp",  # command after installation
    "virt-manager": "virt-manager",
    "screenfetch": "screenfetch",
    "flatpak": "flatpak",
    "plasma-discover-backend-flatpak": "plasma-discover-backend-flatpak",
}

# Dictionary of required Flatpak apps (Friendly Name: Flatpak Application ID).
FLATPAK_REQUIREMENTS = {
    "Discord": "com.discordapp.Discord",
    "VLC": "org.videolan.VLC",
    "RetroArch": "org.libretro.RetroArch",
    "Prism Launcher": "org.prismlauncher.PrismLauncher",
    "qBittorrent": "org.qbittorrent.qBittorrent",
    "Flatseal": "com.github.tchx84.Flatseal"
}

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def verify_directory_contents() -> None:
    """
    Verify that the script is running in a folder that contains only:
      - This script, and
      - Optionally, a folder named 'log'.
    If any other files or directories exist (excluding hidden files starting with '.'),
    print an error and exit immediately (without logging).
    """
    allowed = {os.path.basename(__file__), LOG_FOLDER}
    contents = [item for item in os.listdir(SCRIPT_DIR) if not item.startswith('.')]
    for item in contents:
        if item not in allowed:
            print("Error: The folder must contain only this script and (optionally) a folder named 'log'.")
            sys.exit(1)


def verify_os_and_desktop() -> None:
    """
    Verify that the operating system is Debian 12 and that the desktop environment is KDE Plasma.
    If not, print an error and exit immediately without writing to a log.
    """
    # Verify OS version by reading /etc/os-release
    try:
        with open("/etc/os-release", "r") as f:
            lines = f.readlines()
    except Exception:
        print("Error: Unable to read /etc/os-release. This script requires Debian 12 with KDE Plasma.")
        sys.exit(1)

    os_info = {}
    for line in lines:
        if "=" in line:
            key, val = line.strip().split("=", 1)
            os_info[key] = val.strip('"')

    if os_info.get("ID", "").lower() != "debian" or os_info.get("VERSION_ID", "") != "12":
        print("Error: This script must be run on Debian 12.")
        sys.exit(1)

    # Check for KDE Plasma desktop using XDG_CURRENT_DESKTOP environment variable.
    desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "")
    if not ("KDE" in desktop_env or "Plasma" in desktop_env):
        print("Error: This script must be run on the KDE Plasma desktop environment.")
        sys.exit(1)


def setup_logging() -> str:
    """
    Set up logging so that errors and feedback are written to a log file in the log folder.
    Only the three most recent log files are kept (oldest is deleted if necessary).
    Returns the full path to the new log file.
    """
    log_path = os.path.join(SCRIPT_DIR, LOG_FOLDER)
    os.makedirs(log_path, exist_ok=True)

    # Get list of existing log files (with .log extension) sorted by modification time.
    log_files = sorted(glob.glob(os.path.join(log_path, "*.log")), key=os.path.getmtime)
    if len(log_files) >= 3:
        try:
            os.remove(log_files[0])
        except Exception as e:
            print(f"Warning: Could not remove old log file {log_files[0]}: {e}")

    log_filename = os.path.join(log_path, datetime.datetime.now().strftime("%Y%m%d_%H%M%S.log"))
    logging.basicConfig(
        level=logging.DEBUG,
        filename=log_filename,
        filemode="w",
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return log_filename


def check_command_exists(command: str) -> bool:
    """Return True if the command exists in PATH; otherwise, return False."""
    return shutil.which(command) is not None


def run_subprocess(command: list[str], shell: bool = False) -> str:
    """
    Run a subprocess command.
    Prints its stdout to the terminal.
    If the command fails, logs the error (with stack trace) and exits.
    """
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        cmd_str = command if shell else " ".join(command)
        error_msg = f"Error running command '{cmd_str}': {e.stderr}"
        logging.error(error_msg)
        logging.error(traceback.format_exc())
        print(f"Error: {e.stderr}")
        sys.exit(1)


def update_and_install_apt_packages(missing: list[str]) -> None:
    """
    Run 'sudo apt update' and 'sudo apt upgrade' and install missing apt packages.
    """
    print("Running 'sudo apt update'...")
    run_subprocess(["sudo", "apt", "update"])
    print("Running 'sudo apt upgrade -y'...")
    run_subprocess(["sudo", "apt", "upgrade", "-y"])
    if missing:
        print(f"Installing missing apt packages: {missing}")
        run_subprocess(["sudo", "apt", "install", "-y"] + missing)
    else:
        print("All required apt packages are installed.")


def update_apt_packages() -> None:
    """Update the system's apt packages."""
    print("Updating apt packages...")
    run_subprocess(["sudo", "apt", "update"])
    run_subprocess(["sudo", "apt", "upgrade", "-y"])


def update_flatpak_packages() -> None:
    """Update installed Flatpak packages."""
    print("Updating Flatpak packages...")
    run_subprocess(["flatpak", "update", "-y"])


def add_flathub_repo() -> None:
    """Add the Flathub repository for Flatpak if it is not already added."""
    print("Adding Flatpak Flathub repository (if not already added)...")
    run_subprocess([
        "flatpak", "remote-add", "--if-not-exists", "flathub",
        "https://dl.flathub.org/repo/flathub.flatpakrepo"
    ])


def install_flatpak_apps(missing_apps: dict[str, str]) -> None:
    """
    Install missing Flatpak applications.
    :param missing_apps: A dictionary where keys are friendly names and values are Flatpak app IDs.
    """
    for app_name, app_id in missing_apps.items():
        print(f"Installing Flatpak app: {app_name} ({app_id})...")
        run_subprocess(["flatpak", "install", "flathub", app_id, "-y"])


def perform_zerotier_commands() -> None:
    """
    Execute the ZeroTier commands:
       1. Import the GPG key from ZeroTier and, if a value is produced by 'curl -s https://install.zerotier.com/ | gpg',
          pipe it into sudo bash.
       2. Prompt the user for a ZeroTier network ID and join that network.
    """
    print("Importing ZeroTier GPG key and installing ZeroTier...")
    zerotier_command = (
        "curl -s 'https://raw.githubusercontent.com/zerotier/ZeroTierOne/main/doc/contact%40zerotier.com.gpg' | gpg --import && "
        "if z=$(curl -s 'https://install.zerotier.com/' | gpg); then echo \"$z\" | sudo bash; fi"
    )
    run_subprocess(zerotier_command, shell=True)

    # Prompt for the ZeroTier network ID
    network_id = input("Enter the ZeroTier network ID to join: ").strip()
    if not network_id:
        print("Error: No ZeroTier network ID provided. Exiting.")
        sys.exit(1)

    print(f"Joining ZeroTier network '{network_id}'...")
    run_subprocess(["sudo", "zerotier-cli", "join", network_id])


# -----------------------------------------------------------------------------
# Main Setup Functions
# -----------------------------------------------------------------------------

def initial_setup() -> None:
    """
    Perform the initial installation steps:
      - Check and install missing apt packages.
      - Add the Flathub repository.
      - Check and install missing Flatpak apps.
      - Run the ZeroTier commands.
      - Create a marker file indicating successful initial setup.
      - Finally, prompt the user to reboot.
    """
    # Check required apt packages.
    missing_apt = []
    for package, command in APT_REQUIREMENTS.items():
        if not check_command_exists(command):
            missing_apt.append(package)

    update_and_install_apt_packages(missing_apt)

    # Add Flathub repository.
    add_flathub_repo()

    # Check required Flatpak apps.
    try:
        result = subprocess.run(
            ["flatpak", "list", "--app", "--columns=application"],
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        installed_flatpaks = result.stdout.split()
    except subprocess.CalledProcessError as e:
        logging.error("Error listing Flatpak apps: " + str(e))
        installed_flatpaks = []

    missing_flatpaks = {}
    for app_name, app_id in FLATPAK_REQUIREMENTS.items():
        if app_id not in installed_flatpaks:
            missing_flatpaks[app_name] = app_id

    if missing_flatpaks:
        print("Missing Flatpak apps:", list(missing_flatpaks.keys()))
        install_flatpak_apps(missing_flatpaks)
    else:
        print("All required Flatpak apps are installed.")

    # Execute the ZeroTier commands.
    perform_zerotier_commands()

    # Create a marker file indicating successful initial setup.
    try:
        with open(MARKER_FILE, "w") as f:
            f.write("Setup completed successfully.\n")
    except Exception as e:
        logging.error("Failed to create marker file: " + str(e))
        print("Warning: Unable to create marker file.")

    # Finally, prompt for reboot.
    input("Initial setup complete. Press Enter to reboot...")
    run_subprocess(["sudo", "reboot"])


def update_system() -> None:
    """
    If the program has run before, update both apt and Flatpak packages.
    """
    update_apt_packages()
    update_flatpak_packages()


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

def main() -> None:
    # (1) Verify the folder contents before logging.
    verify_directory_contents()

    # (2) Verify OS and desktop environment before logging.
    verify_os_and_desktop()

    # Now that conditions are met, set up logging.
    log_file = setup_logging()
    print(f"Logging to: {log_file}")

    try:
        # (3) Check if this is the first run or a subsequent update.
        if not os.path.exists(MARKER_FILE):
            print("Initial setup not detected. Proceeding with full installation.")
            initial_setup()
        else:
            print("Initial setup previously completed. Updating packages...")
            update_system()
    except Exception as e:
        # Log any unexpected exceptions with full stack trace.
        logging.error("An unexpected error occurred: " + str(e))
        logging.error(traceback.format_exc())
        print("An unexpected error occurred. Please check the log file for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
