# MANTIS : Multi-Agent based Unit-Test Generation

----------
# Requirement
pip install -r requirement.txt

---------
# How to run?
### Step 1: Configure your test targets in `lib_path_total.csv`

Make sure your CSV file has the following columns (one row per method):

- **lib**: Name of the target project  
  _Example:_ `commons-codec`
- **class**: Name of the target class  
  _Example:_ `Md5Crypt`
- **method**: Name of the target method  
  _Example:_ `md5Crypt`
- **path**: Path to the target class file (relative or absolute)  
  - Relative: `.\main\java\org\apache\commons\codec\digest\Md5Crypt.java`  
  - Absolute: `C:\Users\…\main\java\org\apache\commons\codec\digest\Md5Crypt.java`
- **test**: Package path for the test folder (relative or absolute)  
  _Example:_ `.\test\java\org\apache\commons\codec\digest`
- **name**: Identifier for the test (often same as the method name)  
  _Example:_ `md5Crypt`
- **folder**: Path to the test folder (relative or absolute)  
  _Example:_ `.\test`
- **method_signature**: Full signature of the target method  
  _Example:_ `public static String md5Crypt(byte[] data)`

### Step 2: Configure the settings file

In your config (e.g. `config.py`), set the following fields:

- **API_KEY**: Your OpenAI API key  
  _Example:_ `"sk-ABC123yourapikey"`
- **CONFIG_JSON**: Path to the preprocessed data JSON  
  _Example:_ `"/preprocess_data/cod_all_methods.json"


### Step 3: Run the core MANTIS pipeline

```python main.py``` : 
Generates MANTIS el.0.

```python main_enhance.py``` : 
Based on MANTIS el.N, generates MANTIS el.N+1 (up to 2 iterations).

### Step 4: Measure Coverage

- Check the log file for coverage metrics and the number of times each agent ran.  
- To collect project-level coverage, run:
  ```mvn jacoco:report```
  
