import os

from replynodes.dx import ReplyNodes

client = ReplyNodes(
    api_key=os.environ["REPLYNODES_API_KEY"],
    timeout=10,
)

result = client.youtube.search(term="open source databases", limit=5)
print(result.data)
print("request id:", result.meta.request_id)
