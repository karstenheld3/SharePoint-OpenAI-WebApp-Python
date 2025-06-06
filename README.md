# SharePoint-OpenAI-WebApp-Python
A Python web app that provides Open AI functionality based on documents in SharePoint Online

## Requirements

| Package | Version | PyPI Link |
|---------|---------|------------|
| Flask | 3.0.0 | [PyPI](https://pypi.org/project/Flask/) |
| gunicorn | 23.0.0 | [PyPI](https://pypi.org/project/gunicorn/) |
| cryptography | 41.0.7 | [PyPI](https://pypi.org/project/cryptography/) |
| azure-identity | 1.15.0 | [PyPI](https://pypi.org/project/azure-identity/) |
| requests | 2.32.3 | [PyPI](https://pypi.org/project/requests/) |
| python-dotenv | 1.1.0 | [PyPI](https://pypi.org/project/python-dotenv/) |
| openai | 1.79.0 | [PyPI](https://pypi.org/project/openai/) |

## Azure App Service Compatibility

This application is configured to run on Azure App Service (Linux). Specific package versions have been chosen to ensure compatibility with the Azure App Service Linux environment, particularly regarding GLIBC version requirements.
