local tmp = ngx.var.request_uri
tmp = tmp:gsub('?.*$', '', 1)
tmp = tmp:gsub('^/[^/]+/', '', 1)
tmp = tmp:gsub('+', '%%2B')
tmp = tmp:gsub('&amp;', '%%26')
tmp = ngx.unescape_uri(tmp)
return tmp
