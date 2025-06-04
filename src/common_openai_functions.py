# Common Open AI functions (COAI)
# Copyright 2025, Karsten Held (MIT License)

import os
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import openai
import httpx
from dataclasses import dataclass
from typing import List, Optional, Union, Iterable, Literal, Dict
from openai.types.responses import (ResponseInputParam,ResponseTextConfigParam,ToolParam)
from openai.types.responses.response_includable import ResponseIncludable
from openai.types.shared_params.responses_model import ResponsesModel
from openai.types.shared_params.metadata import Metadata
from openai.types.shared_params.reasoning import Reasoning
from openai.types.responses import response_create_params
from openai._types import NOT_GIVEN, NotGiven
from openai._types import Headers, Query, Body
import time


@dataclass
class CoaiSearchContent:
  text: str
  type: Literal["text"]

@dataclass
class CoaiSearchResponse:
  content: List[CoaiSearchContent]
  file_id: str
  filename: str
  score: float
  attributes: Optional[Dict[str, Union[str, float, bool]]] = None

# Copy the needed parameters from create() function (current version: 1.79.0):
# https://github.com/openai/openai-python/blob/main/src/openai/resources/responses/responses.py
@dataclass
class CoaiResponseParams:
  input: Union[str, ResponseInputParam]
  model: ResponsesModel
  include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN
  instructions: Optional[str] | NotGiven = NOT_GIVEN
  max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN
  metadata: Optional[Metadata] | NotGiven = NOT_GIVEN
  parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN
  previous_response_id: Optional[str] | NotGiven = NOT_GIVEN
  reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN
  service_tier: Optional[Literal["auto", "default", "flex"]] | NotGiven = NOT_GIVEN
  store: Optional[bool] | NotGiven = NOT_GIVEN
  stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN
  temperature: Optional[float] | NotGiven = NOT_GIVEN
  text: ResponseTextConfigParam | NotGiven = NOT_GIVEN
  tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN
  tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN
  top_p: Optional[float] | NotGiven = NOT_GIVEN
  truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN
  user: str | NotGiven = NOT_GIVEN
  # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
  # The extra values given here take precedence over values defined on the client or passed to this method.
  extra_headers: Headers | None = None
  extra_query: Query | None = None
  extra_body: Body | None = None
  timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN



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

# Uses the file_search tool of the Responses API to get search results from a vector store
# Why? As of 2025-06-04, Azure Open AI Services does not support the Séarch API. This is a temporary workaround to get similar results.
# -> Client error '404 Resource Not Found' for url 'https://<ai-resource>.cognitiveservices.azure.com/openai/vector_stores/<VECTOR-STORE-ID>/search?api-version=2025-04-01-preview'
def get_search_results_using_responses(client, model, query, vector_store_id, max_num_results, temperature, max_output_tokens) -> tuple[List[CoaiSearchResponse], any]:
  params = CoaiResponseParams(
    model=model
    ,instructions="Return 'N/A' (without single quotes) if no results are found."
    ,input=query
    ,tools=[{"type": "file_search", "vector_store_ids": [vector_store_id], "max_num_results": max_num_results}]
    ,max_output_tokens=max_output_tokens
    ,temperature=temperature
    ,include=["file_search_call.results"]
  )
  response = _client_responses_create_wrapper(client, params)
  search_results: List[CoaiSearchResponse] = []
  file_search_call = next((item for item in response.output if item.type == 'file_search_call'), None)
  file_search_call_results = None if file_search_call is None else getattr(file_search_call, 'results', None)
  if  file_search_call_results:
    for result in file_search_call_results:
        content = [CoaiSearchContent(text=result.text, type="text")]
        item = CoaiSearchResponse(
          attributes=result.attributes
          ,content=content
          ,file_id=result.file_id
          ,filename=result.filename
          ,score=result.score
        )
        search_results.append(item)
  return search_results, response


# Internal wrapper around OpenAI response model call
def _client_responses_create_wrapper(client, params: CoaiResponseParams):
  return client.responses.create(
    model=params.model,
    input=params.input,
    include=params.include,
    instructions=params.instructions,
    max_output_tokens=params.max_output_tokens,
    metadata=params.metadata,
    parallel_tool_calls=params.parallel_tool_calls,
    previous_response_id=params.previous_response_id,
    reasoning=params.reasoning,
    service_tier=params.service_tier,
    store=params.store,
    stream=params.stream,
    temperature=params.temperature,
    text=params.text,
    tool_choice=params.tool_choice,
    tools=params.tools,
    top_p=params.top_p,
    truncation=params.truncation,
    user=params.user,
    extra_headers=params.extra_headers,
    extra_query=params.extra_query,
    extra_body=params.extra_body,
    timeout=params.timeout
  )