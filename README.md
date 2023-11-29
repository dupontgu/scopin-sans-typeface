## Generating the typeface
1. Install [`fontforge`](https://fontforge.org/) on your computer. You will not need to use the GUI, but the installation of the app will provide the Python hooks used by this script.
2. Download/clone this repo, and navigate to it's root directory using a terminal.
3. Create a Python virtual environment: `python3 -m venv . `
4. Edit your new `pyvenv.cfg` file to allow the use of system-site packages (this will allow the script to access `fontforge`). Set `include-system-site-packages = true` and save the file.
5. Install dependencies: `pip install -r requirements.txt`
6. Run the script: `python main.py`
7. Find the generate font files in `outputs/ScopinSans/{weight}.ttf`