import csv
import os
import shutil
from pathlib import Path
import sys
import io
import re


from Utils import count_java_files, count_txt_files_in_scenarios, count_txt_files_in_enhance, count_txt_files_in_enhance2

CSV_FILE = "path_temp.csv"      
SOURCE_DIR = "./result" 

def parse_error_lines(error_log_lines):
    """
    error_log_lines: 에러 로그 문자열 리스트
    return: 에러가 발생한 라인 번호 리스트(int)
    """
    error_line_numbers = []
    pattern = re.compile(r'\[(\d+),\d+\]')  
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

    blocks = []
    pattern_test_anno = re.compile(r'^\s*@Test\b')
    pattern_method_decl = re.compile(r'^\s*(public\s+)?void\s+\w+\s*\([^)]*\)\s*(throws\s+\w+(<[^>]+>)?(\s*,\s*\w+(<[^>]+>)?)*)?\s*\{')

    i = 0
    n = len(file_lines)
    while i < n:
        print(f"line {i}: {file_lines[i]}")
        if pattern_test_anno.match(file_lines[i]):
            j = i + 1
            while j < n and not pattern_method_decl.match(file_lines[j]):
                j += 1

            if j == n:
                print(f"@Test 발견: {i}, 메서드 선언 못 찾고 j == {j}")

                i = j
                continue

            start_line = j -1 
            brace_count = 0

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

    path = Path(file_path)
    lines = path.read_text(encoding='utf-8').splitlines()

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

    new_code = "\n".join(lines)
    return new_code

def target_main(target):
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  

        for row in reader:

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

   
                        path.write_text(result_code, encoding='utf-8')
                        print(f"✅ 주석 처리 완료: {target_file}")

            except Exception as e:
                print(f"Error: {e}")
def main() :

    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f) 

        for row in reader:
 
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
              
                elif count_txt_files_in_enhance() > 0 :
                    for i in range(1, count_txt_files_in_enhance() + 1) :
                        out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_1_{i}_Test_outMsg.txt")

                        if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                            print(f"파일 존재 & 내용 있음: {out_txt}")
                            fix_list.append(out_txt)
               
                else : # 
                    for i in range(1, count_txt_files_in_scenarios() + 1) :
                        out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_0_{i}_Test_outMsg.txt")

                        if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                            print(f"파일 존재 & 내용 있음: {out_txt}")
                            fix_list.append(out_txt)
           

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


    
                        result_code = comment_out_error_blocks(target_file, error_lines, method_blocks)

                        path.write_text(result_code, encoding='utf-8')
                        print(f"✅ 주석 처리 완료: {target_file}")

            except Exception as e:
                print(f"Error: {e}")
                
def all_comment() :
       with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)  

        for row in reader:

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
                   
                elif count_txt_files_in_enhance() > 0 :
                    for i in range(1, count_txt_files_in_enhance() + 1) :
                        out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_1_{i}_Test_outMsg.txt")

                        if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                            print(f"파일 존재 & 내용 있음: {out_txt}")
                            fix_list.append(out_txt)
                   
                else :
                    for i in range(1, count_txt_files_in_scenarios() + 1) :
                        out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_0_{i}_Test_outMsg.txt")

                        if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                            print(f"파일 존재 & 내용 있음: {out_txt}")
                            fix_list.append(out_txt)
                     

                for f in fix_list :
                    target_file = f.replace("_outMsg.txt", ".java").replace(SOURCE_DIR, test_path)
                    error_file = extract_error_lines(f)

                    path = Path(target_file)

                    if not path.exists():
                        print(f"❌ 주석 처리할 파일이 존재하지 않습니다: {target_file}")
                    else:
                        lines = path.read_text(encoding='utf-8').splitlines()
    

     
                        result_codes = [f"// {line}" for line in lines]
                        result_code = "\n".join(result_codes)
       


            
                        path.write_text(result_code, encoding='utf-8')
                        print(f"✅ 주석 처리 완료: {target_file}")

            except Exception as e:
                print(f"Error: {e}")

def target_all(target):
    with open(CSV_FILE, mode='r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)

        for row in reader:

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
