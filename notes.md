1. `PUT /end-user/{external_id}/`

   ```curl
   curl --location --request PUT 'https://api.portialabs.ai/api/v0/end-user/123-test-user/' \
   --header 'Content-Type: application/json' \
   --header 'Accept: application/json' \
   --header 'Authorization: Api-Key prt-9hmy019f.cGdEHSKGb0e7r7T0tLUbqoP202axSXub' \
   --data-raw '{
    "name":"Dean Ambrose",
    "email":"vinayakvispute2@gmail.com",
    "phone_number":1123341234
   }'
   ```

   OUTPUT:

   ```json
   {
     "external_id": "123-test-user",
     "organization": "11355903-ec47-43e2-89b0-33f30e040d7e",
     "name": "Dean Ambrose",
     "email": "vinayakvispute2@gmail.com",
     "phone_number": "1123341234",
     "additional_data": {},
     "created": "2025-08-18T11:38:35.342920Z",
     "updated": "2025-08-18T11:40:05.091039Z"
   }
   ```

2. `GET /end-user/:external_id/`

```curl
curl --location 'https://api.portialabs.ai/api/v0/end-user/123-test-user/' \
--header 'Accept: application/json' \
--header 'Authorization: Api-Key prt-9hmy019f.cGdEHSKGb0e7r7T0tLUbqoP202axSXub'
```

OUTPUT:

```json
{
  "external_id": "123-test-user",
  "organization": "11355903-ec47-43e2-89b0-33f30e040d7e",
  "name": "Dean Ambrose",
  "email": "vinayakvispute2@gmail.com",
  "phone_number": "1123341234",
  "additional_data": {},
  "created": "2025-08-18T11:38:35.342920Z",
  "updated": "2025-08-18T11:40:05.091039Z"
}
```

3. `POST /tools/:tool_id/ready/`

```curl
curl --location 'https://api.portialabs.ai/api/v0/tools/portia:github::star_repo/ready/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Api-Key prt-9hmy019f.cGdEHSKGb0e7r7T0tLUbqoP202axSXub' \
--data '{
  "output": {},
  "execution_context":{
    "end_user_id":"123-test-user",
    "plan_run_id": "urn:uuid:d0820023-d084-52e0-3b86-a1d7120742d3"
  }
}'
```

OUTPUT :

```json
{
  "ready": false,
  "clarifications": [
    {
      "id": "clar-27bf79e9-c03e-4c97-b71e-9d711fcf4095",
      "plan_run_id": "prun-d0820023-d084-52e0-3b86-a1d7120742d3",
      "category": "Action",
      "response": null,
      "step": null,
      "user_guidance": "OAuth required for github: Click the link below to authenticate.",
      "resolved": false,
      "source": "Portia cloud tool auth",
      "action_url": "https://github.com/login/oauth/authorize/?redirect_uri=https%3A%2F%2Fapi.portialabs.ai%2Fapi%2Fv0%2Foauth%2Fgithub&client_id=Ov23liXuuhY9MOePgG8Q&scope=public_repo+starring&state=APP_NAMES%3Dgithub%253A%253Agithub%26PLAN_RUN_ID%3Durn%253Auuid%253Ad0820023-d084-52e0-3b86-a1d7120742d3%26END_USER_ID%3D0ecc3f86-4bc6-43e9-bf39-71366d0a2191%26ORG_ID%3D11355903-ec47-43e2-89b0-33f30e040d7e%26CLARIFICATION_ID%3Dclar-27bf79e9-c03e-4c97-b71e-9d711fcf4095%26SCOPES%3Dpublic_repo%2Bstarring&response_type=code",
      "require_confirmation": false
    }
  ]
}
```

4. Show Dialog box to authenticate this github app

5. `POST /plans/`

```curl --location 'https://api.portialabs.ai/api/v0/plans/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Api-Key prt-9hmy019f.cGdEHSKGb0e7r7T0tLUbqoP202axSXub' \
--data '{
    "query": "Star the github repo for portiaAI/portia-sdk-python",
    "tool_ids": [
        "portia:github::star_repo"
    ],
    "steps": [
        {
            "task": "Star the GitHub repository '\''portiaAI/portia-sdk-python'\'' using the provided repository identifier.",
            "inputs": [],
            "tool_id": "portia:github::star_repo",
            "output": "$repo_starred",
            "condition": null
        }
    ],
    "plan_inputs": []
}'
```

OUTPUT:

```json
{
  "id": "plan-1386aba2-0d48-4799-acb0-277987929a2e",
  "user": "vinayakvispute262003@gmail.com",
  "run_count": 0,
  "query": "Star the github repo for portiaAI/portia-sdk-python",
  "tool_ids": ["portia:github::star_repo"],
  "steps": [
    {
      "task": "Star the GitHub repository 'portiaAI/portia-sdk-python' using the provided repository identifier.",
      "inputs": [],
      "tool_id": "portia:github::star_repo",
      "output": "$repo_starred",
      "condition": null
    }
  ],
  "plan_inputs": [],
  "created": "2025-08-18T13:20:29.767975Z",
  "updated": "2025-08-18T13:20:29.767996Z",
  "liked": false,
  "organization": "11355903-ec47-43e2-89b0-33f30e040d7e"
}
```

6. `PUT /plan-runs/:id/`

```curl
curl --location --request PUT 'https://api.portialabs.ai/api/v0/plan-runs/550e8411-e29b-41d4-a716-446655440000/' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--header 'Authorization: Api-Key prt-9hmy019f.cGdEHSKGb0e7r7T0tLUbqoP202axSXub' \
--data '{
  "id": "550e8411-e29b-41d4-a716-446655440000",
  "plan_id": "plan-1386aba2-0d48-4799-acb0-277987929a2e",
  "end_user": "123-test-user",
  "state": "IN_PROGRESS",
  "execution_context": {
    "end_user_id": "123-test-user",
    "plan_run_id": "550e8411-e29b-41d4-a716-446655440000"
  },
   "outputs": {}
}'
```
