import csv
import json
import re

import ast
import sys
import io

from Utils import count_txt_files_in_scenarios



CSV_FILE = "path_temp.csv"
JSON_FOLDER = "./result"


def extract_outer_json_block(text):
    lines = text.splitlines()
    in_json_block = False
    block_lines = []
    start_index = None

    for i, line in enumerate(lines):
        if not in_json_block and line.strip() == "```json":
            in_json_block = True
            start_index = i
            continue
        elif in_json_block and line.strip() == "```":
            # 
            return "\n".join(lines[start_index + 1:i])  # 
        elif in_json_block:
            block_lines.append(line)

    return None  # 

def main():
    # 1) CSV 
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # 2)
    for row in rows:
        lib = row["lib"]
        name = row["name"]
        class_name = row["class"]
        for i in range(1, count_txt_files_in_scenarios()+1):
            json_filename = f"{lib}_{name}_0_{i}_Test.json"
            json_path = os.path.join(JSON_FOLDER, json_filename)

            if not os.path.exists(json_path):
                print(f"[ERROR] JSON not found: {json_path}")
                continue

            # 
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
            except Exception as e:
                print(f"[ERROR] JSON road fail : {json_path} ({e})")
                continue

            # 응답 필드 파싱
            if "response" not in data:
                print(f"[WARN] {json_filename} 내에 'response' 키가 없습니다. 건너뜁니다.")
                continue

            response_text = data["response"]
            # CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
            # match = CODE_BLOCK_PATTERN.search(response_text)
            # if not match:

            
            json_string = extract_outer_json_block(response_text)

            #json_string = match.group(1).strip()

            print(json_string)
            
            test_match = re.search(r'"Test"\s*:\s*"(?P<content>.*?)"\s*,\s*"note"', json_string, re.DOTALL)
            if not test_match:
                print(f"[ERROR] in {json_filename} 'Test' field not found")
                return False
            raw_code_escaped = test_match.group(1)
            java_code = bytes(raw_code_escaped, "utf-8").decode("unicode_escape")



            improvement_code = java_code

            if "```java" in improvement_code:
       
                match = re.search(r'```java\s*(.*?)\s*```', improvement_code, re.DOTALL)
                if match:

                    java_code = match.group(1).strip()
                    improvement_code = java_code
                else : 
                    improvement_code = improvement_code.replace("```java", "")


            output_filename = os.path.join(
                JSON_FOLDER, f"{class_name}_{name}_0_{i}_Test.java"
            )
            with open(output_filename, "w", encoding="utf-8") as out_file:
                out_file.write(improvement_code)

            print(f"[INFO] {json_filename} → {output_filename} ")

    return True        

if __name__ == "__main__":
    main()
