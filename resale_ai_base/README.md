# Resale AI Base

Technical helpers shared by the resale AI features (`resale_ai_product`,
`resale_ai_manufacturer`, `resale_advertisements`).

## Features

`resale.ai.service` (abstract model, no data, no access rules needed):

- `get_agent(config_key)`: returns the `ai.agent` whose id is stored in the
  given system parameter, or an empty recordset.
- `request_llm(...)`: sends one structured request to an agent's provider and
  returns the raw response.
- `parse_json_response(response)`: extracts the JSON object from a provider
  response, tolerating Markdown fences.
- `ResaleAIRequestError`: `UserError` subclass raised for provider failures so
  callers can fall back to a backup agent.

## Configuration

None. Agents are selected in the settings of the modules that use them.
