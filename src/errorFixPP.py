import os
import csv
import json
import re
import io
import sys


from Utils import count_txt_files_in_scenarios, count_txt_files_in_enhance, count_java_files, count_txt_files_in_enhance2

CSV_FILE = "path_temp.csv"  # CSV 파일
JSON_FOLDER = "./result"        # JSON 파일들이 들어있는 폴더
SOURCE_DIR = "./result"

def main():
    # 1) CSV 읽어서 rows에 저장
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
        
        fix_list = []

        if count_txt_files_in_enhance2() > 0 :
                for i in range(1, count_txt_files_in_enhance2() + 1) :
                    out_txt = os.path.join(SOURCE_DIR, f"{class_name}_{name}_2_{i}_Test_outMsg.txt")

                    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                        print(f"파일 존재 & 내용 있음: {out_txt}")
                        fix_list.append(out_txt)
                        # 여기에 처리할 로직 작성
        elif count_txt_files_in_enhance() > 0 :
                for i in range(1, count_txt_files_in_enhance() + 1) :
                    out_txt = os.path.join(SOURCE_DIR, f"{class_name}_{name}_1_{i}_Test_outMsg.txt")

                    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                        print(f"파일 존재 & 내용 있음: {out_txt}")
                        fix_list.append(out_txt)
                        # 여기에 처리할 로직 작성
        else : # 초기 테스트
            for i in range(1, count_txt_files_in_scenarios() + 1) :
                out_txt = os.path.join(SOURCE_DIR, f"{class_name}_{name}_0_{i}_Test_outMsg.txt")

                if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                    print(f"파일 존재 & 내용 있음: {out_txt}")
                    fix_list.append(out_txt)
                    # 여기에 처리할 로직 작성

        for f in fix_list:
            json_path = f.replace("Test_outMsg.txt", "fix_Test.json")
            save_path = f.replace("Test_outMsg.txt", "Test.java")
            if not os.path.exists(json_path):
                print(f"[ERROR] JSON 파일 없음: {json_path}")
                continue

            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
            except Exception as e:
                print(f"[ERROR] JSON 로드 실패: {json_path} ({e})")
                continue

            if "response" not in data:
                print(f"[WARN] {json_path} 내에 'response' 키가 없습니다. 건너뜁니다.")
                continue

            response_text = data["response"]
            CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)

            # 1) 정규식으로 ```json { ... } ``` 내부의 실제 JSON 문자열 찾기
            match = CODE_BLOCK_PATTERN.search(response_text)
            if not match:
                print(f"[WARN] {json_path}에서 ```json {{...}}``` 구조를 찾지 못했습니다.")
                continue

            # 2) 그룹(1)에 있는 { ... } 부분이 실제 JSON 객체
            json_string = match.group(1).strip()
            test_match = re.search(r'"FixedTest"\s*:\s*"(?P<content>.*?)"\s*,\s*"note"', json_string, re.DOTALL)
            if not test_match:
                print(f"[ERROR] 내부에서 'Test' 필드를 추출하지 못했습니다.")
                print("------ 문제가 된 코드블록 ------")
                continue
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
                    improvement_code = improvement_code.replace("```java", "")

            # 결과 저장

            with open(save_path, "w", encoding="utf-8") as out_file:
                out_file.write(improvement_code)

            print(f"[INFO] {save_path} 저장 완료.")


    return
    
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

    # 5) 매칭 처리
    for i, row in enumerate(rows):
        name = row["name"]  # CSV에서 'name' 열
        class_name = row["class"]  # CSV에서 'class' 열
        test_path = row["test"]  # CSV에서 'test' 열

        json_path = json_files[i]  # i번째로 결정된 JSON 경로
        
        # JSON 로드
        try:
            with open(json_path, "r", encoding="utf-8") as jf:
                data = json.load(jf)
        except Exception as e:
            print(f"[ERROR] JSON 로드 실패: {json_path} ({e})")
            continue

        if "response" not in data:
            print(f"[WARN] {json_path} 내에 'response' 키가 없습니다. 건너뜁니다.")
            continue
        
        response_text = data["response"]
        CODE_BLOCK_PATTERN = re.compile(r'```(?:json)?\s*(\{.*?\})\s*```', re.DOTALL)

        # 1) 정규식으로 ```json { ... } ``` 내부의 실제 JSON 문자열 찾기
        match = CODE_BLOCK_PATTERN.search(response_text)
        if not match:
            print(f"[WARN] {json_path}에서 ```json {{...}}``` 구조를 찾지 못했습니다.")
            continue

        # 2) 그룹(1)에 있는 { ... } 부분이 실제 JSON 객체
        json_string = match.group(1).strip()
        test_match = re.search(r'"FixedTest"\s*:\s*"(?P<content>.*?)"\s*,\s*"note"', json_string, re.DOTALL)
        if not test_match:
            print(f"[ERROR] 내부에서 'Test' 필드를 추출하지 못했습니다.")
            print("------ 문제가 된 코드블록 ------")
            continue
        raw_code_escaped = test_match.group(1)
        java_code = bytes(raw_code_escaped, "utf-8").decode("unicode_escape")

        improvement_code = java_code

        # 6) 결과 저장

        scenario_n = count_txt_files_in_scenarios()
        java_n = count_java_files(SOURCE_DIR)
        enhance_n = count_txt_files_in_enhance()
        enhance2_n = count_txt_files_in_enhance2()

        target = enhance_n
        if enhance2_n > 0 :
            target = enhance2_n
        if scenario_n - java_n != 0: # 개선 된 Case
            save_paths = []
            for i in range(1, target+1): #기본 case
                    unit_test_path = row.get("test", "").strip() + "\\" + row.get("class", "") + "_" +row.get("name", "").strip() +f"_1_{i}_Test.java"
                    path = row.get("class", "") + "_" +row.get("name", "").strip() +f"_1_{i}_Test.java"

                    if enhance2_n > 0 :
                        unit_test_path = row.get("test", "").strip() + "\\" + row.get("class", "") + "_" +row.get("name", "").strip() +f"_2_{i}_Test.java"
                        path = row.get("class", "") + "_" +row.get("name", "").strip() +f"_2_{i}_Test.java"
                    if os.path.exists(unit_test_path):
                        save_paths.append(path)
                    else:
                        break
            save_path = save_paths[-1]
        else :
            save_paths = []
            for i in range(1, scenario_n+1): #기본 case
                    unit_test_path = row.get("test", "").strip() + "\\" + row.get("class", "") + "_" +row.get("name", "").strip() +f"_0_{i}_Test.java"
                    path = row.get("class", "") + "_" +row.get("name", "").strip() +f"_0_{i}_Test.java"
                    if os.path.exists(unit_test_path):
                        save_paths.append(path)
                    else:
                        break
            save_path = save_paths[-1]

        target_file = os.path.join(JSON_FOLDER, save_path)

        output_filename = target_file
        
        print(output_filename)
        try:
            with open(output_filename, "w", encoding="utf-8") as out_file:
                out_file.write(improvement_code)
            print(f"[INFO] {os.path.basename(json_path)} → {os.path.basename(output_filename)} 저장 완료.")
        except Exception as e:
            print("파일저장 실패. 확인 요망.")


        
main()