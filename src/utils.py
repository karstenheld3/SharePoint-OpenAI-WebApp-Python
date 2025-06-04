from typing import Dict, Any, List
import datetime

# Format a file size in bytes into a human-readable string
def format_filesize(num_bytes):
  if not num_bytes: return ''
  for unit in ['B','KB','MB','GB','TB']:
    if num_bytes < 1024: return f"{num_bytes:.2f} {unit}"
    num_bytes /= 1024
  return f"{num_bytes:.2f} PB"

# Format timestamp into a human-readable string (RFC3339 with ' ' instead of 'T')
def format_timestamp(ts):
  return ('' if not ts else datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'))

def log_function_header(name):
  start_time = datetime.datetime.now()
  print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] START: {name}...")
  return start_time

def log_function_footer(name, start_time):
  end_time = datetime.datetime.now()
  secs = (end_time - start_time).total_seconds()
  parts = [(int(secs // 3600), 'hour'), (int((secs % 3600) // 60), 'min'), (int(secs % 60), 'sec')]
  total_time = ', '.join(f"{val} {unit}{'s' if val != 1 else ''}" for val, unit in parts if val > 0)
  print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] END: {name} ({total_time}).")

def truncate_string(string, max_length):
  if len(string) > max_length:
    return string[:max_length] + "..."
  return string

import html

# Returns a nested html table from the given data (Dict or List or Array)
def convert_to_nested_html_table(data: Any, max_depth: int = 10) -> str:
  def handle_value(v: Any, depth: int) -> str:
    if depth >= max_depth: return html.escape(str(v))
    if isinstance(v, dict): return handle_dict(v, depth + 1)
    elif isinstance(v, list): return handle_list(v, depth + 1)
    else: return html.escape(str(v))

  def handle_list(items: List[Any], depth: int) -> str:
    if not items or depth >= max_depth: return html.escape(str(items))
    # For simple lists, just return the string representation
    if not any(isinstance(item, (dict, list)) for item in items): return html.escape(str(items))
    # For complex lists, create a table
    rows = [f"<tr><td>[{i}]</td><td>{handle_value(item, depth)}</td></tr>" for i, item in enumerate(items)]
    return f"<table border=1>{''.join(rows)}</table>"
  
  def handle_dict(d: Dict[str, Any], depth: int) -> str:
    if not d or depth >= max_depth: return html.escape(str(d))
    rows = [f"<tr><td>{html.escape(str(k))}</td><td>{handle_value(v, depth)}</td></tr>" for k, v in d.items()]
    return f"<table border=1>{''.join(rows)}</table>"
  return handle_value(data, 1)

def log_function_header(name):
  start_time = datetime.datetime.now()
  print(f"[{start_time.strftime('%Y-%m-%d %H:%M:%S')}] START: {name}...")
  return start_time

def log_function_footer(name, start_time):
  end_time = datetime.datetime.now()
  secs = (end_time - start_time).total_seconds()
  parts = [(int(secs // 3600), 'hour'), (int((secs % 3600) // 60), 'min'), (int(secs % 60), 'sec')]
  total_time = ', '.join(f"{val} {unit}{'s' if val != 1 else ''}" for val, unit in parts if val > 0)
  print(f"[{end_time.strftime('%Y-%m-%d %H:%M:%S')}] END: {name} ({total_time}).")
