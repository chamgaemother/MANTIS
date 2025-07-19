import os
import csv
import json
import re

import ast
import sys
import io

from Utils import count_java_files, count_txt_files_in_scenarios, count_txt_files_in_enhance, count_txt_files_in_enhance2

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
            # 종료 블록 만남
            return "\n".join(lines[start_index + 1:i])  # 내용만 반환
        elif in_json_block:
            block_lines.append(line)

    return None  # 못 찾은 경우

def main():
    # 1) CSV 읽기
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    # 2) 각 row별 JSON 처리
    for row in rows:
        lib = row["lib"]
        name = row["name"]
        class_name = row["class"]

        enhance2_n = count_txt_files_in_enhance2()
        enhance_n = count_txt_files_in_enhance()

        target = enhance_n
        if enhance2_n > 0:
            target = enhance2_n

        for i in range(1, target + 1):
            json_filename = f"{lib}_{name}_1_{i}_Test.json"
            if enhance2_n > 0 :
                json_filename = f"{lib}_{name}_2_{i}_Test.json"

            json_path = os.path.join(JSON_FOLDER, json_filename)

            if not os.path.exists(json_path):
                print(f"[ERROR] JSON 파일 없음: {json_path}")
                continue

            # JSON 로드
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
            except Exception as e:
                print(f"[ERROR] JSON 로드 실패: {json_path} ({e})")
                continue

            # 응답 필드 파싱
            if "response" not in data:
                print(f"[WARN] {json_filename} 내에 'response' 키가 없습니다. 건너뜁니다.")
                continue

            response_text = data["response"]
            # CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
            # match = CODE_BLOCK_PATTERN.search(response_text)
            # if not match:
            #     print(f"[WARN] {json_filename}에서 ```json {{...}}``` 구조를 찾지 못했습니다.")
            
            json_string = extract_outer_json_block(response_text)

            #json_string = match.group(1).strip()
            test_match = re.search(r'"Test"\s*:\s*"(?P<content>.*?)"\s*,\s*"note"', json_string, re.DOTALL)
            if not test_match:
                print(f"[ERROR] {json_filename} 내부에서 'Test' 필드를 추출하지 못했습니다.")
                return False
            raw_code_escaped = test_match.group(1)
            java_code = bytes(raw_code_escaped, "utf-8").decode("unicode_escape")

            improvement_code = java_code

            if "```java" in improvement_code:
                
                # 1단계: 정규식으로 ```java { ... } ``` 내부의 실제 Java 문자열 찾기
                match = re.search(r'```java\s*(.*?)\s*```', improvement_code, re.DOTALL)
                if match:
                    # 2단계: 그룹(1)에 있는 { ... } 부분이 실제 Java 코드
                    java_code = match.group(1).strip()
                    improvement_code = java_code
                else : 
                    improvement_code = java_code.replace("```java", "")

            # 결과 저장
            if enhance2_n > 0:
                output_filename = os.path.join(
                JSON_FOLDER, f"{class_name}_{name}_2_{i}_Test.java"
                )
            else :
                output_filename = os.path.join(
                    JSON_FOLDER, f"{class_name}_{name}_1_{i}_Test.java"
                )
            with open(output_filename, "w", encoding="utf-8") as out_file:
                out_file.write(improvement_code)

            print(f"[INFO] {json_filename} → {output_filename} 저장 완료.")

    return True        

if __name__ == "__main__":
    main()
