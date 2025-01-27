router_prompt = """You are given a query: {re_structured_query} and are tasked to classify the query into a maximum of 2 classes: "text_api, image_api" if the query demands or requires classification into these API classes.

When converting the query to keywords, ensure that:

Keywords preserve the complete semantic meaning of the original query.
No keyword segmentation should lead to a loss of context or produce irrelevant results when performing a search.
Group words that form meaningful phrases together, avoiding unnecessary splitting.
Return the output in the following structure:

json
{{
    "api_needed": 0,
    "api_name": ["keyword_1", "keyword_2", ... "keyword_n"],
    "api_name": ["keyword_1", "keyword_2", ... "keyword_n"]
}}

Example:

Query: images of famous Varanasi ghats

Correct Response:
json
{{
    "api_needed": 1,
    "image_api": ["famous Varanasi ghats"]
}}


Incorrect Response:
json
{{
    "api_needed": 1,
    "image_api": ["images", "Varanasi ghats", "famous Varanasi ghats"]
}}


Query: Tell me about history of Varanasi.


Correct Response:
json
{{
    "api_needed": 1,
    "text_api": ["history of Varanasi"]
}}

Incorrect Response:
json
{{
    "api_needed": 1,
    "search_api": ["Varanasi", "history"]
}}


Query: Hii How are you ? 

json
{{
    "api_needed" : 0,
    "message" :["your answere here"]
}}

"""