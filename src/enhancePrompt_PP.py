import os
import csv
import json
import re

import sys
import io

# 콘솔 출력 인코딩 설정

from Utils import count_txt_files_in_enhance
CSV_FILE = "path_temp.csv"  # CSV 파일
JSON_FOLDER = "./result"       # JSON 파일들이 들어있는 폴더

def main():
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    # 2) JSON 폴더 내 JSON 파일 목록
    #    ※ 수정 시각(최신 순)으로 정렬
    json_files = [
        fn for fn in os.listdir(JSON_FOLDER)
        if fn.lower().endswith(".json")
    ]
    # 파일 경로를 전체로 만들어서 정렬
    full_paths = [os.path.join(JSON_FOLDER, f) for f in json_files]
    # 최신(가장 나중에 수정된) → 먼저
    full_paths.sort(key=os.path.getmtime, reverse=True)

    # 이제 full_paths는 가장 최근 수정된 파일이 맨 앞
    
    # 3) CSV 행 수와 비교
    if len(full_paths) > len(rows):
        # JSON 파일이 너무 많을 때 → 가장 최근 파일들만 rows 개수만큼 사용
        full_paths = full_paths[:len(rows)]
    elif len(full_paths) < len(rows):
        print(f"[ERROR] JSON 파일 수({len(full_paths)})가 CSV 행 수({len(rows)})보다 적습니다.")
        return

    # full_paths를 다시 최신 순에서 오래된 순으로 정렬하거나,
    # 혹은 그대로 사용하는 등 원하는 정책을 정하면 됨.
    # 여기선 '가장 최근 n개'를 골라낸 뒤 그대로 인덱스로 매칭한다.
    
    # 4) 최종 JSON 파일 목록
    #   (여기서는 '가장 최근 n개'를 CSV와 1:1로 순서대로 매칭)
    json_files = full_paths  # 변수명 재사용

    # 3) 순서대로 매칭 처리
    for i, row in enumerate(rows):
        name = row["name"]  # CSV에서 'name' 열
        lib = row["lib"]  # CSV에서 'lib' 열
        json_path = os.path.join(json_files[i])

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
        if count_txt_files_in_enhance() > 0:
            output_filename = os.path.join(
            JSON_FOLDER, f"{lib}_{name}_2enhance_scenarios.txt"
            )
        else :
            output_filename = os.path.join(
                JSON_FOLDER, f"{lib}_{name}_enhance_scenarios.txt"
            )
        with open(output_filename, "w", encoding="utf-8") as out_file:
            #out_file.write(improvement_code)
            out_file.write(json_string)

        print(f"[INFO] {json_path} → {output_filename} 저장 완료.")

if __name__ == "__main__":
    main()
