import openai
import os
import datetime
import json
import pandas as pd
import io
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Custom Config Class
from config import Config
from Utils import chat_with_openai, count_txt_files_in_scenarios, count_txt_files_in_enhance, count_java_files, load_prompt, count_txt_files_in_enhance2, extract_method_body, are_signatures_equal

# OpenAI Client initialize
client = openai.OpenAI(api_key=Config.get_api_key())


PROMPT_DIR = Config.get_prompt_dir()

SYSTEM_PROMPT_PATH = "./prompt/errorFix System.txt"
USER_PROMPT_PATH = "./prompt/errorFix User.txt"
AI_PROMPT_PATH = "./prompt/errorFix AI.txt"
JSON_PATH = Config.get_json_path()
SOURCE_DIR = "./result"


def extract_error_lines(file_path):
    error_lines = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.startswith('[ERROR]'):
                error_lines.append(line.strip())
    return error_lines

def save_response(response_obj, model, system_prompt, user_prompt):
   
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")  # YYYYMMDD_HHMMSS 
    filename = f"{timestamp}_{model}_response.json"
    directory = "./result" 
    os.makedirs(directory, exist_ok=True)  # 
    filepath = os.path.join(directory, filename)

    # JSON 
    response_data = {
        "info": {
            "model": model,
            "finish_reason": response_obj.choices[0].finish_reason,
            "usage": {
                "completion_tokens": response_obj.usage.completion_tokens,
                "prompt_tokens": response_obj.usage.prompt_tokens,
                "total_tokens": response_obj.usage.total_tokens,
                "completion_tokens_details": {
                    "accepted_prediction_tokens": response_obj.usage.completion_tokens_details.accepted_prediction_tokens,
                    "audio_tokens": response_obj.usage.completion_tokens_details.audio_tokens,
                    "reasoning_tokens": response_obj.usage.completion_tokens_details.reasoning_tokens,
                    "rejected_prediction_tokens": response_obj.usage.completion_tokens_details.rejected_prediction_tokens
                },
                "prompt_tokens_details": {
                    "audio_tokens": response_obj.usage.prompt_tokens_details.audio_tokens,
                    "cached_tokens": response_obj.usage.prompt_tokens_details.cached_tokens
                }
            }
        },
        "prompt": {
            "system_prompt": system_prompt if system_prompt else "None",
            "user_prompt": user_prompt
        },
        "response": response_obj.choices[0].message.content
    }

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(response_data, file, indent=4, ensure_ascii=False)

    print(f"✅ : {filepath}")


def process_prompt_file(err_file_name, file_path, library_name, class_name, name, original_code, target_dict,
                        user_prompt, system_prompt, ai_prompt, model, unit_test) :

    if not os.path.exists(err_file_name):
        return f"-- : {err_file_name}"
    
    with open(err_file_name, "r", encoding="utf-8") as pf:
        out_Msg = pf.read()

    user_prompt_modified = user_prompt.replace("{ Library Name }", library_name)
    user_prompt_modified = user_prompt_modified.replace("{ Class Name }", class_name)
    user_prompt_modified = user_prompt_modified.replace("{ Insert existing JUnit 5 test code here }", unit_test)
    user_prompt_modified = user_prompt_modified.replace("{ CLASS_BODY }", original_code)
    user_prompt_modified = user_prompt_modified.replace("{ CLASS_NAME }", target_dict["clazz"])
    user_prompt_modified = user_prompt_modified.replace("{ METHOD_NAME }", target_dict["methodName"])
    user_prompt_modified = user_prompt_modified.replace("{ VISIBILITY }", target_dict["visibility"])
    user_prompt_modified = user_prompt_modified.replace("{ METHOD_SIGNATURE }", target_dict["signature"])
    #user_prompt_modified = user_prompt_modified.replace("{ METHOD_BODY }", target_dict["body"])
    user_prompt_modified = user_prompt_modified.replace("{ NODE }", str(target_dict["nodes"]))
    user_prompt_modified = user_prompt_modified.replace("{ EDGE }", str(target_dict["edges"]))
    user_prompt_modified = user_prompt_modified.replace("{ FLOW_SUMMARY }", '\n'.join(target_dict["flowSummary"]))
    user_prompt_modified = user_prompt_modified.replace("{ CYCLOMATIC_COMPLEXITY }", str(target_dict["cc"]))
    user_prompt_modified = user_prompt_modified.replace("{ BLOCK_LIST }", '\n'.join(target_dict["blockList"]))
    user_prompt_modified = user_prompt_modified.replace("{ BLOCK_EDGES }", '\n'.join(target_dict["blockEdges"]))
    user_prompt_modified = user_prompt_modified.replace("{ DEP_CLASS }", '\n'.join(str(dep_method) for dep_method in target_dict["depClasses"]))
    user_prompt_modified = user_prompt_modified.replace("{ DEP_METHOD }", '\n'.join(str(dep_method) for dep_method in target_dict["depMethods"]))

    chain_response_obj, chain_response_text = chat_with_openai(
        model, system_prompt, ai_prompt, user_prompt_modified
    )

    if isinstance(chain_response_obj, str):
        return chain_response_obj
    
    save_filename = err_file_name.replace("Test_outMsg.txt", "fix_Test.json")
    save_path = save_filename

    print("save path : ", save_path)

    response_data = {
                    "info": {
                        "model": model,
                        "finish_reason": chain_response_obj.choices[0].finish_reason,
                        "usage": {
                            "completion_tokens": chain_response_obj.usage.completion_tokens,
                            "prompt_tokens": chain_response_obj.usage.prompt_tokens,
                            "total_tokens": chain_response_obj.usage.total_tokens,
                    
                            "completion_tokens_details": {
                                "accepted_prediction_tokens": chain_response_obj.usage.completion_tokens_details.accepted_prediction_tokens,
                                "audio_tokens": chain_response_obj.usage.completion_tokens_details.audio_tokens,
                                "reasoning_tokens": chain_response_obj.usage.completion_tokens_details.reasoning_tokens,
                                "rejected_prediction_tokens": chain_response_obj.usage.completion_tokens_details.rejected_prediction_tokens
                            },
                            "prompt_tokens_details": {
                                "audio_tokens": chain_response_obj.usage.prompt_tokens_details.audio_tokens,
                                "cached_tokens": chain_response_obj.usage.prompt_tokens_details.cached_tokens
                            }
                        }
                    },
                    "prompt": {
                        "system_prompt": system_prompt if system_prompt else "None",
                        "user_prompt": user_prompt_modified
                    },
                    "response": chain_response_obj.choices[0].message.content
                }

    with open(save_path, "w", encoding="utf-8") as sf:
        json.dump(response_data, sf, indent=4, ensure_ascii=False)

    return f"-- finish result save: {save_filename}"
    


def main():
    print("💬 OpenAI Chat start")


    while True:
        
        model_choice = '1'

        if model_choice in Config.MODEL_MAP:
            model = Config.MODEL_MAP[model_choice]
            print(f"✅ model `{model}` selected.\n")
            break
        else:
            print("❌ .")


    system_prompt = load_prompt(SYSTEM_PROMPT_PATH) 
    ai_prompt = load_prompt(AI_PROMPT_PATH) 
    user_prompt = load_prompt(USER_PROMPT_PATH)
    json_file = Path(JSON_PATH)

    if not user_prompt:
        print("❌ `user.txt` not found. please check `/prompt/user.txt` file")
        exit()

    if model != "o1-mini" and not system_prompt:
        print("⚠️ `system.txt` file is empty. please check `/prompt/system.txt`.")

    with json_file.open(encoding="utf-8") as f:
        data = json.load(f)            # → Python list[ dict ]

    print("🎤 model and prompt finish!")


    path_file = "path_temp.csv"
    df = pd.read_csv(path_file, encoding="cp949")
    futures = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for idx, row in df.iterrows():
            file_path = str(row.get("path", "")).strip()
            library_name = str(row.get("lib", "")).strip()
            class_name = str(row.get("class", "")).strip()
            name = str(row.get("name", "")).strip()
            method_signature = row.get("method_signiture", "").strip()
            test_path = row.get("test", "").strip()

            if not file_path or not os.path.exists(file_path):
                print(f"-- path is empty: {file_path}")
                continue

            target_dict = dict()

            for d in data:
                if class_name in d["clazz"] and name in d["methodName"]:
                    result = are_signatures_equal(d["signature"], method_signature)
                    if result :
                        target_dict = d
                        break

            with open(file_path, "r", encoding="utf-8") as code_file:
                original_code = code_file.read()

            if not target_dict:
                print(f"-- target method infomation less: {class_name}.{name}")
                continue

            fix_list = []
            unit_tests = dict()
            fix_list = []

            if count_txt_files_in_enhance2() > 0 :
                for i in range(1, count_txt_files_in_enhance2() + 1) :
                    out_txt = os.path.join(SOURCE_DIR, f"{class_name}_{name}_2_{i}_Test_outMsg.txt")
                    unit_test_path = os.path.join(test_path, f"{class_name}_{name}_2_{i}_Test.java")
                    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 and os.path.exists(unit_test_path):
                        print(f"target : {out_txt}")
                        fix_list.append(out_txt)
           
                        with open(unit_test_path, "r", encoding="utf-8") as test_file:
                            unit_test = test_file.read()
                            unit_tests[out_txt] = unit_test
            elif count_txt_files_in_enhance() > 0 :
                for i in range(1, count_txt_files_in_enhance() + 1) :
                    out_txt = os.path.join(SOURCE_DIR, f"{class_name}_{name}_1_{i}_Test_outMsg.txt")
                    unit_test_path = os.path.join(test_path, f"{class_name}_{name}_1_{i}_Test.java")
                    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 and os.path.exists(unit_test_path):
                        print(f"target: {out_txt}")
                        fix_list.append(out_txt)
                  
                        with open(unit_test_path, "r", encoding="utf-8") as test_file:
                            unit_test = test_file.read()
                            unit_tests[out_txt] = unit_test
            else : # 
                for i in range(1, count_txt_files_in_scenarios() + 1) :
                    out_txt = os.path.join(SOURCE_DIR, f"{class_name}_{name}_0_{i}_Test_outMsg.txt")
                    unit_test_path = os.path.join(test_path, f"{class_name}_{name}_0_{i}_Test.java")
                    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 0 and os.path.exists(unit_test_path):
                        print(f"target : {out_txt}")
                        fix_list.append(out_txt)
                       
                        with open(unit_test_path, "r", encoding="utf-8") as test_file:
                            unit_test = test_file.read()
                            unit_tests[out_txt] = unit_test
                        

            num_parts = len(fix_list)
            for f in fix_list:
                futures.append(executor.submit(
                    process_prompt_file, f, file_path, library_name, class_name, name,
                    original_code, target_dict, user_prompt, system_prompt, ai_prompt, model, unit_tests[f]
                ))
        for future in as_completed(futures):
            print(".")



    return
    if os.path.exists(path_file):

        df = pd.read_csv(path_file, encoding="cp949")

        
        for idx, row in df.iterrows():
            file_path = row.get("path", "").strip()
            library_name = row.get("lib", "").strip()
            class_name = row.get("class", "").strip()
            method_name = row.get("method", "").strip() 
            name = row.get("name", "").strip()
            method_signature = row.get("method_signiture", "").strip()
            scenario_n = count_txt_files_in_scenarios()
            java_n = count_java_files(SOURCE_DIR)
            enhance_n = count_txt_files_in_enhance()
            enhance2_n = count_txt_files_in_enhance2()

            if enhance_n != 0: #
                target_classes = []
                error_paths = []
                target = enhance_n
                if enhance2_n > 0 :
                    target = enhance2_n
                for i in range(1, target+1): #
                    unit_test_path = row.get("test", "").strip() + "\\" + row.get("class", "") + "_" +row.get("name", "").strip() +f"_1_{i}_Test.java"
                    if enhance2_n > 0 :
                        unit_test_path = row.get("test", "").strip() + "\\" + row.get("class", "") + "_" +row.get("name", "").strip() +f"_2_{i}_Test.java"

                    if os.path.exists(unit_test_path):
                        target_classes.append(unit_test_path)
                    else:
                        break

                error_path = rf'./error_logs/{row.get("class", "")}_{row.get("name", "").strip()}_1_{len(target_classes)}_Test_outMsg.txt'
                if enhance2_n > 0:
                    error_path = rf'./error_logs/{row.get("class", "")}_{row.get("name", "").strip()}_2_{len(target_classes)}_Test_outMsg.txt'
  
                unit_test_path = target_classes[-1]

            else :
                target_classes = []
                error_paths = []
                for i in range(1, scenario_n+1): 
                    unit_test_path = row.get("test", "").strip() + "\\" + row.get("class", "") + "_" +row.get("name", "").strip() +f"_0_{i}_Test.java"
                    if os.path.exists(unit_test_path):
                        target_classes.append(unit_test_path)
                    else:
                        break
                error_path = rf'./error_logs/{row.get("class", "")}_{row.get("name", "").strip()}_0_{len(target_classes)}_Test_outMsg.txt'
                unit_test_path = target_classes[-1]



            if not file_path:
                continue 

            target_dict = dict()
            
            for d in data:
                if class_name in d["clazz"] and name in d["methodName"]:
                    result = are_signatures_equal(d["signature"], method_signature)
                    if result :
                        target_dict = d
                        break


            if os.path.exists(file_path):
               
                try :
                    with open(file_path, "r", encoding="utf-8") as code_file:
                        original_code = code_file.read()

                    with open(unit_test_path, "r", encoding="utf-8") as test_file:
                        unit_test = test_file.read()
                except Exception as e:
                    print(f"⚠️ : {file_path} ({e})")
                    continue

                if target_dict["body"] == "(source not found)" :
                    body =  extract_method_body(original_code, method_signature)
                    target_dict["body"] = body

            
                user_prompt_modified = user_prompt.replace("{ Library Name }", library_name)
                user_prompt_modified = user_prompt_modified.replace("{ Class Name }", class_name)
                user_prompt_modified = user_prompt_modified.replace("{ Insert existing JUnit 5 test code here }", unit_test)
                user_prompt_modified = user_prompt_modified.replace("{ CLASS_BODY }", original_code)
                user_prompt_modified = user_prompt_modified.replace("{ CLASS_NAME }", target_dict["clazz"])
                user_prompt_modified = user_prompt_modified.replace("{ METHOD_NAME }", target_dict["methodName"])
                user_prompt_modified = user_prompt_modified.replace("{ VISIBILITY }", target_dict["visibility"])
                user_prompt_modified = user_prompt_modified.replace("{ METHOD_SIGNATURE }", target_dict["signature"])
                #user_prompt_modified = user_prompt_modified.replace("{ METHOD_BODY }", target_dict["body"])
                user_prompt_modified = user_prompt_modified.replace("{ NODE }", str(target_dict["nodes"]))
                user_prompt_modified = user_prompt_modified.replace("{ EDGE }", str(target_dict["edges"]))
                user_prompt_modified = user_prompt_modified.replace("{ FLOW_SUMMARY }", '\n'.join(target_dict["flowSummary"]))
                user_prompt_modified = user_prompt_modified.replace("{ CYCLOMATIC_COMPLEXITY }", str(target_dict["cc"]))
                user_prompt_modified = user_prompt_modified.replace("{ BLOCK_LIST }", '\n'.join(target_dict["blockList"]))
                user_prompt_modified = user_prompt_modified.replace("{ BLOCK_EDGES }", '\n'.join(target_dict["blockEdges"]))
                user_prompt_modified = user_prompt_modified.replace("{ DEP_CLASS }", '\n'.join(str(dep_method) for dep_method in target_dict["depClasses"]))
                user_prompt_modified = user_prompt_modified.replace("{ DEP_METHOD }", '\n'.join(str(dep_method) for dep_method in target_dict["depMethods"]))

                name = str(row.get("name", "")).strip()

                errors = extract_error_lines(error_path)
                
                error_string = "\n".join(errors)
                user_prompt_modified = user_prompt_modified.replace("{ Insert compilation or runtime error log here }", error_string)

                print(f"\n📝 '{file_path}' 파일의 코드를 {model} 모델로 처리 중...")


  
                chain_response_obj, chain_response_text = chat_with_openai(
                    model, system_prompt, ai_prompt, user_prompt_modified
                )

                if isinstance(chain_response_obj, str):
                
                    print(chain_response_obj)
                    continue

                print(f"🤖 AI ({file_path}): {chain_response_text[:200]}")


                if chain_response_obj:
                    save_response(chain_response_obj, model, system_prompt, user_prompt_modified)
            else:
                print(f"⚠️ 경로가 존재하지 않습니다: {file_path}")
    else:
        print("⚠️ path.csv 파일이 존재하지 않습니다.")

    print("\n✅ 모든 경로에 대한 처리가 완료되었습니다!")

if __name__ == "__main__":
    main()
