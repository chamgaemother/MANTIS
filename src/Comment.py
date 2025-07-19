import csv
import os
import shutil
from pathlib import Path
import sys
import io
import re


from Utils import count_java_files, count_txt_files_in_scenarios, count_txt_files_in_enhance, count_txt_files_in_enhance2

CSV_FILE = "path_temp.csv"       # CSV 파일 경로
SOURCE_DIR = "./result" # 복사할 원본 파일들이 있는 디렉터리

def parse_error_lines(error_log_lines):
    """
    error_log_lines: 에러 로그 문자열 리스트
    return: 에러가 발생한 라인 번호 리스트(int)
    """
    error_line_numbers = []
    pattern = re.compile(r'\[(\d+),\d+\]')  # [filepath:[line,col]]

    for line in error_log_lines:
        if 'package' in line.lower():
            continue
        m = pattern.search(line)
        if m:
            line_num = int(m.group(1))
            error_line_numbers.append(line_num)

    return error_line_numbers

def extract_error_lines(file_path):
    error_lines = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith('[ERROR]'):
                error_lines.append(line.strip())
    return error_lines

def extract_test_method_line_blocks(file_lines):
    """
    file_lines: 파일 내용을 라인별로 나눈 리스트
    return: [[start_line, end_line], ...] (1-based line numbering)
    """
    blocks = []
    pattern_test_anno = re.compile(r'^\s*@Test\b')
    pattern_method_decl = re.compile(r'^\s*(public\s+)?void\s+\w+\s*\([^)]*\)\s*(throws\s+\w+(<[^>]+>)?(\s*,\s*\w+(<[^>]+>)?)*)?\s*\{')

    i = 0
    n = len(file_lines)
    while i < n:
        print(f"라인 {i}: {file_lines[i]}")
        if pattern_test_anno.match(file_lines[i]):
            # 다음 줄부터 메서드 선언 찾기 (한두 줄 안에 있을 거라 가정)
            j = i + 1
            while j < n and not pattern_method_decl.match(file_lines[j]):
                j += 1

            if j == n:
                print(f"@Test 발견: {i}, 메서드 선언 못 찾고 j == {j}")
                # 메서드 선언 못 찾음
                i = j
                continue

            start_line = j -1 # 1-based 라인번호
            brace_count = 0
            # 현재 줄부터 중괄호 열고 닫히는 지점 찾기
            for k in range(j, n):
                brace_count += file_lines[k].count('{')
                brace_count -= file_lines[k].count('}')
                if brace_count == 0:
                    end_line = k + 1
                    blocks.append([start_line, end_line])
                    i = k
                    break
        i += 1

    return blocks

def comment_out_error_blocks(file_path, error_lines, method_blocks):
    """
    file_path: 수정할 java 파일 경로 (Path or str)
    error_lines: 에러가 발생한 라인 번호 리스트
    method_blocks: [[start_line, end_line], ...] 테스트 메서드 라인 범위 리스트

    에러 라인이 포함된 메서드 블록을 주석 처리 (블록 주석 /* ... */)
    """
    path = Path(file_path)
    lines = path.read_text(encoding='utf-8').splitlines()

    # 에러 라인이 포함된 블록 인덱스 찾기
    blocks_to_comment = []
    for idx, (start, end) in enumerate(method_blocks):
        for err_line in error_lines:
            if start <= err_line <= end:
                blocks_to_comment.append(idx)
                break

    print(blocks_to_comment)
    for idx in blocks_to_comment:
        start, end = method_blocks[idx]
        
        for i in range(start - 1, end):
            if not lines[i].lstrip().startswith("//"):
                lines[i] = "// " + lines[i]

    # 결과 저장 또는 출력
    new_code = "\n".join(lines)
    return new_code

def target_main(target):
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  # 첫 줄 헤더(lib, class, path, test, name)를 기준으로 DictReader 사용

        for row in reader:
            # CSV 각 행에서 필요한 값 가져오기
            lib_value   = row['lib']
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            try :
                    target_out = os.path.join(SOURCE_DIR, target + "_outMsg.txt")
                    target = target + ".java"
                    target_file = os.path.join(test_path, target )
                    error_file = extract_error_lines(target_out)

                    path = Path(target_file)

                    if not path.exists():
                        print(f"❌ 주석 처리할 파일이 존재하지 않습니다: {target_file}")
                    else:
                        lines = path.read_text(encoding='utf-8').splitlines()
                        method_blocks = extract_test_method_line_blocks(lines)
                        print(f"테스트 메서드 블록: {method_blocks}")
                        error_lines = parse_error_lines(error_file)
                        print(f"에러 라인: {error_lines}")

                        result_code = comment_out_error_blocks(target_file, error_lines, method_blocks)

                        # # 결과 저장
                        path.write_text(result_code, encoding='utf-8')
                        print(f"✅ 주석 처리 완료: {target_file}")

            except Exception as e:
                print(f"Error: {e}")
def main() :
    # CSV 파일 열기
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  # 첫 줄 헤더(lib, class, path, test, name)를 기준으로 DictReader 사용

        for row in reader:
            # CSV 각 행에서 필요한 값 가져오기
            lib_value   = row['lib']
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            try :

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
                    target_file = f.replace("_outMsg.txt", ".java").replace(SOURCE_DIR, test_path)
                    error_file = extract_error_lines(f)

                    path = Path(target_file)

                    if not path.exists():
                        print(f"❌ 주석 처리할 파일이 존재하지 않습니다: {target_file}")
                    else:
                        lines = path.read_text(encoding='utf-8').splitlines()
                        method_blocks = extract_test_method_line_blocks(lines)
                        print(f"테스트 메서드 블록: {method_blocks}")
                        error_lines = parse_error_lines(error_file)
                        print(f"에러 라인: {error_lines}")


                        # 3. 에러 포함된 블록 주석 처리
                        result_code = comment_out_error_blocks(target_file, error_lines, method_blocks)
                        # print(f"주석 처리된 코드:\n{result_code}")

                        # 각 줄 앞에 // 추가
                        # commented_lines = [f"// {line}" for line in lines]

                        # # 결과 저장
                        path.write_text(result_code, encoding='utf-8')
                        print(f"✅ 주석 처리 완료: {target_file}")

            except Exception as e:
                print(f"Error: {e}")
                
def all_comment() :
       with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  # 첫 줄 헤더(lib, class, path, test, name)를 기준으로 DictReader 사용

        for row in reader:
            # CSV 각 행에서 필요한 값 가져오기
            lib_value   = row['lib']
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            try :

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
                    target_file = f.replace("_outMsg.txt", ".java").replace(SOURCE_DIR, test_path)
                    error_file = extract_error_lines(f)

                    path = Path(target_file)

                    if not path.exists():
                        print(f"❌ 주석 처리할 파일이 존재하지 않습니다: {target_file}")
                    else:
                        lines = path.read_text(encoding='utf-8').splitlines()
                        # method_blocks = extract_test_method_line_blocks(lines)
                        # print(f"테스트 메서드 블록: {method_blocks}")
                        # error_lines = parse_error_lines(error_file)
                        # print(f"에러 라인: {error_lines}")


                        # 3. 에러 포함된 블록 주석 처리
                        result_codes = [f"// {line}" for line in lines]
                        result_code = "\n".join(result_codes)
                        # print(f"주석 처리된 코드:\n{result_code}")

                        # 각 줄 앞에 // 추가
                        # commented_lines = [f"// {line}" for line in lines]

                        # # 결과 저장
                        path.write_text(result_code, encoding='utf-8')
                        print(f"✅ 주석 처리 완료: {target_file}")

            except Exception as e:
                print(f"Error: {e}")

def target_all(target):
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  # 첫 줄 헤더(lib, class, path, test, name)를 기준으로 DictReader 사용

        for row in reader:
            # CSV 각 행에서 필요한 값 가져오기
            lib_value   = row['lib']
            class_value = row['class']
            test_path   = row['test']
            name_value  = row['name']

            try :
                    target_out = os.path.join(SOURCE_DIR, target + "_outMsg.txt")
                    target = target + ".java"
                    
                    target_file = os.path.join(test_path, target )
                    error_file = extract_error_lines(target_out)

                    path = Path(target_file)

                    if not path.exists():
                        print(f"❌ 주석 처리할 파일이 존재하지 않습니다: {target_file}")
                    else:
                        lines = path.read_text(encoding='utf-8').splitlines()
                        result_codes = []

                        for line in lines:
                            stripped_line = line.lstrip()
                            if (stripped_line.startswith("//") or
                                stripped_line.startswith("package") or
                                stripped_line.startswith("public class")):
                                result_codes.append(line)
                            else:
                                result_codes.append(f"// {line}")
                        result_codes.append("}")

                        result_code = "\n".join(result_codes)
                        path.write_text(result_code, encoding='utf-8')
                        print(f"✅ 주석 처리 완료: {target_file}")


            except Exception as e:
                print(f"Error: {e}")
