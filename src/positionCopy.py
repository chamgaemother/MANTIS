import csv
import os
import shutil

import sys
import io

from Utils import count_txt_files_in_scenarios, count_java_files, count_txt_files_in_enhance, count_txt_files_in_enhance2

# 콘솔 출력 인코딩 설정


CSV_FILE = "path_temp.csv"       # CSV 파일 경로
SOURCE_DIR = "./result" # 복사할 원본 파일들이 있는 디렉터리


def initialCopy():
    # CSV 파일 열기
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  # 첫 줄 헤더(lib, class, path, test, name)를 기준으로 DictReader 사용
        for row in reader:
            # CSV 각 행에서 필요한 값 가져오기
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            try :
                num = count_txt_files_in_scenarios()
                for i in range(1, num + 1):
                    source_file = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_0_{i}_Test.java")
                    target_file = os.path.join(test_path, f"{class_value}_{name_value}_0_{i}_Test.java")

                    os.makedirs(os.path.dirname(target_file), exist_ok=True)
                    # 파일 복사
                    shutil.copy(source_file, target_file)
                    print(f"Copied: {source_file} -> {target_file}")
            except Exception as e:
                print(f"Error: {e}")
def enhanceCopy() :
    if count_txt_files_in_enhance2() > 0 :
        for i in range(count_txt_files_in_enhance2()) :
            enhanceCopy_m()
    else :
        for i in range(count_txt_files_in_enhance()) :
            enhanceCopy_m()
def enhanceCopy_m():
     with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  # 첫 줄 헤더(lib, class, path, test, name)를 기준으로 DictReader 사용
        for row in reader:
            # CSV 각 행에서 필요한 값 가져오기
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            try :
                num = count_txt_files_in_enhance()
                enhance2_n = count_txt_files_in_enhance2()
                if enhance2_n > 0 :
                    num = enhance2_n
                for i in range(1, num + 1):
                    source_file = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_1_{i}_Test.java")
                    target_file = os.path.join(test_path, f"{class_value}_{name_value}_1_{i}_Test.java")
                    if enhance2_n > 0:
                        source_file = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_2_{i}_Test.java")
                        target_file = os.path.join(test_path, f"{class_value}_{name_value}_2_{i}_Test.java")

                    if os.path.exists(target_file):
                        continue
                    else:
                        # 테스트 디렉터리가 존재하지 않을 수도 있으므로, 필요 시 생성
                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        # 파일 복사
                        shutil.copy(source_file, target_file)
                        print(f"Copied: {source_file} -> {target_file}")
                        break
            except Exception as e:
                print(f"Error: {e}")

def errorCopy():
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  # 첫 줄 헤더(lib, class, path, test, name)를 기준으로 DictReader 사용
        for row in reader:
            # CSV 각 행에서 필요한 값 가져오기
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            fix_list = []

            if count_txt_files_in_enhance2() > 0 :
                for i in range(1, count_txt_files_in_enhance2() + 1) :
                    out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_2_{i}_Test_outMsg.txt")

                    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                        print(f"파일 존재 & 내용 있음: {out_txt}")
                        fix_list.append(out_txt)
                        # 여기에 처리할 로직 작성
            elif count_txt_files_in_enhance() > 0 :
                for i in range(1, count_txt_files_in_enhance() + 1) :
                    out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_1_{i}_Test_outMsg.txt")

                    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                        print(f"파일 존재 & 내용 있음: {out_txt}")
                        fix_list.append(out_txt)
                        # 여기에 처리할 로직 작성
            else : # 초기 테스트
                for i in range(1, count_txt_files_in_scenarios() + 1) :
                    out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_0_{i}_Test_outMsg.txt")

                    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                        print(f"파일 존재 & 내용 있음: {out_txt}")
                        fix_list.append(out_txt)
                        # 여기에 처리할 로직 작성

            for f in fix_list :
                source_file = f.replace("_outMsg.txt", ".java")
                target_file = source_file.replace(SOURCE_DIR, test_path)
                # 파일 복사
                try :
                    shutil.copy(source_file, target_file)
                    print(f"Copied: {source_file} -> {target_file}")
  
                except Exception as e:
                    print(f"Error: {e}")

            return


            try :
                java_n = count_java_files()
                scenario_n = count_txt_files_in_scenarios()
                enhance_n = count_txt_files_in_enhance()
                enhance2_n = count_txt_files_in_enhance2()
                if java_n == scenario_n :
                    targets = []
                    sources = []
                    for i in range(1, scenario_n + 1):
                        source_file = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_0_{i}_Test.java")
                        target_file = os.path.join(test_path, f"{class_value}_{name_value}_0_{i}_Test.java")

                        if os.path.exists(target_file):
                            targets.append(target_file)
                            sources.append(source_file)
                            continue
                        else:
                            break
                    target_file = targets[-1]
                    source_file = sources[-1]
                else :
                    targets = []
                    sources = []
                    target = enhance_n
                    if enhance2_n > 0:
                        target = enhance2_n
                    for i in range(1, target + 1):
                        source_file = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_1_{i}_Test.java")
                        target_file = os.path.join(test_path, f"{class_value}_{name_value}_1_{i}_Test.java")
                        if enhance2_n > 0 :
                            source_file = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_2_{i}_Test.java")
                            target_file = os.path.join(test_path, f"{class_value}_{name_value}_2_{i}_Test.java")

                        if os.path.exists(target_file):
                            targets.append(target_file)
                            sources.append(source_file)
                            continue
                        else:
                            break
                    target_file = targets[-1]
                    source_file = sources[-1]
                # 테스트 디렉터리가 존재하지 않을 수도 있으므로, 필요 시 생성
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                # 파일 복사
                shutil.copy(source_file, target_file)
                print(f"Copied: {source_file} -> {target_file}")
       
            except Exception as e:
                print(f"Error: {e}")
    
if __name__ == "__main__": 
    errorCopy()