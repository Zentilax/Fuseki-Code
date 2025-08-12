from openai import OpenAI
import requests
from config import OPENAI_API_KEY, FUSEKI_ENDPOINT

client = OpenAI(api_key=OPENAI_API_KEY)

def load_ontology_prompt():
    with open("ontology_prompt.txt", "r", encoding="utf-8") as f:
        return f.read()
def load_formatting_prompt():
    with open("formatting_prompt.txt", "r", encoding="utf-8") as f:
        return f.read()

def generate_sparql_query(question, ontology_prompt):
    messages = [
        {"role": "system", "content": ontology_prompt},
        {"role": "user", "content": f"User Question: {question}"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",  # Updated to a valid model name
            messages=messages
        )
        
        # Since the prompt now returns only the SPARQL query, return it directly
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        return f"⚠️ Error generating SPARQL query: {str(e)}"

def query_fuseki(sparql_query):
    headers = {"Accept": "application/sparql-results+json"}
    response = requests.post(FUSEKI_ENDPOINT, data={"query": sparql_query}, headers=headers)

    if response.status_code != 200:
        raise Exception(f"SPARQL query failed: {response.status_code} - {response.text}")
    
    results = response.json()["results"]["bindings"]
    return results

def format_results_raw(results):
    """Convert raw SPARQL results to a simple text format for LLM processing."""
    if not results:
        return "No results found."

    output = ""
    for row in results:
        output += ", ".join(f"{key}: {val['value']}" for key, val in row.items()) + "\n"
    return output

def format_results_with_llm(raw_results, original_question):
    if not raw_results or raw_results == "No results found.":
        return raw_results
    
    formatting_prompt = load_formatting_prompt()

    try:
        messages = [
            {"role": "system", "content": formatting_prompt},
            {"role": "user", "content": f"Original question: {original_question}\n\nRaw results from database:\n{raw_results}\n\nPlease format this information in a user-friendly way."}
        ]
        
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=messages
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        # Fall back to raw results if formatting fails
        print(f"⚠️  Formatting failed, showing raw results: {e}")
        return raw_results

def main():
    ontology_prompt = load_ontology_prompt()

    while True:
        question = input("\nAsk a question about German cuisine (or type 'exit'): ")
        if question.lower() == "exit":
            break

        print("\n🔍 Generating SPARQL query...")
        sparql_query = generate_sparql_query(question, ontology_prompt)
        print(f"\n📄 SPARQL:\n{sparql_query}")

        # Check if there was an error in query generation
        if sparql_query.startswith("⚠️"):
            print(sparql_query)
            continue

        try:
            print("\n🔗 Querying Jena Fuseki...")
            results = query_fuseki(sparql_query)
            #print("\n Raw Results : ",results)
           
            raw_formatted = format_results_raw(results)
            #print("\n Raw Formatted Results : ",raw_formatted)

            # Use LLM to make results more readable
            print("\n✨ Formatting results...")
            formatted_results = format_results_with_llm(raw_formatted, question)
            
            print("\n✅ Results:")
            print(formatted_results)
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()