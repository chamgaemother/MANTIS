import subprocess
import sys
import io
import os
import shutil
import csv
from datetime import datetime
from collections import defaultdict
import re

from Utils import count_java_files, count_txt_files_in_scenarios, extract_params
step_count = defaultdict(int)
LOG_FILE_PATH = './result/logs.txt'
SOURCE_DIR = "./result" 
input_file = 'lib_path_total.csv'
output_file = 'path_temp.csv'
from genScenario import main as genScenario
from Prompt_PP import main as Prompt_PP
from Scenario_PP import main as Scenario_PP
from genPartTest import main as genPartTest
from InitialTest_PP import main as InitialTest_PP
from changeClassNameFromFile import main as changeClassNameFromFile
from positionCopy import initialCopy, enhanceCopy, errorCopy
from errorFix import main as errorFix
from errorFixPP import main as errorFixPP
from Comment import main as Comment, all_comment, target_main, target_all
from errMsg_parse import err_parse

from ExeAndCov import main as ExeAndCov


"""
1. genPrompt
2. Prompt pp
3. gen initialTest
4. initialTest pp
5. changeClassNameFromFile
6. position
7. execute
8. errorFix
9. errorFixPP
10. enhanceCov
11. enhanceCovPP
"""

def log_step(step_name, phase):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{step_name}] {phase}"
    

    print(log_line)

    os.makedirs('./result', exist_ok=True)
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')
    if phase == "END":
        step_count[step_name] += 1

def gen_prompt():
    step = "Scenario_Gen"
    log_step(step, "START")
    genScenario()
    log_step(step, "END")

def prompt_post_process():
    step = "Scenario_PP"
    log_step(step, "START")
    Prompt_PP()
    Scenario_PP()
    log_step(step, "END")

def gen_initial_test():
    step = "InitialTest_Gen"
    log_step(step, "START")
    genPartTest()
    log_step(step, "END")

def initial_test_post_process():
    step = "InitialTest_PP"
    log_step(step, "START")
    InitialTest_PP()
    log_step(step, "END")


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
        print("branch coverage:", branch_cov)
        return 1

def error_fix():
    step = "Error_Fix"
    log_step(step, "START")

    errorFix()
    errorFixPP()
    log_step(step, "END")

def count_check(class_value, name_value):
    fix_list = []
    i = count_txt_files_in_scenarios()
    for i in range(1, count_txt_files_in_scenarios() + 1) :
        out_txt = os.path.join(SOURCE_DIR, f"{class_value}_{name_value}_0_{i}_Test_outMsg.txt")

        if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 :
            print(f"file existed: {out_txt}")
            fix_list.append(f"{class_value}_{name_value}_0_{i}_Test")

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
        gen_prompt()
        prompt_post_process()
    except Exception as e :
        print(e)

    try : 
        while True:
            gen_initial_test()
            initial_test_post_process()
            if count_java_files() ==  count_txt_files_in_scenarios():
                break
    except Exception as e :
        print(e)

    try :
        change_class_name_from_file()
    except Exception as e :
        print(e)

    scenario_n = count_txt_files_in_scenarios()

    scenario_fix_count = dict()
    for i in range(1, scenario_n+1) :
        scenario_fix_count[f"{class_value}_{method_value}_0_{i}_Test"] = 0


    try :
        initialCopy()
    except Exception :
        print(Exception)

    fix_count = 0

    while(fix_count < max(scenario_n, 5)) :
        result = execute_test()    
        if result == 0:
                print("⚠️⚠️Execute InitialTest Error")
                return 0

        elif result == 1: 
                break

        elif result == 2: 
                      
                err_parse()
                target = count_check(class_value, method_value)

                comment_flag = False

                if len(target) == 0 :

                    all_comment()
                    break
                for t in target :
                    print(t)
                    print(scenario_fix_count[t])
                    if scenario_fix_count[t] == 3 :
                        target_main(t)
                        comment_flag = True
                        scenario_fix_count[t] +=1
                    elif scenario_fix_count[t] > 3 :
                        target_all(t)
                        comment_flag = True
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

    if fix_count  ==  max(scenario_n, 5):
        print("---------------------------------------------------------")
        print(f"final fix check")
        print("---------------------------------------------------------")
        
        result = execute_test(1)      
        if result != 1:

            Comment()
            result = execute_test()

            if result == 1 :
                print("next")
            else :
                print("")
                all_comment()
                # delete_path(SOURCE_DIR)
                # print(count_txt_files_in_scenarios())
                # input("계속 삭제하려면 .. ")
                # for i in range(1, count_txt_files_in_scenarios() + 1) :
                #     delete_path(os.path.join(test_path, f"{class_value}_{method_value}_0_{i}_Test.java"))
                # return 0




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
            test = row[4]
            name = row[2]
            sig = row[7]

            param = extract_params(sig)

            result_base_path = './agtTest'
            new_folder = f"{lib}_{class_name}_{name}_result"
            # new_folder = f"{lib}_{class_name}_{name}_{param}_result"

            if os.path.exists(new_folder):
                print(f"warn: {new_folder} → main() skip")
                continue

            with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(header)  
                writer.writerow(row)     

            print(f"{i} LINE RUNING:", row)
            print("======= START =======")
            result = main(class_name, name, test)
            print("======= FINISH =======")

            if result == 0 :
                continue

            old_folder = "./result"
            

            if os.path.exists(old_folder):
                if os.path.exists(new_folder):
                    shutil.rmtree(new_folder)
                os.rename(old_folder, new_folder)
                print(f"{old_folder} → {new_folder}")
            else:
                print(f"not found: {old_folder}")   
