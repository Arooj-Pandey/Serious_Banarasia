router_prompt = """You are given a query: {re_structured_query} and are tasked to classify the query into a maximum of 2 classes: (text_api, image_api) if the query demands or requires classification into these API classes.

When converting the (query) into (keywords), ensure that:

1. Keywords preserve the complete semantic meaning of the original query.

2. No keyword segmentation should lead to any kind of contextual loss, and should not produce any kind of irrelevant results when performing a search.

3. Group words that form meaningful phrases together, avoiding unnecessary splitting.

4. If the query includes any kind of proper noun or named entity, ensure that the named entity is preserved as a single keyword.

5. Return the output in the following structure:

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