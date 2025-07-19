import subprocess
import sys
import io
import os
import shutil
import csv
from datetime import datetime
from collections import defaultdict
import re

from Utils import count_java_files, count_txt_files_in_scenarios, count_txt_files_in_enhance, count_txt_files_in_enhance2
step_count = defaultdict(int)
LOG_FILE_PATH = './result/enhance_logs.txt'
SOURCE_DIR = "./result" 
input_file = 'lib_path_total.csv'
output_file = 'path_temp.csv'

from genEnhanceScenario import main as EnhanceScenario
from enhancePrompt_PP import main as enhancePrompt_PP
from enhanceScenario_PP import main as enhanceScenario_PP
from genEnhancePartTest import main as genEnhanceTest
from enhanceTest_PP import main as enhanceTest_PP
from changeClassNameFromFile import main as changeClassNameFromFile
from positionCopy import initialCopy, enhanceCopy, errorCopy
from errorFix import main as errorFix
from errorFixPP import main as errorFixPP
from Comment import main as Comment, all_comment, target_main, target_all
from errMsg_parse import err_parse

from ExeAndCov import main as ExeAndCov


def log_step(step_name, phase):
    global LOG_FILE_PATH
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{step_name}] {phase}"
    

    print(log_line)

    os.makedirs('./result', exist_ok=True)
    if count_txt_files_in_enhance() > 0:
        LOG_FILE_PATH = './result/2enhance_logs.txt'
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')
    if phase == "END":
        step_count[step_name] += 1

def change_class_name_from_file():
    step = "ChangeName_PP"
    log_step(step, "START")
    changeClassNameFromFile()
    log_step(step, "END")

def execute_test(final_loop_flag=0):
    global line_cov, branch_cov
    step = "Execute"
    log_step(step, "START")
    line_cov, branch_cov = ExeAndCov()

    if line_cov == "-" or branch_cov =="-":

        return 2
    else :
        print("line coverage:", line_cov)
        print("brach coverage:", branch_cov)
        return 1
        
def error_fix():
    step = "Error_Fix"
    log_step(step, "START")
    errorFix()
    errorFixPP()
    log_step(step, "END")       

def gen_prompt():
    step = "Enhance Scenario_Gen"
    log_step(step, "START")
    EnhanceScenario()
    log_step(step, "END")

def prompt_post_process():
    step = "Enhance Scenario_PP"
    log_step(step, "START")
    enhancePrompt_PP()
    enhanceScenario_PP()
    log_step(step, "END")

def gen_enhance_test():
    step = "enhanceTest_Gen"
    log_step(step, "START")
    genEnhanceTest()
    log_step(step, "END")

def enhance_test_post_process():
    step = "enhanceTest_PP"
    log_step(step, "START")
    enhanceTest_PP()
    log_step(step, "END")

def count_check(class_value, name_value):
    fix_list = []
    scenario_n = count_txt_files_in_enhance()
    scenario2_n = count_txt_files_in_enhance2()

    if scenario2_n > 0 :
        for i in range(1, count_txt_files_in_scenarios() + 1) :
            out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_2_{i}_Test_outMsg.txt")

            if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                print(f"error file existed: {out_txt}")
                fix_list.append(f"{class_value}_{name_value}_2_{i}_Test")
    else :
        for i in range(1, count_txt_files_in_scenarios() + 1) :
            out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_1_{i}_Test_outMsg.txt")

            if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
                print(f"error file existed: {out_txt}")
                fix_list.append(f"{class_value}_{name_value}_1_{i}_Test")

    return fix_list
def delete_path(path):
    if os.path.isfile(path):
        os.remove(path)

    elif os.path.isdir(path):
        shutil.rmtree(path)
 
    else:
        print(f"⚠️ : {path}")

def main(class_value, method_value, test_path):
    try : 
        EnhanceScenario()
        prompt_post_process()
    except Exception as e :
        print(e)

    if count_txt_files_in_enhance2() == 0 and count_txt_files_in_enhance == 0 :

        return 1
    elif count_txt_files_in_enhance2==0 and count_txt_files_in_enhance > 0:

        return 1

    try : 
        while True:
            gen_enhance_test()
            enhance_test_post_process()
            if count_java_files() ==  count_txt_files_in_scenarios() + count_txt_files_in_enhance() + count_txt_files_in_enhance2() :
                break
    except Exception as e :
        print(e)

    try :
        change_class_name_from_file()
    except Exception as e :
        print(e)


    scenario_n = count_txt_files_in_enhance()
    scenario2_n = count_txt_files_in_enhance2()

    target_n = scenario_n
    if scenario2_n > 0 :
        target_n = scenario2_n

    scenario_fix_count = dict()
    if scenario2_n > 0 :
        for i in range(1, scenario2_n+1) :
            scenario_fix_count[f"{class_value}_{method_value}_2_{i}_Test"] = 0
    else : 
        for i in range(1, scenario_n+1) :
            scenario_fix_count[f"{class_value}_{method_value}_1_{i}_Test"] = 0

    try :
            enhanceCopy()
    except Exception :
            print(Exception)


    fix_count = 0

    while(fix_count < max(target_n, 5)) :
        result = execute_test()    
        if result == 0:

                return 0

        elif result == 1:
                break

        elif result == 2: 
                err_parse()
                target = count_check(class_value, method_value)
                if len(target) == 0 :
       
                    all_comment()
                    break

                comment_flag = False
                for t in target :
                    print(t)
                    print(scenario_fix_count[t])
                    if scenario_fix_count[t] == 3 :
                        target_main(t)
                        comment_flag = True
                        scenario_fix_count[t] +=1
                    elif scenario_fix_count[t] == 4 :
                        target_all(t)
                        scenario_fix_count[t] +=1
                        comment_flag = True
                    elif scenario_fix_count[t] > 4 :
                        all_comment()
                        return 1
                if comment_flag :
                    continue
                for t in target :        
                    scenario_fix_count[t] +=1    

                fix_count += 1
                print("---------------------------------------------------------")
                print(f"⚠️⚠️ Error Fix Count: {fix_count}")     
                print("---------------------------------------------------------") 
                try :
                    error_fix()
                except Exception :
                    print(Exception)
                change_class_name_from_file()
                errorCopy()
    if fix_count  ==  max(target_n, 5):
        print("---------------------------------------------------------")
        print(f"Final Fix check")
        print("---------------------------------------------------------")
        
        result = execute_test(1)      
        if result != 1:

            Comment()
            result = execute_test()

            if result == 1 :
                print("next line")
            else :
         
                all_comment()
                # delete_path(SOURCE_DIR)

                # for i in range(1, target + 1) :
                #     if scenario2_n > 0 :
                #         print(os.path.join(test_path, f"{class_value}_{method_value}_2_{i}_Test.java"))
                #         delete_path(os.path.join(test_path, f"{class_value}_{method_value}_2_{i}_Test.java"))
                #     else : 
                #         print(os.path.join(test_path, f"{class_value}_{method_value}_1_{i}_Test.java"))
                #         delete_path(os.path.join(test_path, f"{class_value}_{method_value}_1_{i}_Test.java"))
                # return 0


    # if line_cov == 0 or branch_cov == 0:
    #         print("삭제 추후 재 실행")
    #         delete_path(SOURCE_DIR)
    #         for i in range(1, target + 1) :
    #                 if scenario2_n > 0 :
    #                     print(os.path.join(test_path, f"{class_value}_{method_value}_2_{i}_Test.java"))
    #                     delete_path(os.path.join(test_path, f"{class_value}_{method_value}_2_{i}_Test.java"))
    #                 else : 
    #                     print(os.path.join(test_path, f"{class_value}_{method_value}_1_{i}_Test.java"))
    #                     delete_path(os.path.join(test_path, f"{class_value}_{method_value}_1_{i}_Test.java"))
    #         return 0

    print("\n========================")
    print("📊 Step Execution Summary")
    print("========================")
    result_data = []
    for step, count in step_count.items():
            result_data.append(f"- {step} : {count}")
    cov_data = f"line_cov : {line_cov}, branch_cov : {branch_cov}"
    result_data.append(cov_data)
    result_data.append(str(scenario_fix_count))
    results = "\n".join(result_data)
    print(results)
    os.makedirs('./result', exist_ok=True)
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
            f.write(results + '\n')
    print("========================")
    return 1


if __name__ == "__main__":
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = list(csv.reader(infile))  
        header = reader[0]  
        data_rows = reader[1:]  

        for i, row in enumerate(data_rows, start=2):  

            lib = row[0]
            class_name = row[1]
            name = row[2]
            test = row[4]

            result_base_path = './agtTest'
            old_folder = f"{lib}_{class_name}_{name}_result"
            new_folder = f"{lib}_{class_name}_{name}_enhance_result"

            if os.path.exists(new_folder):
                new_folder = f"{lib}_{class_name}_{name}_2enhance_result"
                old_folder = f"{lib}_{class_name}_{name}_enhance_result"
                print(f"2th enhance loop start.")
                if os.path.exists(new_folder): 
                    print(f"warm: {new_folder} → main() skip")
                    input("continue press enter...")
                    continue
            else :
                continue



            test_folder = "./result"
            if os.path.exists(old_folder):
                # 기존 새 폴더 있으면 삭제하고 덮어쓰기
                if os.path.exists(test_folder):
                    shutil.rmtree(test_folder)
                os.rename(old_folder, test_folder)
                print(f"폴더 이름 변경 완료: {old_folder} → {test_folder}")
            else:
                print(f"폴더 없음: {old_folder}")   


            with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(header)  # 고정 1줄
                writer.writerow(row)     # 현재 줄

            print(f"{i}번째 줄 처리 중:", row)
            main(class_name, name, test)

            if "2enhance_result" in new_folder:
                if count_java_files() < count_txt_files_in_scenarios() + count_txt_files_in_enhance() + count_txt_files_in_enhance2():
                    print("폴더 삭제 요망")
                    input("⚠️⚠️ InitialTest Error. Press Enter to continue...")
            else :
                if count_java_files() < count_txt_files_in_scenarios() + count_txt_files_in_enhance():
                    print("폴더 삭제 요망")
                    input("⚠️⚠️ InitialTest Error. Press Enter to continue...")
            

            if os.path.exists(test_folder):
                # 기존 새 폴더 있으면 삭제하고 덮어쓰기
                if os.path.exists(new_folder):
                    shutil.rmtree(new_folder)
                os.rename(test_folder, new_folder)
                print(f"폴더 이름 변경 완료: {test_folder} → {new_folder}")
            else:
                print(f"폴더 없음: {old_folder}")   

