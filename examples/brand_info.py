import os

from replynodes.dx import ReplyNodes

client = ReplyNodes(api_key=os.environ["REPLYNODES_API_KEY"])
result = client.web.brand(url="https://replynodes.com")

print(result.data)
print("request id:", result.meta.request_id)
