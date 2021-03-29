import platform

BOTTLE_FILE_SUFFIX = "bottle.tar.gz"
SYSTEM = platform.system()
IS_LINUX = SYSTEM == "Linux"
IS_MAC_OS = SYSTEM == "Darwin"

MAC_VER_TO_CODENAME = {
    "10.13": "High Sierra",
    "10.14": "Mojave",
    "10.15": "Catalina",
    "10.16": "Big Sur",
    "11.0": "Big Sur",
    "11.1": "Big Sur",
    "11.2": "Big Sur",
}
