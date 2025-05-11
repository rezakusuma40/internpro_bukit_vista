if you can't run it on streamlit due to "OSError: [E050] Can't find model 'en_core_web_sm'. It doesn't seem to be a Python package or a valid path to a data directory." error, try to add this to requirements.txt: change 3.8.0 to your version if needed
https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

cred.json contains all necessary credentials for the app to run.  
I don't push cred.json to github cause it's secret.
If you want to run it yourself, you must provide your own credentials
