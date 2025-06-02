High level Architecture:

Prompt -> Gemini LLM (Fucntion call using SQL) -> SQL Call to GCP Bigquery -> 
                                                                            |
Response <-     Gemini LLM (SQL Results to Natural Language)    <- Results <-


Prompt Examples:

how many clinicals are ordered last week?
how many surgeries are performed in the last 2 days?
num of patients stayed in the hospital more than a day
average hospital stay of all the patients
number of inpatients joined with in 5 days of a previous discharge
get me top 10 patients with longest duration in the hospital
give me the top 3 reasons of the patient stayed in the hospital longest

Future Enhancements:

Scalability:
Use async queries if response time becomes a bottleneck
Cache frequent queries or LLM responses in Cloud Memorystore

AI Enhancements:
prompt caching (to reduce token costs)
Improve prompt engineering for medical context
Log prompts and responses for fine-tuning and debugging

Deploment to GCP:
Use Cloud Run or App Engine for deploying the Streamlit app
Store secrets (API keys, credentials) securely in Secret Manager
Add Cloud Logging and Monitoring for observability
Set up custom domain and HTTPS with Cloud Load Balancer
Restrict access to authorized users