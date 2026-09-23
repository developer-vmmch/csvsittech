import re

with open('static/css/vmmc-select.css', 'r') as f:
    content = f.read()

# Replace '.vmmc-search-select .vss-dropdown' with '.vss-dropdown'
content = content.replace('.vmmc-search-select .vss-dropdown', '.vss-dropdown')
# Replace '.vmmc-search-select .vss-list' with '.vss-dropdown .vss-list'
content = content.replace('.vmmc-search-select .vss-list', '.vss-dropdown .vss-list')
# Replace '.vmmc-search-select .vss-item' with '.vss-dropdown .vss-item'
content = content.replace('.vmmc-search-select .vss-item', '.vss-dropdown .vss-item')
content = content.replace('.vmmc-search-select .vss-item:hover', '.vss-dropdown .vss-item:hover')
content = content.replace('.vmmc-search-select .vss-item.highlighted', '.vss-dropdown .vss-item.highlighted')
content = content.replace('.vmmc-search-select .vss-item-main', '.vss-dropdown .vss-item-main')
content = content.replace('.vmmc-search-select .vss-item-sub', '.vss-dropdown .vss-item-sub')
content = content.replace('.vmmc-search-select .vss-message', '.vss-dropdown .vss-message')

with open('static/css/vmmc-select.css', 'w') as f:
    f.write(content)

