import os
from flask import Flask, send_from_directory, jsonify, request
from demodata import DEMO_RESPONSES, CRAWLER_SETTINGS

app = Flask(__name__)

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

if __name__ == '__main__':
  app.run(
    host='0.0.0.0',      # Required for Azure
    port=int(os.environ.get('PORT', 5000)),
    debug=False           # Disable debug mode in production
  )
