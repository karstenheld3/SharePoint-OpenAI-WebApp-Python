import os
import time
from flask import Flask, send_from_directory, jsonify, request
from demodata import DEMO_RESPONSES, CRAWLER_SETTINGS
from openai_backendtools import create_openai_client, create_azure_openai_client

app = Flask(__name__)

# Global variables
openai_client = None
azure_openai_model_deployment_name = os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini")

# Initialize OpenAI client
def init_openai_client():
  global openai_client
  try:
    openai_service_type = os.getenv("OPENAI_SERVICE_TYPE", "openai")
    azure_openai_use_key_authentication = os.getenv("AZURE_OPENAI_USE_KEY_AUTHENTICATION", "false").lower() in ['true']

    if openai_service_type == "openai":
      openai_client = create_openai_client()
    elif openai_service_type == "azure_openai":
      openai_client = create_azure_openai_client(azure_openai_use_key_authentication)
  except Exception as e:
    print(f"Error initializing OpenAI client: {str(e)}")
    raise

# Initialize the client at module level
init_openai_client()

# Retries the given function on rate limit errors
def retry_on_openai_errors(fn, indentation=0, retries=5, backoff_seconds=10):
  for attempt in range(retries):
    try:
      return fn()
    except Exception as e:
      # Only retry on rate limit errors
      if not (hasattr(e, 'type') and e.type == 'rate_limit_error'):
        raise e
      if attempt == retries - 1:  # Last attempt
        raise e
      print(f"{' '*indentation}Rate limit reached, retrying in {backoff_seconds} seconds... (attempt {attempt + 2} of {retries})")
      time.sleep(backoff_seconds)

def truncate_string(string, max_length):
  if len(string) > max_length:
    return string[:max_length] + "..."
  return string


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
      'content_root': 'https://[TENANT].sharepoint.com/'
      # 'favicon': 'AAABAAAIACoJQAANgA...APgfAAA='  # base64, optional
    }
  }
  return jsonify(response), 200, {'Content-Type': 'application/json'}

@app.route('/query', methods=['POST'])
def query():
  # Get request data
  request_data = request.get_json()
  if not request_data or 'data' not in request_data or 'query' not in request_data['data']:
    return jsonify({'error': 'Invalid request format'}), 400, {'Content-Type': 'application/json'}

  search_query = request_data['data']['query']

  # Search for matching query in demo responses
  for item in DEMO_RESPONSES:
    if item['query'].lower() == search_query.lower():
      return jsonify({'data': {
        'query': item['query'],
        'answer': item['answer'],
        'source_markers': item['source_markers'],
        'sources': item['sources']
      }}), 200, {'Content-Type': 'application/json'}

  # If no match found, return empty response with correct structure
  return jsonify({'data': {
    'query': search_query,
    'answer': '',
    'source_markers': ['【', '】'],
    'sources': []
  }}), 200, {'Content-Type': 'application/json'}

@app.route('/search')
def search():
  # Get query parameters
  query = request.args.get('query')
  vsid = request.args.get('vsid')
  
  if not query:
    return jsonify({"error": "Missing 'query' parameter"}), 400, {'Content-Type': 'application/json'}
  if not vsid:
    return jsonify({"error": "Missing 'vsid' (vector store id) parameter"}), 400, {'Content-Type': 'application/json'}

  print(f"  Query: {truncate_string(query,80)}")

  try:
    response = retry_on_openai_errors(lambda: openai_client.responses.create(
      model=azure_openai_model_deployment_name
      ,input=query
      ,tools=[{ "type": "file_search", "vector_store_ids": [vsid] }]
      ,include=["file_search_call.results"]
    ), indentation=4)
    output_text = response.output_text
    response_file_search_tool_call = next((item for item in response.output if item.type == 'file_search_call'), None)
    search_results = getattr(response_file_search_tool_call, 'results', None)

    print(f"  Response: {truncate_string(response.output_text,80)}")
    print(f"  status='{response.status}', tool_choice='{response.tool_choice}', input_tokens={response.usage.input_tokens}, output_tokens={response.usage.output_tokens}")
  except Exception as e:
    print(f"    Error: {str(e)}")
    return jsonify({"error": str(e)}), 500, {'Content-Type': 'application/json'}

  # If no match found, return empty response with correct structure
  return jsonify({"data": {
    "query": query
    ,"answer": output_text
    ,"status": response.status
    ,"tool_choice": response.tool_choice
    ,"input_tokens": response.usage.input_tokens
    ,"output_tokens": response.usage.output_tokens
  }}), 200, {'Content-Type': 'application/json'}

if __name__ == '__main__':
  app.run(
    host='0.0.0.0',      # Required for Azure
    port=int(os.environ.get('PORT', 5000)),
    debug=False           # Disable debug mode in production
  )
