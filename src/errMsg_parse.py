from Utils import count_txt_files_in_scenarios, count_txt_files_in_enhance, count_txt_files_in_enhance2
import csv
import os
import re


CSV_FILE = "path_temp.csv"  # CSV 파일
log_dir = "./error_logs"
result_dir = "./result"


def err_parse() :
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  # 첫 줄 헤더(lib, class, path, test, name)를 기준으로 DictReader 사용
        for row in reader:
            # CSV 각 행에서 필요한 값 가져오기
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            target_txt= ""
            target_list = []
            save_dict = dict()

            if count_txt_files_in_enhance2() > 0 :
                    i = count_txt_files_in_enhance2()
                    target_txt = os.path.join(log_dir, f"{class_value}_{name_value}_2_{i}_Test_outMsg.txt")
                    for j in range(1, i +1) :
                        target_list.append(f"{class_value}_{name_value}_2_{j}_Test")
                        save_dict[f"{class_value}_{name_value}_2_{j}_Test"] = []
                        # 여기에 처리할 로직 작성
            elif count_txt_files_in_enhance() > 0 :
                    i = count_txt_files_in_enhance()
                    target_txt = os.path.join(log_dir, f"{class_value}_{name_value}_1_{i}_Test_outMsg.txt")
                    for j in range(1, i +1) :
                        target_list.append(f"{class_value}_{name_value}_1_{j}_Test")
                        save_dict[f"{class_value}_{name_value}_1_{j}_Test"] = []
                        # 여기에 처리할 로직 작성
            else : # 초기 테스트
                print("초기테스트")
                i = count_txt_files_in_scenarios()
                target_txt = os.path.join(log_dir, f"{class_value}_{name_value}_0_{i}_Test_outMsg.txt")
                for j in range(1, i +1) :
                    target_list.append(f"{class_value}_{name_value}_0_{j}_Test")
                    save_dict[f"{class_value}_{name_value}_0_{j}_Test"] = []
            
   # === 실제 파싱 =====================================================
            if not os.path.exists(target_txt):
                print("⚠️  파일이 없습니다:", target_txt)
                continue

            with open(target_txt, encoding="utf-8") as log_f:
                current_target = None  # 지금 모으는 대상 테스트 이름

                for line in log_f:
                    if "[ERROR]" not in line:
                        # ERROR 블록이 끝났다고 가정
                        current_target = None
                        continue

                    # 1) 새로운 테스트-오류의 첫 줄인가?
                    matched = next(
                        (t for t in target_list if t in line), None
                    )
                    if matched:
                        current_target = matched
                        save_dict[matched].append(line)
                        continue

                    # 2) 직전에 잡힌 테스트-오류의 연속 줄인가?
                    if current_target:
                        save_dict[current_target].append(line)

            # === 결과 저장 =====================================================
            for key, lines in save_dict.items():
                if not lines:
                    continue
                out_path = os.path.join(result_dir, f"{key}_outMsg.txt")
                with open(out_path, "w", encoding="utf-8") as out_f:
                    out_f.writelines(lines)
                print(f"✅ {out_path} 저장 완료 ({len(lines)} lines)")

