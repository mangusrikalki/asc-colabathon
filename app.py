import time
from google.cloud import bigquery
import streamlit as st
import vertexai
from vertexai.generative_models import FunctionDeclaration, GenerativeModel, Part, Tool

vertexai.init(
    project="asc-colabathon",
    location="us-central1"
)

BIGQUERY_DATASET_ID = "dv_test_1"
GCP_PROJECT_ID= "asc-colabathon"

list_datasets_func = FunctionDeclaration(
    name="list_datasets",
    description="Get a list of datasets",
    parameters={
        "type": "object",
        "properties": {},
    },
)

list_tables_func = FunctionDeclaration(
    name="list_tables",
    description="List tables in all the datasets from the array of datasets given in arguments",
    parameters={
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "array",
                "description": "Dataset ID to fetch tables from.",
            }
        },
        "required": [
            "dataset_id",
        ],
    },
)

get_table_func = FunctionDeclaration(
    name="get_table",
    description="""Get information about a table, including the description, schema, and number of rows that will help answer the user's question.
        Always use the fully qualified dataset and table names.""",
    parameters={
        "type": "object",
        "properties": {
            "table_id": {
                "type": "string",
                "description": "Fully qualified ID of the table to get information about",
            }
        },
        "required": [
            "table_id",
        ],
    },
)

sql_query_func = FunctionDeclaration(
    name="sql_query",
    description="""Get information from data in BigQuery using SQL queries. 
        for all the queries use use dv_test_1 as a default dataset.
        use table test1 for all the clinical releted queries.
        use documentclass to filter out the type of clinical orders (example: ORDER, SURGERY)
        use createddatetime for all the date and time releated queries.""",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "SQL query on a single line that will help give quantitative answers to the user's question when run on a BigQuery dataset and table. In the SQL query, always use the fully qualified dataset and table names.",
            }
        },
        "required": [
            "query",
        ],
    },
)

sql_query_tool = Tool(
    function_declarations=[
        list_datasets_func,
        list_tables_func,
        get_table_func,
        sql_query_func,
    ],
)

model = GenerativeModel(
    "gemini-2.0-flash", # "gemini-1.5-pro-001",
    generation_config={"temperature": 0},
    tools=[sql_query_tool],
)

st.set_page_config(
    page_title="AI Chat bot for the Clinical Data",
    layout="wide",
)

col1, col2 = st.columns([8, 1])
with col1:
    st.title("AI Chat bot for Health Care Clinical Data")
with col2:
    st.text("Demo")

st.subheader("Using Vertex AI - Gemini AI - Function Calling")

st.markdown(
    """[Source Code](https://github.com/mangusrikalki/asc-colabathon/blob/main/app.py)   •
    [Documentation](https://github.com/mangusrikalki/asc-colabathon/blob/main/readme.md)"""
)

with st.expander("Sample prompts", expanded=True):
    st.write(
        """
        - What kind of information is in this database?
        - Can you show the top 3 campaigns by impressions?
        """
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"].replace("$", "\$"))  # noqa: W605
        # try:
        #     with st.expander("Function calls, parameters, and responses"):
        #         st.markdown(message["backend_details"])
        # except KeyError:
        #     pass

if prompt := st.chat_input("Ask me about information in the database..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        chat = model.start_chat()
        client = bigquery.Client(GCP_PROJECT_ID)
        prompt += """
            Please give a concise, high-level summary followed by detail in
            plain language about where the information in your response is
            coming from in the database. Only use information that you learn
            from BigQuery, do not make up information.
            """
        # this is the first prompt
        response = chat.send_message(prompt)

        response = response.candidates[0].content.parts[0]
        # print(response)

        api_requests_and_responses = []
        backend_details = ""

        params = {}
        api_response = ""
        datasets = list()
        # this is used to learn the responses using gemini
        function_calling_in_process = True
        while function_calling_in_process:
            try:
                #setting params
                
                for key, value in response.function_call.args.items():
                    params[key] = value
                
                print("1 - chat_send: " + str(api_response) + "; call_name: " + response.function_call.name + "; params: ")
                print(", ".join(f"{k}: {v}" for k, v in params.items()))
                
                if response.function_call.name == "list_datasets":
                    api_response = client.list_datasets()
                    # api_response = str([dataset.dataset_id for dataset in api_response])
                    for dataset in api_response:
                        datasets.append(str(dataset.dataset_id))
                    print("datasets: " + str(datasets))
                    api_response = datasets # " ,".join(datasets)
                    api_requests_and_responses.append(
                        [response.function_call.name, params, api_response]
                    )
                    # datasets = api_response
                if response.function_call.name == "list_tables":
                    api_response = ""
                    for d in params["dataset_id"]:
                        print("dataset id = " + d)
                        print(d)
                        tmp_response = client.list_tables(d)
                        tmp_response = str([table.table_id for table in tmp_response])
                        print("inside:" + tmp_response)
                        api_response = api_response + tmp_response
                        api_requests_and_responses.append(
                        [response.function_call.name, params, api_response])
                    print("outside:" + api_response)

                if response.function_call.name == "get_table":
                    api_response = client.get_table(params["table_id"])
                    api_response = api_response.to_api_repr()
                    api_requests_and_responses.append(
                        [
                            response.function_call.name,
                            params,
                            [
                                str(api_response.get("description", "")),
                                str(
                                    [
                                        column["name"]
                                        for column in api_response["schema"]["fields"]
                                    ]
                                ),
                            ],
                        ]
                    )
                    api_response = str(api_response)

                if response.function_call.name == "sql_query":
                    job_config = bigquery.QueryJobConfig(
                        maximum_bytes_billed=100000000
                    )  # Data limit per query job
                    try:
                        cleaned_query = (
                            params["query"]
                            .replace("\\n", " ")
                            .replace("\n", "")
                            .replace("\\", "")
                        )
                        query_job = client.query(cleaned_query, job_config=job_config)
                        api_response = query_job.result()
                        api_response = str([dict(row) for row in api_response])
                        api_response = api_response.replace("\\", "").replace("\n", "")
                        api_requests_and_responses.append(
                            [response.function_call.name, params, api_response]
                        )
                    except Exception as e:
                        api_response = f"{str(e)}"
                        api_requests_and_responses.append(
                            [response.function_call.name, params, api_response]
                        )

                print("2  - chat_send: " + str(api_response) + "; call_name: " + response.function_call.name + "; params: ")
                print(", ".join(f"{k}: {v}" for k, v in params.items()))

                response = chat.send_message(
                    Part.from_function_response(
                        name=response.function_call.name, 
                        response={
                            "content": api_response,
                        },
                    ),
                )
                response = response.candidates[0].content.parts[0]

                backend_details += "- Function call:\n"
                backend_details += (
                    "   - Function name: ```"
                    + str(api_requests_and_responses[-1][0])
                    + "```"
                )
                backend_details += "\n\n"
                backend_details += (
                    "   - Function parameters: ```"
                    + str(api_requests_and_responses[-1][1])
                    + "```"
                )
                backend_details += "\n\n"
                backend_details += (
                    "   - API response: ```"
                    + str(api_requests_and_responses[-1][2])
                    + "```"
                )
                backend_details += "\n\n"
                # with message_placeholder.container():
                    # st.markdown(backend_details)

            except AttributeError:
                function_calling_in_process = False

        time.sleep(3)

        full_response =  response.text
        with message_placeholder.container():
            st.markdown(full_response.replace("$", "\$"))
        #     with st.expander("Function calls, parameters, and responses:"):
        #         st.markdown(backend_details)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": full_response,
                "backend_details": backend_details,
            }
        )