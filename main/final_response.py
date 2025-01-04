from pathlib import Path
import json
from google.generativeai import GenerativeModel
from translator.Query_Restructure_and_Segregation import QueryRestructurer

# Initialize Google AI Model
GM = GenerativeModel('gemini-pro')


def generate_final_prompt(results, user_query):
    final_prompt_template_path = Path(r"D:\projects\Serious_Banarasia\prompts\final_response\final_prompt.txt")
    if not final_prompt_template_path.is_file():
        raise FileNotFoundError(f"Prompt file not found at {final_prompt_template_path}")

    with open(final_prompt_template_path, "r", encoding="utf-8") as f:
        final_prompt_template = f.read()
        formatted_final_prompt_template = final_prompt_template.format(
            results=results,
            query=user_query
        )

    keywords_result = GM.generate_content(formatted_final_prompt_template)
    return keywords_result.text if keywords_result and hasattr(keywords_result, 'text') else str(keywords_result) # return final prompt

# # Main execution
# restructured_query = restructure_query("tell me about shri kashi vishwanath ji")
# keywords = get_keywords_result_dict(restructured_query)
# results = route_keywords(keywords)

# with open('keywords_result_dict.json', 'r') as f:
#     data = json.load(f)
#     results = parse_api_results(data)

# final_prompt = generate_final_prompt(results, "tell me about shri kashi vishwanath ji")