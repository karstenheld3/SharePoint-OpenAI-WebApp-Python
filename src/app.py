import os
from flask import Flask, send_from_directory, jsonify, request
from dataclasses import asdict
from demodata import DEMO_RESPONSES, CRAWLER_SETTINGS
from common_openai_functions import *
from utils import *

app = Flask(__name__)

# Global variables
openai_client = None

openai_service_type = os.getenv("OPENAI_SERVICE_TYPE", "openai")
openai_api_key = os.environ.get('OPENAI_API_KEY')

azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
azure_openai_api_version = os.environ.get('AZURE_OPENAI_API_VERSION')
azure_openai_api_key = os.environ.get('AZURE_OPENAI_API_KEY')
azure_openai_use_key_authentication = os.getenv("AZURE_OPENAI_USE_KEY_AUTHENTICATION", "false").lower() in ['true']
azure_openai_model_deployment_name = os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")

default_search_vector_store_id = os.getenv("DEFAULT_SEARCH_VECTOR_STORE_ID", "<your_default_vector_store_id>")
default_sharepoint_source_url = os.getenv("DEFAULT_SHAREPOINT_SOURCE_URL", "https://<your_tenant>.sharepoint.com/sites/<your_site>/Shared%20Documents/")

# Initialize OpenAI client
def init_openai_client():
  global openai_client
  try:
    if openai_service_type == "openai":
      openai_client = create_openai_client(openai_api_key)
    elif openai_service_type == "azure_openai":
      openai_client = create_azure_openai_client(azure_openai_endpoint, azure_openai_api_version, azure_openai_api_key, azure_openai_use_key_authentication)
  except Exception as e:
    print(f"Error initializing OpenAI client of type '{openai_service_type}': {str(e)}")
    raise

# Initialize the client at module level
init_openai_client()



@app.route('/')
def home():
  return 'Hello World!'

@app.route('/alive')
def health():
  """Health check endpoint for monitoring."""
  return "OK", 200

# Handle favicon.ico requests
@app.route('/favicon.ico')
def favicon():
  return '', 204

# Ensure the default document is not served
@app.route('/hostingstart.html')
def ignore_default_doc():
  return home()

@app.route('/describe', methods=['POST'])
def describe():
  function_name = 'describe()'
  start_time = log_function_header(function_name)
  # extract tenant url from default_sharepoint_source_url (part until 3rd /)
  sharepoint_tenant_url = '/'.join(default_sharepoint_source_url.split('/')[:3]) + '/'

  # Extract domains from crawler settings
  domains = [
    {
      'name': dom.get('name', ''),
      'description': dom.get('description', '')
    } for dom in CRAWLER_SETTINGS.get('domains', [])
  ]
  
  # Prepare response
  response = {
    'data': {
      'description': 'This tool can search the content of SharePoint documents.',
      'domains': domains,
      'content_root': sharepoint_tenant_url
      # 'favicon': 'AAABAAAIACoJQAANgA...APgfAAA='  # base64, optional
    }
  }
  log_function_footer(function_name, start_time)
  return jsonify(response), 200, {'Content-Type': 'application/json'}

@app.route('/query', methods=['POST'])
def query():
  function_name = 'query()'
  start_time = log_function_header(function_name)
  vsid = default_search_vector_store_id

  # Get request data
  request_data = request.get_json()
  if not request_data or 'data' not in request_data or 'query' not in request_data['data']:
    return jsonify({'error': 'Invalid request format'}), 400, {'Content-Type': 'application/json'}

  query = request_data['data']['query']

  if query and vsid:
    print(f"  Query: {truncate_string(query,80)}")

    # Search for matching query in demo responses
    for item in DEMO_RESPONSES:
      if item['query'].lower() == query.lower():
        return jsonify({'data': {
          'query': item['query'],
          'answer': item['answer'],
          'source_markers': item['source_markers'],
          'sources': item['sources']
        }}), 200, {'Content-Type': 'application/json'}

    search_results, response = retry_on_openai_errors(
      lambda:get_search_results_using_responses(openai_client, azure_openai_model_deployment_name, query, vsid, 4, 0, 100)
      ,indentation=2
    )

    data = build_data_object(query, search_results, response)
    return jsonify({'data': data}), 200, {'Content-Type': 'application/json'}


  # By default return empty response with correct structure
  return jsonify({'data': {
    'query': query,
    'answer': '',
    'source_markers': ['【', '】'],
    'sources': []
  }}), 200, {'Content-Type': 'application/json'}

  log_function_footer(function_name, start_time)

# Convert search_results to data object as required by /query endpoint with array of sources { "data": "<text>", "source": "<url>", "metadata": { <attributes> } }
def build_data_object(query, search_results, response):
  sources = []
  sourceDocLibUrl = default_sharepoint_source_url
  if not sourceDocLibUrl.endswith("/"): sourceDocLibUrl += "/"
  for result in search_results:
    source = {
      "data": result.content[0].text if result.content else "",
      "source": f"{sourceDocLibUrl}{result.filename}",
      "metadata": result.attributes
    }
    sources.append(source)
  data = {
    "query": query
    ,"answer": response.output_text
    ,"source_markers": ["【", "】"]
    ,"sources": sources
  }
  return data
  

# https://platform.openai.com/docs/guides/tools-file-search
# https://github.com/openai/openai-python/blob/main/src/openai/resources/responses/responses.py
@app.route('/search')
def search():
  function_name = 'search()'
  start_time = log_function_header(function_name)

  # Get query parameters
  query = request.args.get('query')
  vsid = request.args.get('vsid')
  format = request.args.get('format', 'html')
  
  if not query:
    message = "Missing 'query' parameter"
    if format == 'json': return jsonify({"error": message}), 400, {'Content-Type': 'application/json'}
    else: return message, 400, {'Content-Type': 'text/plain'}
  if not vsid:
    message = "Missing 'vsid' (vector store id) parameter"
    if format == 'json': return jsonify({"error": message}), 400, {'Content-Type': 'application/json'}
    else: return message, 400, {'Content-Type': 'text/plain'}

  print(f"  Query: {truncate_string(query,80)}")

  # try:
  search_results, response = retry_on_openai_errors(
    lambda:get_search_results_using_responses(openai_client, azure_openai_model_deployment_name, query, vsid, 4, 0, 100)
    ,indentation=2
  )
  data = build_data_object(query, search_results, response)

  print(f"  Response: {truncate_string(response.output_text,80)}")
  print(f"  status='{response.status}', tool_choice='{response.tool_choice}', input_tokens={response.usage.input_tokens}, output_tokens={response.usage.output_tokens}")
  # except Exception as e:
  #   print(f"    Error: {str(e)}")
  #   return jsonify({"error": str(e)}), 500, {'Content-Type': 'application/json'}

  # If no match found, return empty response with correct structure
  if format == 'json':
    return jsonify({"data": data}), 200, {'Content-Type': 'application/json'}
  else:
    # For HTML response, convert the data dict to HTML table and wrap in proper HTML document
    table_html = convert_to_nested_html_table(data)
    output_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Search Results</title></head><body>{table_html}</body></html>"""
    return output_html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    
  log_function_footer(function_name, start_time)

if __name__ == '__main__':
  app.run(
    host='0.0.0.0',      # Required for Azure
    port=int(os.environ.get('PORT', 5000)),
    debug=False           # Disable debug mode in production
  )
