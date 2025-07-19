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
from Utils import count_txt_files_in_enhance, chat_with_openai, load_prompt, count_txt_files_in_enhance2

# 프롬프트 파일 경로
SYSTEM_PROMPT_PATH = "./prompt/enhanceTest System.txt"
USER_PROMPT_PATH = "./prompt/enhanceTest User.txt"
AI_PROMPT_PATH = "./prompt/enhanceTest AI.txt"
JSON_PATH = Config.get_json_path()

def process_prompt_file(i, file_path, library_name, class_name, name, original_code, target_dict,
                        user_prompt, system_prompt, ai_prompt, model):
    
    prompt_file_name = f"{library_name}_{name}_enhance_scenarios_part_{i}.txt"
    prompt_file_path = os.path.join("./result/enhance_scenarios", prompt_file_name)
    if count_txt_files_in_enhance2() > 0:
        prompt_file_name = f"{library_name}_{name}_2enhance_scenarios_part_{i}.txt"
        prompt_file_path = os.path.join("./result/2enhance_scenarios", prompt_file_name)

    if not os.path.exists(prompt_file_path):
        return f"-- 프롬프트 파일 없음: {prompt_file_path}"

    with open(prompt_file_path, "r", encoding="utf-8") as pf:
        scenarios = pf.read()

    user_prompt_modified = user_prompt \
        .replace("{ LIBRARY_NAME }", library_name) \
        .replace("{ SCENARIO_LIST }", scenarios) \
        .replace("{ CLASS_BODY }", original_code) \
        .replace("{ CLASS_NAME }", target_dict["clazz"]) \
        .replace("{ class_name }", class_name) \
        .replace("{ METHOD_NAME }", target_dict["methodName"]) \
        .replace("{ VISIBILITY }", target_dict["visibility"]) \
        .replace("{ METHOD_SIGNATURE }", target_dict["signature"]) \
        .replace("{ METHOD_BODY }", target_dict["body"]) \
        .replace("{ FLOW_SUMMARY }", '\n'.join(target_dict["flowSummary"])) \
        .replace("{ NODE }", str(target_dict["nodes"])) \
        .replace("{ EDGE }", str(target_dict["edges"])) \
        .replace("{ CYCLOMATIC_COMPLEXITY }", str(target_dict["cc"])) \
        .replace("{ BLOCK_LIST }", '\n'.join(target_dict["blockList"])) \
        .replace("{ BLOCK_EDGES }", '\n'.join(target_dict["blockEdges"])) \
        .replace("{ DEP_CLASS }", '\n'.join(str(dep) for dep in target_dict["depClasses"])) \
        .replace("{ DEP_METHOD }", '\n'.join(str(dep) for dep in target_dict["depMethods"]))

    chain_response_obj, chain_response_text = chat_with_openai(
        model, system_prompt, ai_prompt, user_prompt_modified
    )

    if isinstance(chain_response_obj, str):
        return chain_response_obj

    if count_txt_files_in_enhance2() > 0:
        save_filename = f"{library_name}_{name}_2_{i}_Test.json"
    else :
        save_filename = f"{library_name}_{name}_1_{i}_Test.json"
    save_path = os.path.join("./result", save_filename)

    response_data = {
                    "info": {
                        "model": model,
                        "finish_reason": chain_response_obj.choices[0].finish_reason,
                        "usage": {
                            "completion_tokens": chain_response_obj.usage.completion_tokens,
                            "prompt_tokens": chain_response_obj.usage.prompt_tokens,
                            "total_tokens": chain_response_obj.usage.total_tokens,
                            # 아래 details 는 모델 종류에 따라 없을 수도 있으므로 가변적으로 처리
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

    return f"-- 완료: {save_filename}"

def main() :
    print("-- OpenAI Chat 시작 (종료하려면 'exit' 입력)")

    model_choice = '4'  # gpt-4o-mini 고정
    model = Config.MODEL_MAP.get(model_choice)
    if not model:
        print("-- 유효하지 않은 모델 선택")
        exit(1)

    print(f"-- 모델 `{model}` 선택됨.\n")

    system_prompt = load_prompt(SYSTEM_PROMPT_PATH)
    ai_prompt = load_prompt(AI_PROMPT_PATH)
    user_prompt = load_prompt(USER_PROMPT_PATH)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("-- 모델과 프롬프트 설정 완료!")

    path_file = "path_temp.csv"
    if not os.path.exists(path_file):
        print("-- path.csv 파일이 존재하지 않습니다.")
        exit(1)

    df = pd.read_csv(path_file, encoding="cp949")

    futures = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for idx, row in df.iterrows():
            file_path = str(row.get("path", "")).strip()
            library_name = str(row.get("lib", "")).strip()
            class_name = str(row.get("class", "")).strip()
            name = str(row.get("name", "")).strip()

            if not file_path or not os.path.exists(file_path):
                print(f"-- 경로가 비었거나 없음: {file_path}")
                continue

            with open(file_path, "r", encoding="utf-8") as code_file:
                original_code = code_file.read()

            target_dict = next(
                (d for d in data if class_name in d["clazz"] and name in d["methodName"]), {}
            )

            if not target_dict:
                print(f"-- 대상 메서드 정보 누락: {class_name}.{name}")
                continue

            num_parts = count_txt_files_in_enhance()
            if count_txt_files_in_enhance2() > 0 :
                num_parts = count_txt_files_in_enhance2()
                
            for i in range(1, num_parts+1):
                futures.append(executor.submit(
                    process_prompt_file, i, file_path, library_name, class_name, name,
                    original_code, target_dict, user_prompt, system_prompt, ai_prompt, model
                ))

        for future in as_completed(futures):
            print(future.result())

    print("\n-- 모든 경로에 대한 처리가 완료되었습니다!")

if __name__ == "__main__":
    main()