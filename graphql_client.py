from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

transport = RequestsHTTPTransport(
    url="http://127.0.0.1:8000/graphql",
    verify=True,
    retries=3,
)

client = Client(transport=transport, fetch_schema_from_transport=True)

def send_to_graphql(info):
    mutation = gql("""
        mutation AddUser($input: UserProfileInput!) {
            addUserProfile(input: $input) {
                success
                message
            }
        }
    """)

    variables = {
        "input": {
            "name": info["name"],
            "email": info["email"],
            "phone": info["phone"],
            "location": info["location"],
            "skills": info["skills"],
            "jobs": info["jobs"]
        }
    }

    result = client.execute(mutation, variable_values=variables)
    print("GraphQL response:", result)
    