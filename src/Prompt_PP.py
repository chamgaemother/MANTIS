import os
import csv
import json
import re

import sys
import io

# 콘솔 출력 인코딩 설정


CSV_FILE = "path_temp.csv"  # CSV 파일
JSON_FOLDER = "./result"       # JSON 파일들이 들어있는 폴더

def main():
    # 1) CSV 읽어서 rows에 저장
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    # 2) JSON 폴더 내 JSON 파일 목록 (파일명으로 정렬)
    json_files = [fn for fn in os.listdir(JSON_FOLDER) if fn.lower().endswith(".json")]
    json_files.sort()  # 예: ["20230327.json", "20230328.json", "20230329.json", ...]

    # CSV 행 수와 JSON 파일 수가 달라지면 매칭 오류
    if len(json_files) != len(rows):
        print(f"[ERROR] JSON 파일 수({len(json_files)})와 CSV 행 수({len(rows)})가 일치하지 않습니다.")
        return

    # 3) 순서대로 매칭 처리
    for i, row in enumerate(rows):
        name = row["name"]  # CSV에서 'name' 열
        lib = row["lib"]  # CSV에서 'lib' 열
        json_path = os.path.join(JSON_FOLDER, json_files[i])

        # JSON 로드
        try:
            with open(json_path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
        except Exception as e:
            print(f"[ERROR] JSON 로드 실패: {json_path} ({e})")
            continue

        # data["response"] 확인
        if "response" not in data:
            print(f"[WARN] {json_path} 내에 'response' 키가 없습니다. 건너뜁니다.")
            continue
        response_text = data["response"]
        CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)
        # 1) 정규식으로 ```json { ... } ``` 내부의 실제 JSON 문자열 찾기
        match = CODE_BLOCK_PATTERN.search(response_text)
        if not match:
            print(f"[WARN] {json_path}에서 ```json {{...}}``` 구조를 찾지 못했습니다.")
            json_string = response_text
        else :
            # 2) 그룹(1)에 있는 { ... } 부분이 실제 JSON 객체
            json_string = match.group(1).strip()

        # # 3) 이 부분을 다시 json.loads로 파싱
        # try:
        #     response_json = json.loads(json_string)
        # except json.JSONDecodeError as e:
        #     print(f"[ERROR] {json_path} 코드블록 내부가 JSON 형식이 아닙니다: {e}")
        #     continue


        # # scenarios 키 확인
        # if "scenarios" not in response_json:
        #     print(f"[WARN] {json_path} 내에 'scenarios' 키가 없습니다. 건너뜁니다.")
        #     continue

        # improvement_code = response_json["scenarios"]
        

        # 5) 결과 저장 (출력 위치를 4o-mini-3m4w 폴더 내로 변경)
        output_filename = os.path.join(
            JSON_FOLDER, f"{lib}_{name}_scenarios.txt"
        )
        with open(output_filename, "w", encoding="utf-8") as out_file:
            #out_file.write(improvement_code)
            out_file.write(json_string)

        print(f"[INFO] {json_path} → {output_filename} 저장 완료.")

if __name__ == "__main__":
    main()
