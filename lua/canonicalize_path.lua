local tmp = ngx.var.request_uri

-- Remove query string
tmp = tmp:gsub('?.*$', '', 1)

-- Remove first part of path (command)
tmp = tmp:gsub('^/[^/]+/', '', 1)

-- substitute thoses chars with encoded string
tmp = tmp:gsub('+', '%%2B')
tmp = tmp:gsub('&amp;', '%%26')

tmp = ngx.unescape_uri(tmp)
return tmp
