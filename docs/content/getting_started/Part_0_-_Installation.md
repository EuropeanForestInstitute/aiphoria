# Part 0 - Installation

## Prerequisites
- Python 3.9+

All the following steps assumes that the Python is already installed and path / environment variables are properly set.
Tested in Windows 10 / Windows 11 / Ubuntu 24.04.<br>
These instruction steps are for command line / shell and does not cover how to do this in IDE (for example VS Code, PyCharm).
---

## 1. Download or clone the repository
You can clone the repository using git or download the compressed repository as ZIP.

**Either:**
1) Clone the repository
```
git clone https://github.com/EuropeanForestInstitute/aiphoria.git aiphoria
```

or download the repository by going to [aiphoria GitHub repository](https://github.com/EuropeanForestInstitute/aiphoria) clicking the green "Code" button and selecting "Download as ZIP"


After that change current working directory to aiphoria by running
```
cd aiphoria
```

---
## 2. Create Python virtual environment
Create Python virtual environment for storing libraries locally inside aiphoria directory.
It's also possible to install required libraries system-wide but using virtual environments
has multiple benefits:
-  Easy to create multiple "setups" for different Python versions
- No need to install Python libraries system-wide
- Easier to replicate and track down issues with different library versions

NOTE: Last parameter (env) is the name of the directory where Python will install virtual environment
and this can be changed to another name if needed (e.g. name to reflect used python version)

```
python -m venv venv
```

---
## 2. Activate virtual environment
Windows:
```
venv\Scripts\activate.bat
```

Linux:
```
source venv/bin/activate
```

---
## 3. Install all the dependencies
```
pip install -r docs/requirements.txt
```

---
### 3.1. (Optional) Convert Jupyter Notebook file to Python file
Example scenario is provided as Jupyter Notebook file and needs to be converted to Python file.<br>
If you use IDE that supports Notebook files then this step is not needed.
```
jupyter nbconvert --to script example.ipynb
```

---
## 4. Run the example scenario
This will run example scenario and generate output to "output" directory.
```
python example.py data/example_data.xlsx
```

> NOTE: You can also run the example.ipynb in IDE (PyCharm, VS Code, etc.) that supports Jupyter Notebooks.

---
## 5. Check the results
All output is generated to directory named "output". Each subdirectory in "output" is results for alternative scenario defined in data file (refer aiphoria documentation about scenarios).<br>
Output-directory will always contain at least directory "Baseline" that contains results for the baseline scenario results (if there is no other alternatives scenarios defined).<br><br>
If alternative scenarios are defined in data file (check sheet "Scenarios" in example data file):<br>
- Results for each alternative scenarios are created as subdirectories to "output" and have the same name as the alternative scenario 
<br>

In the next part we go through the example scenario step-by-step and explain what happens in each step.<br> 
<br>
Next part: [Part 1 - Example scenario explained](Part_1_-_Example_scenario_explained.md)
