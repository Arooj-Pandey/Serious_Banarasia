# from pathlib import Path
# import json
# from google.generativeai import GenerativeModel
# from translator.Query_Restructure_and_Segregation import QueryRestructurer

# # Initialize Google AI Model
# GM = GenerativeModel('gemini-pro')


# def generate_final_prompt(results, user_query):
#     final_prompt_template_path = Path(r"D:\projects\Serious_Banarasia\prompts\final_response\final_prompt.txt")
#     if not final_prompt_template_path.is_file():
#         raise FileNotFoundError(f"Prompt file not found at {final_prompt_template_path}")

#     with open(final_prompt_template_path, "r", encoding="utf-8") as f:
#         final_prompt_template = f.read()
#         formatted_final_prompt_template = final_prompt_template.format(
#             results=results,
#             query=user_query
#         )

#     keywords_result = GM.generate_content(formatted_final_prompt_template)
#     return keywords_result.text if keywords_result and hasattr(keywords_result, 'text') else str(keywords_result) # return final prompt


from pathlib import Path
import json
from langchain_openai import OpenAI
from translator.Query_Restructure_and_Segregation import QueryRestructurer
from models.openai import OpenAI

# Initialize Google AI Model
GM = OpenAI("gpt-3.5-turbo-instruct")


def generate_final_prompt(results, user_query):
    try:
        final_prompt_template_path = Path(r"D:\projects\Serious_Banarasia\prompts\final_response\final_prompt.txt")
        if not final_prompt_template_path.is_file():
            raise FileNotFoundError(f"Prompt file not found at {final_prompt_template_path}")

        with open(final_prompt_template_path, "r", encoding="utf-8") as f:
            final_prompt_template = f.read()
            formatted_final_prompt_template = final_prompt_template.format(
                results=results,
                query=user_query
            )

        keywords_result = GM.invoke(formatted_final_prompt_template)
        
        # Extract only the text from the response
        if isinstance(keywords_result, dict):
            if 'choices' in keywords_result and len(keywords_result['choices']) > 0:
                return keywords_result['choices'][0]['text'].strip()
        
        # If response is already a string or has text attribute
        if hasattr(keywords_result, 'text'):
            return keywords_result.text.strip()
        
        return str(keywords_result).strip()

    except Exception as e:
        logger.error(f"Error generating final prompt: {str(e)}")
        return f"Error processing response: {str(e)}"