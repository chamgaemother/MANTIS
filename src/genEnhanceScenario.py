import openai
import os
import datetime
import json
import pandas as pd
import sys
import io
import subprocess
import os
from pathlib import Path

# Custom Config Class
from config import Config
from Utils import save_response, load_prompt, chat_with_openai, count_java_files, count_txt_files_in_scenarios

# 프롬프트 파일 경로 설정
PROMPT_DIR = Config.get_prompt_dir()
SYSTEM_PROMPT_PATH = "./prompt/enhanceScenarioSystem.txt"
USER_PROMPT_PATH = "./prompt/enhanceScenarioUser.txt"
AI_PROMPT_PATH = "./prompt/enhanceScenarioAI.txt"
JSON_PATH = Config.get_json_path()
SOURCE_DIR = "./result"

def read_and_join_java_sources_with_header(folder_path, class_name, method_name):
    """
    주어진 폴더에서 .java 파일들을 정렬 후 하나의 문자열로 합침.
    각 파일 앞에 'class_name::method_name' 포맷의 헤더를 붙임.
    """
    java_files = []

    # 1. 모든 .java 파일 수집
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".java"):
                full_path = os.path.join(root, file)
                java_files.append((file, full_path))

    # 2. 파일 이름 기준 정렬
    java_files.sort(key=lambda x: x[0])

    # 3. 파일 내용 합치기
    combined_code = ""
    for filename, path in java_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
                combined_code += f"{class_name}::{method_name} // {filename}\n{code}\n\n"
        except Exception as e:
            print(f"[ERROR] {filename} 읽기 실패: {e}")

    return combined_code


def main():
    print("-- OpenAI Chat 시작 (종료하려면 'exit' 입력)")

    # 사용자에게 모델 선택 요청 (번호 입력)
    while True:
        # 예시를 위해 고정 (원본 로직 유지)
        model_choice = '4' #o1-mini

        if model_choice in Config.MODEL_MAP:
            model = Config.MODEL_MAP[model_choice]
            print(f"-- 모델 `{model}` 선택됨.\n")
            break
        else:
            print("-- 올바른 번호를 입력하세요.")

    # 프롬프트 파일 로드
    system_prompt = load_prompt(SYSTEM_PROMPT_PATH) 
    ai_prompt = load_prompt(AI_PROMPT_PATH) 
    user_prompt = load_prompt(USER_PROMPT_PATH)
    json_file = Path(JSON_PATH)

    if not user_prompt:
        print("-- `user.txt` 파일이 비어있거나 없습니다. `/prompt/user.txt`를 확인하세요.")
        exit()

    if model != "o1-mini" and not system_prompt:
        print("-- `system.txt` 파일이 비어있거나 없습니다. `/prompt/system.txt`를 확인하세요.")

    with json_file.open(encoding="utf-8") as f:
        data = json.load(f)            # → Python list[ dict ]

    print("-- 모델과 프롬프트 설정 완료!")

    # 이 부분에서 path.txt → path.csv 로 변경, Pandas DataFrame 처리
    path_file = "path_temp.csv"
    if os.path.exists(path_file):
        # CSV 파일을 읽어 DataFrame 생성
        df = pd.read_csv(path_file, encoding="cp949")

        for idx, row in df.iterrows():
            file_path = row.get("path", "").strip()
            library_name = row.get("lib", "").strip()
            class_name = row.get("class", "").strip()
            name = row.get("name", "").strip()
            unit_tests = read_and_join_java_sources_with_header(SOURCE_DIR, class_name, name)

            target_dict = dict()
            
            for d in data:
                if class_name in d["clazz"] and name in d["methodName"]:
                    target_dict = d
                    break

            if not file_path:
                continue  # path가 비어있으면 무시

            if os.path.exists(file_path):
                # Java 소스 코드 읽기
                with open(file_path, "r", encoding="utf-8") as code_file:
                    original_code = code_file.read()

                # user_prompt에서 필요한 부분들을 순차적으로 대체
                user_prompt_modified = user_prompt.replace("{ LIBRARY_NAME }", library_name)
                user_prompt_modified = user_prompt_modified.replace("{ CLASS_BODY }", original_code)
                user_prompt_modified = user_prompt_modified.replace("{ CLASS_NAME }", target_dict["clazz"])
                user_prompt_modified = user_prompt_modified.replace("{ EXISTING_TEST_SUITE }", unit_tests)
                user_prompt_modified = user_prompt_modified.replace("{ METHOD_NAME }", target_dict["methodName"])
                user_prompt_modified = user_prompt_modified.replace("{ VISIBILITY }", target_dict["visibility"])
                user_prompt_modified = user_prompt_modified.replace("{ METHOD_SIGNATURE }", target_dict["signature"])
                user_prompt_modified = user_prompt_modified.replace("{ METHOD_BODY }", target_dict["body"])
                user_prompt_modified = user_prompt_modified.replace("{ FLOW_SUMMARY }", '\n'.join(target_dict["flowSummary"]))
                user_prompt_modified = user_prompt_modified.replace("{ NODE }", str(target_dict["nodes"]))
                user_prompt_modified = user_prompt_modified.replace("{ EDGE }", str(target_dict["edges"]))
                user_prompt_modified = user_prompt_modified.replace("{ CYCLOMATIC_COMPLEXITY }", str(target_dict["cc"]))
                user_prompt_modified = user_prompt_modified.replace("{ BLOCK_LIST }", '\n'.join(target_dict["blockList"]))
                user_prompt_modified = user_prompt_modified.replace("{ BLOCK_EDGES }", '\n'.join(target_dict["blockEdges"]))
                user_prompt_modified = user_prompt_modified.replace("{ DEP_CLASS }", '\n'.join(str(dep_method) for dep_method in target_dict["depClasses"]))
                user_prompt_modified = user_prompt_modified.replace("{ DEP_METHOD }", '\n'.join(str(dep_method) for dep_method in target_dict["depMethods"]))

                print(f"\n-- '{file_path}' 파일의 코드를 {model} 모델로 처리 중...")

                # OpenAI와 채팅 실행
                chain_response_obj, chain_response_text = chat_with_openai(
                    model, system_prompt, ai_prompt, user_prompt_modified
                )

                if isinstance(chain_response_obj, str):
                    # OpenAIError 등 에러 메시지
                    print(chain_response_obj)
                    continue

                print(f"-- AI ({file_path}): {chain_response_text[0:200]}...")  # 응답의 처음 500자 출력

                # 응답 저장
                if chain_response_obj:
                    save_response(chain_response_obj, model, system_prompt, user_prompt_modified)
            else:
                print(f"-- 경로가 존재하지 않습니다: {file_path}")
    else:
        print("-- path.csv 파일이 존재하지 않습니다.")

    print("\n-- 모든 경로에 대한 처리가 완료되었습니다!")

# 채팅 실행
if __name__ == "__main__":
    main()