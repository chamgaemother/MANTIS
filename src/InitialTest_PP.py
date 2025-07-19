import csv
import json
import re

import ast
import sys
import io

from Utils import count_txt_files_in_scenarios

# 콘솔 출력 인코딩 설정


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
        for i in range(1, count_txt_files_in_scenarios()+1):
            json_filename = f"{lib}_{name}_0_{i}_Test.json"
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

            print(json_string)
            
            test_match = re.search(r'"Test"\s*:\s*"(?P<content>.*?)"\s*,\s*"note"', json_string, re.DOTALL)
            if not test_match:
                print(f"[ERROR] {json_filename} 내부에서 'Test' 필드를 추출하지 못했습니다.")
                return False
            raw_code_escaped = test_match.group(1)
            java_code = bytes(raw_code_escaped, "utf-8").decode("unicode_escape")

            # try:
            #     parsed = ast.literal_eval(json_string)
            #     response_json = json.loads(json.dumps(parsed))  # 딕셔너리로 변환
            #     print(f"[OK] {json_filename} 파싱 성공")
            # except (ValueError, SyntaxError) as e:
            #     print(f"[ERROR] {json_filename} 코드블록 내부가 JSON 형식이 아닙니다: {e}")
            #     print("------ 문제가 된 코드블록 ------")
            #     print(json_string[:500] + "\n...")
            #     continue

            # if "Test" not in java_code:
            #     print(f"[WARN] {json_filename} 내에 'Test' 키가 없습니다. 건너뜁니다.")
            #     continue

            improvement_code = java_code

            if "```java" in improvement_code:
                # 1단계: 정규식으로 ```java { ... } ``` 내부의 실제 Java 문자열 찾기
                match = re.search(r'```java\s*(.*?)\s*```', improvement_code, re.DOTALL)
                if match:
                    # 2단계: 그룹(1)에 있는 { ... } 부분이 실제 Java 코드
                    java_code = match.group(1).strip()
                    improvement_code = java_code
                else : 
                    improvement_code = improvement_code.replace("```java", "")

            # 결과 저장
            output_filename = os.path.join(
                JSON_FOLDER, f"{class_name}_{name}_0_{i}_Test.java"
            )
            with open(output_filename, "w", encoding="utf-8") as out_file:
                out_file.write(improvement_code)

            print(f"[INFO] {json_filename} → {output_filename} 저장 완료.")

    return True        

if __name__ == "__main__":
    main()
