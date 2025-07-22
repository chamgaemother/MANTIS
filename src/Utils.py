import datetime
import json
import os
import openai
# Custom Config Class
from config import Config


import re
import javalang
from typing import List, Tuple, Optional

# OpenAI Client initialize
client = openai.OpenAI(api_key=Config.get_api_key())

def count_java_files(directory = "./result"):
    java_file_count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".java"):
                java_file_count += 1
    return java_file_count

def count_txt_files_in_scenarios():
    directory = "./result/scenarios"
    if not os.path.exists(directory):
        print("❌ .")
        return 0

    txt_files = [f for f in os.listdir(directory) if f.endswith(".txt")]
    return len(txt_files)

def count_txt_files_in_enhance():
    directory = "./result/enhance_scenarios"
    if not os.path.exists(directory):
        print("❌ .")
        return 0

    txt_files = [f for f in os.listdir(directory) if f.endswith(".txt")]
    return len(txt_files)

def count_txt_files_in_enhance2():
    directory = "./result/2enhance_scenarios"
    if not os.path.exists(directory):
        print("❌ .")
        return 0

    txt_files = [f for f in os.listdir(directory) if f.endswith(".txt")]
    return len(txt_files)

def chat_with_openai(model, system_prompt, ai_prompt, user_prompt):
    try:
        messages = []
        if system_prompt and model != "o1-mini":
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "user", "content": system_prompt})

        messages.append({"role": "assistant", "content": ai_prompt})
        messages.append({"role": "user", "content": user_prompt})

        if model in ["o1", "o1-mini"]:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=Config.get_max_tokens()
            )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=Config.get_max_tokens()
            )

        reply = response.choices[0].message.content
        return response, reply.strip()

    except openai.OpenAIError as e:
        return f"-- OpenAI API error: {e}", ""
    
def save_response(response_obj, model, system_prompt, user_prompt):

    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")  # YYYYMMDD_HHMMSS 형식
    filename = f"{timestamp}_{model}_response.json"
    directory = "./result"  
    os.makedirs(directory, exist_ok=True) 
    filepath = os.path.join(directory, filename)

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

    print(f"-- response save to json : {filepath}")
    
def load_prompt(file_path):
 
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

_SIG_RE = re.compile(
    r"""
    <                                    
    (?P<class>[^:]+?)\s*:\s*         
    (?P<ret>[^ ]+)\s+                   
    (?P<name>[^\(]+)                     
    \(
       (?P<params>[^\)]*)              
    \)
    >                                   
    """,
    re.VERBOSE,
)

def _simple(t: str) -> str:
    return t.strip().split('.')[-1].replace('[]', '').replace('...', '').strip()

def parse_jimple_signature(sig: str) -> Tuple[str, List[str]]:
    m = _SIG_RE.match(sig.strip())
    if not m:
        raise ValueError(f"invalid Jimple signiture: {sig}")
    name = m["name"].strip()
    params = [p for p in map(str.strip, m["params"].split(',')) if p]
    params_simple = [_simple(p) for p in params]
    return name, params_simple


def extract_method_body(source: str, jimple_sig: str) -> Optional[str]:


    target_name, target_params = parse_jimple_signature(jimple_sig)
    tree = javalang.parse.parse(source)
    lines = source.splitlines(keepends=True)

    for _, node in tree.filter(javalang.tree.MethodDeclaration):

        if node.name != target_name or len(node.parameters) != len(target_params):
            continue


        node_param_simple = [_erase(_simple(p.type.name)) for p in node.parameters]

        if node_param_simple != target_params:
            continue  

      
        start_line = node.position.line - 1          # 0-index
        start_col  = node.position.column - 1


        offset = sum(len(l) for l in lines[:start_line]) + start_col
        sub_src = source[offset:]

        brace_open = sub_src.find('{')
        if brace_open == -1:
            continue  

        brace_depth = 0
        for idx, ch in enumerate(sub_src[brace_open:], start=brace_open):
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
                if brace_depth == 0:
               
                    return sub_src[brace_open:idx + 1]

    return None   


def _erase(tname: str) -> str:
    #  TypicalTypeParam, e.g. T, E, K, V, N …
    if re.fullmatch(r'[A-Z]\w*', tname):
        return 'Object'        
    return tname

def _parse_first(sig: str) -> Tuple[str, str, List[str]]:
    """
    format : 'org.apache.commons.cli.Options parsePattern(java.lang.String)'
    return value: (return_type, method_name, [param_types])
    """
    m = re.fullmatch(r'\s*(\S+)\s+(\w+)\((.*)\)\s*', sig)
    if not m:
        raise ValueError(f"worong first signiture: {sig}")
    ret, name, params = m.groups()
    params_list = [p.strip() for p in params.split(',')] if params else []
    return ret, name, params_list

def _parse_second(sig: str) -> Tuple[str, str, List[str]]:
    """
    FORAMT: '<org.apache.commons.cli.PatternOptionBuilder: org.apache.commons.cli.Options parsePattern(java.lang.String)>'
    RETURN VALUE: (return_type, method_name, [param_types])

    """

    inner = sig.strip()[1:-1] if sig.strip().startswith('<') and sig.strip().endswith('>') else sig
    m = re.fullmatch(r'\s*(\S+)\s*:\s*(\S+)\s+(\w+)\((.*)\)\s*', inner)
    if not m:
        raise ValueError(f"wrong second signiture: {sig}")
    _decl_class, ret, name, params = m.groups()
    params_list = [p.strip() for p in params.split(',')] if params else []
    return ret, name, params_list

def are_signatures_equal(first_sig: str, second_sig: str) -> bool:
    """
    두 시그니처가 같은 메서드를 가리키면 True, 다르면 False
    (비교 기준: 리턴타입, 메서드 이름, 파라미터 목록이 모두 동일)
    """
    ret1, name1, params1 = _parse_first(first_sig)
    ret2, name2, params2 = _parse_second(second_sig)
    return (ret1 == ret2) and (name1 == name2) and (params1 == params2)



def extract_params(signature: str, simple_name: bool = True) -> List[str]:

    sig = signature.strip().lstrip("<").rstrip(">")

    match = re.search(r"\((.*)\)", sig)
    if not match:
        raise ValueError("Invalid signature: no parameter list found")
    params_block = match.group(1).strip()

    if not params_block:
        return []


    params: List[str] = []
    level = 0    
    current = []

    for ch in params_block:
        if ch == '<':
            level += 1
        elif ch == '>':
            level -= 1
        elif ch == ',' and level == 0:
            params.append(''.join(current).strip())
            current = []
            continue
        current.append(ch)
    if current:
        params.append(''.join(current).strip())

    if simple_name:
        def simplify(t: str) -> str:
        
            suffix = ''
            while t.endswith('[]') or t.endswith('...'):
                if t.endswith('[]'):
                    suffix = '[]' + suffix
                    t = t[:-2]
                else:  # ...
                    suffix = '...' + suffix
                    t = t[:-3]
    
            if '<' in t:
                outer, inner = re.match(r'([^<]+)<(.+)>', t).groups()
                inner_types = ','.join(simplify(p.strip()) for p in split_top_level(inner))
                outer_simple = outer.split('.')[-1]
                return f"{outer_simple}<{inner_types}>{suffix}"
            return f"{t.split('.')[-1]}{suffix}"
  
        def split_top_level(s: str) -> List[str]:
            lvl = 0; buf = []; parts = []
            for c in s:
                if c == '<': lvl += 1
                elif c == '>': lvl -= 1
                elif c == ',' and lvl == 0:
                    parts.append(''.join(buf)); buf = []; continue
                buf.append(c)
            if buf: parts.append(''.join(buf))
            return parts
        params = [simplify(p) for p in params]

    return params
