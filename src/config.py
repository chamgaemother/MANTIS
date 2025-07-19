# config.py
class Config:
    __API_KEY = "your-api-key-here"  
    __PROMPT_DIR = "./prompt"  
    __SYSTEM_PROMPT = "system.txt"  
    __USER_PROMPT = "user.txt" 
    __MAX_TOKENS = 15000   
    __CONFIG_JSON = "./preprocess_data/cod_all_methods.json"  

    MODEL_MAP = {
    "1": "gpt-4o",
    "2": "gpt-4o-mini",
    "3": "o1",
    "4": "o1-mini"
    }

    @classmethod
    def get_api_key(cls):

        return cls.__API_KEY
    
    @classmethod
    def get_json_path(cls):

        return cls.__CONFIG_JSON
    

    @classmethod
    def set_api_key(cls, new_key): 

        cls.__API_KEY = new_key

    @classmethod
    def get_prompt_dir(cls):

        return cls.__PROMPT_DIR
    
    @classmethod
    def set_prompt_dir(cls, new_dir):
 
        cls.__PROMPT_DIR = new_dir

    @classmethod
    def get_system_prompt(cls):
        
        return cls.__SYSTEM_PROMPT
    
    @classmethod
    def set_system_prompt(cls, new_prompt):
  
        cls.__SYSTEM_PROMPT = new_prompt

    @classmethod
    def get_user_prompt(cls):

        return cls.__USER_PROMPT
    
    @classmethod
    def set_user_prompt(cls, new_prompt):
   
        cls.__USER_PROMPT = new_prompt

    @classmethod
    def get_max_tokens(cls):
      
        return cls.__MAX_TOKENS

    @classmethod
    def set_max_tokens(cls, new_max_tokens):
  
        cls.__MAX_TOKENS = new_max_tokens
