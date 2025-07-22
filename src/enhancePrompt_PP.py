import os
import csv
import json
import re

import sys
import io



from Utils import count_txt_files_in_enhance
CSV_FILE = "path_temp.csv"  
JSON_FOLDER = "./result"       

def main():
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
  
    json_files = [
        fn for fn in os.listdir(JSON_FOLDER)
        if fn.lower().endswith(".json")
    ]

    full_paths = [os.path.join(JSON_FOLDER, f) for f in json_files]
  
    full_paths.sort(key=os.path.getmtime, reverse=True)

    
  
    if len(full_paths) > len(rows):
   
        full_paths = full_paths[:len(rows)]
    elif len(full_paths) < len(rows):
        print(f"[ERROR]")
        return


    json_files = full_paths 


    for i, row in enumerate(rows):
        name = row["name"]  #
        lib = row["lib"]  # 
        json_path = os.path.join(json_files[i])

        # JSON 
        try:
            with open(json_path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
        except Exception as e:
            print(f"[ERROR] JSON load fail: {json_path} ({e})")
            continue

        # data["response"] 
        if "response" not in data:
            print(f"[WARN] in {json_path}  'response' key not found. skip.")
            continue
        response_text = data["response"]
        CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)

        match = CODE_BLOCK_PATTERN.search(response_text)
        if not match:
            print(f"[WARN] in {json_path} ```json {{...}}``` format not foubd")
            json_string = response_text
        else :
       
            json_string = match.group(1).strip()


        if count_txt_files_in_enhance() > 0:
            output_filename = os.path.join(
            JSON_FOLDER, f"{lib}_{name}_2enhance_scenarios.txt"
            )
        else :
            output_filename = os.path.join(
                JSON_FOLDER, f"{lib}_{name}_enhance_scenarios.txt"
            )
        with open(output_filename, "w", encoding="utf-8") as out_file:
    
            out_file.write(json_string)

        print(f"[INFO] {json_path} → {output_filename} save.")

if __name__ == "__main__":
    main()
