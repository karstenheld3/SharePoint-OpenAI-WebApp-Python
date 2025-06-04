import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import openai

def create_openai_client():
  api_key = os.environ.get('OPENAI_API_KEY')
  return openai.OpenAI(api_key=api_key)

# Create an Azure OpenAI client using either managed identity or API key authentication.
def create_azure_openai_client(use_key_authentication=False):
  endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
  api_version = os.environ.get('AZURE_OPENAI_API_VERSION')
  
  if use_key_authentication:
    # Use API key authentication
    api_key = os.environ.get('AZURE_OPENAI_API_KEY')
    # Create client with API key
    return openai.AzureOpenAI(
      api_version=api_version,
      azure_endpoint=endpoint,
      api_key=api_key
    )
  else:
    # Use managed identity or service principal authentication (whatever is configured in the environment variables)
    cred = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(cred, "https://cognitiveservices.azure.com/.default")
    # Create client with token provider
    return openai.AzureOpenAI( api_version=api_version, azure_endpoint=endpoint, azure_ad_token_provider=token_provider )


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
